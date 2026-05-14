"""
Modal app definition for SpineAssist V2.

Deploy:   modal deploy backend/modal_app.py
Dev mode: modal serve backend/modal_app.py  (hot-reload)
"""
import os
import sys
import modal

app = modal.App("spineassist")
weights_volume = modal.Volume.from_name("spineassist-weights", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libglib2.0-0", "libsm6", "libxext6", "libxrender-dev", "libgl1", "wget", "unzip")
    .pip_install(
        "torch", "torchvision",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_dir("backend", remote_path="/app")
)


@app.cls(
    image=image,
    gpu="T4",
    volumes={"/weights": weights_volume},
    secrets=[modal.Secret.from_name("kaggle-credentials")],
    timeout=300,
    container_idle_timeout=120,
)
class SpineAssistApp:
    @modal.enter()
    def load_models(self):
        sys.path.insert(0, "/app")
        sys.path.insert(0, "/app/model_code")
        from main import load_all_models
        self.models = load_all_models("/weights")
        self.device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
        print(f"Models loaded on {self.device}: {list(self.models.keys())}")

    @modal.asgi_app()
    def web(self):
        import asyncio
        import json
        import shutil
        import tempfile

        from fastapi import FastAPI, File, HTTPException, UploadFile
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import StreamingResponse

        from main import (
            convert_to_npy,
            extract_images,
            format_results,
            generate_crops,
            parse_dicom_series,
            run_classifiers,
            run_coords_prediction,
            run_level2,
        )

        models = self.models
        device = self.device

        web_app = FastAPI(title="SpineAssist API V2")
        web_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @web_app.get("/")
        def health():
            return {"status": "ok", "models": list(models.keys())}

        @web_app.post("/api/predict/stream")
        async def predict_stream(file: UploadFile = File(...)):
            if not file.filename.endswith(".zip"):
                raise HTTPException(400, "Only .zip files are accepted.")

            content = await file.read()
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(400, "File too large. Maximum 50 MB.")

            filename = file.filename
            queue: asyncio.Queue = asyncio.Queue()

            def cb(msg: str):
                queue.put_nowait(("progress", msg))

            async def run_inference():
                work_dir = tempfile.mkdtemp()
                try:
                    npy_dir = os.path.join(work_dir, "npy")
                    crops_dir = os.path.join(work_dir, "crops")

                    cb("Parsing DICOM series...")
                    df_meta, extract_path = parse_dicom_series(content, filename, work_dir)

                    cb("Converting to arrays...")
                    convert_to_npy(df_meta, npy_dir)

                    cb("Predicting vertebral coordinates...")
                    preds_sag, df_sag = run_coords_prediction(models, df_meta, npy_dir, device)

                    crops_info: list = []
                    crop_fts: dict = {}
                    if preds_sag is not None:
                        cb("Generating level crops...")
                        crops_info, df_crop = generate_crops(
                            preds_sag, df_sag, df_meta, npy_dir, crops_dir
                        )
                        cb("Running classifiers...")
                        crop_fts = run_classifiers(models, df_crop, crops_dir, device)

                    cb("Aggregating predictions...")
                    final_preds, targets = run_level2(models, df_meta, crop_fts, device)

                    predictions = format_results(final_preds, targets, crops_info)
                    images = extract_images(df_meta, npy_dir)

                    await queue.put(("result", {
                        "patient_id": df_meta["study_id"].iloc[0] if not df_meta.empty else "Unknown",
                        "predictions": predictions,
                        "images": images,
                    }))
                except Exception as e:
                    await queue.put(("error", str(e)))
                finally:
                    shutil.rmtree(work_dir, ignore_errors=True)
                    await queue.put(None)

            async def event_stream():
                asyncio.create_task(run_inference())
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    event_type, data = item
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        return web_app
