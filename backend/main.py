import os
import sys
import json
import glob
import zipfile
import shutil
import base64
import tempfile
from collections import Counter

import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    import pydicom
except Exception:
    pydicom = None

try:
    import torch
except Exception:
    torch = None

try:
    from scipy.special import softmax
except Exception:
    def softmax(x, axis=-1):
        e = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e / e.sum(axis=axis, keepdims=True)

LEVELS = ["L1/L2", "L2/L3", "L3/L4", "L4/L5", "L5/S1"]
LEVELS_ = ["l1_l2", "l2_l3", "l3_l4", "l4_l5", "l5_s1"]
SEVERITIES = ["Normal/Mild", "Moderate", "Severe"]


def _setup_paths():
    """Add model_code to sys.path so internal imports resolve."""
    here = os.path.dirname(os.path.abspath(__file__))
    model_code_path = os.path.join(here, "model_code")
    if model_code_path not in sys.path:
        sys.path.insert(0, model_code_path)
    if here not in sys.path:
        sys.path.insert(0, here)


def load_all_models(weights_dir: str) -> dict:
    """Load all six model checkpoints from weights_dir into a dict keyed by role."""
    _setup_paths()
    from inference.lvl1 import predict, Config
    from model_zoo.models import define_model
    from model_zoo.models_lvl2 import define_model as define_model_2
    from util.torch import load_model_weights

    device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
    models = {}

    # Coords model
    folder = f"{weights_dir}/2024-08-29_0/"
    if os.path.exists(folder + "config.json"):
        try:
            cfg = Config(json.load(open(folder + "config.json")))
            cfg.local_rank = 0
            m = define_model(
                cfg.name,
                num_classes=cfg.num_classes,
                num_classes_aux=getattr(cfg, "num_classes_aux", 0),
                n_channels=cfg.n_channels,
                pooling=getattr(cfg, "pooling", "avg"),
                drop_rate=getattr(cfg, "drop_rate", 0.0),
                drop_path_rate=getattr(cfg, "drop_path_rate", 0.0),
                reduce_stride=getattr(cfg, "reduce_stride", False),
                pretrained=False,
            ).to(device).eval()
            m = load_model_weights(m, folder + f"{cfg.name}_1.pt", verbose=0, strict=False)
            models["coords"] = (m, cfg)
            print("Loaded: coords")
        except Exception as e:
            print(f"Error loading coords: {e}")

    # Crop classification models
    crop_map = {
        "crop": "2024-10-04_1",
        "crop_2": "2024-10-04_9",
        "scs_crop_coords": "2024-10-04_34",
        "scs_crop_coords_2": "2024-10-04_37",
    }
    for mode, folder_name in crop_map.items():
        folder = f"{weights_dir}/{folder_name}/"
        if os.path.exists(folder + "config.json"):
            try:
                cfg = Config(json.load(open(folder + "config.json")))
                cfg.local_rank = 0
                m = define_model(
                    cfg.name,
                    num_classes=cfg.num_classes,
                    num_classes_aux=getattr(cfg, "num_classes_aux", 0),
                    head_3d=getattr(cfg, "head_3d", ""),
                    n_frames=getattr(cfg, "n_frames", 1),
                    n_channels=cfg.n_channels,
                    pooling=getattr(cfg, "pooling", "avg"),
                    drop_rate=getattr(cfg, "drop_rate", 0.0),
                    drop_path_rate=getattr(cfg, "drop_path_rate", 0.0),
                    reduce_stride=getattr(cfg, "reduce_stride", False),
                    pretrained=False,
                ).to(device).eval()
                m = load_model_weights(m, folder + f"{cfg.name}_1.pt", verbose=0)
                if mode == "crop_2":
                    m.delta = 1
                models[mode] = (m, cfg)
                print(f"Loaded: {mode}")
            except Exception as e:
                print(f"Error loading {mode}: {e}")

    # Level-2 aggregation model
    folder = f"{weights_dir}/2024-10-08_2/"
    if os.path.exists(folder + "config.json"):
        try:
            cfg = Config(json.load(open(folder + "config.json")))
            m = define_model_2(
                cfg.name, ft_dim=cfg.ft_dim, layer_dim=cfg.layer_dim,
                dense_dim=cfg.dense_dim, p=cfg.p, n_fts=cfg.n_fts
            ).to(device).eval()
            m = load_model_weights(m, folder + f"{cfg.name}_1.pt", verbose=0)
            models["lvl2"] = (m, cfg)
            print("Loaded: lvl2")
        except Exception as e:
            print(f"Error loading lvl2: {e}")

    # Axial coords model
    folder = f"{weights_dir}/2024-09-02_33/"
    if os.path.exists(folder + "config.json"):
        try:
            cfg = Config(json.load(open(folder + "config.json")))
            cfg.local_rank = 0
            m = define_model(
                cfg.name,
                num_classes=cfg.num_classes,
                num_classes_aux=getattr(cfg, "num_classes_aux", 0),
                n_channels=cfg.n_channels,
                pooling=getattr(cfg, "pooling", "avg"),
                drop_rate=getattr(cfg, "drop_rate", 0.0),
                drop_path_rate=getattr(cfg, "drop_path_rate", 0.0),
                reduce_stride=getattr(cfg, "reduce_stride", False),
                pretrained=False,
            ).to(device).eval()
            m = load_model_weights(m, folder + f"{cfg.name}_1.pt", verbose=0, strict=False)
            models["coords_ax"] = (m, cfg)
            print("Loaded: coords_ax")
        except Exception as e:
            print(f"Error loading coords_ax: {e}")

    return models


def parse_dicom_series(file_bytes: bytes, filename: str, work_dir: str):
    """
    Write ZIP bytes to work_dir, extract, and build a series metadata DataFrame.
    Returns (df_meta, extract_path). The ZIP file is deleted after extraction.
    Raises ValueError if no DICOM files are found.
    """
    zip_path = os.path.join(work_dir, filename)
    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    study_name = filename[:-4]  # strip .zip
    extract_path = os.path.join(work_dir, study_name)
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        real_extract = os.path.realpath(extract_path)
        for member in z.infolist():
            member_path = os.path.realpath(os.path.join(real_extract, member.filename))
            if not member_path.startswith(real_extract + os.sep):
                raise ValueError(f"Illegal path in ZIP: {member.filename}")
        z.extractall(extract_path)
    os.remove(zip_path)

    dcm_files = glob.glob(f"{extract_path}/**/*.dcm", recursive=True)
    if not dcm_files:
        raise ValueError("No DICOM (.dcm) files found in the ZIP.")

    series_dict: dict = {}
    for dcm_path in dcm_files:
        rel = os.path.relpath(dcm_path, extract_path).replace("\\", "/")
        rel_parts = rel.split("/")
        if len(rel_parts) < 3:
            raise ValueError(f"Expected study/series/file.dcm structure in ZIP, got: {rel}")
        study_id, series_id = rel_parts[-3], rel_parts[-2]
        key = f"{study_id}/{series_id}"
        series_dict.setdefault(key, []).append(dcm_path)

    rows = []
    for key, files in series_dict.items():
        study_id, series_id = key.split("/")
        dcm = pydicom.dcmread(files[0], stop_before_pixels=True)
        description = getattr(dcm, "SeriesDescription", "Unknown")
        desc_lower = description.lower()

        orient = "Unknown"
        if "sagittal" in desc_lower or "sag" in desc_lower:
            orient = "Sagittal"
        elif "axial" in desc_lower or "ax" in desc_lower:
            orient = "Axial"
        elif hasattr(dcm, "ImageOrientationPatient"):
            iop = [float(x) for x in dcm.ImageOrientationPatient]
            normal = np.abs(np.cross(np.array(iop[:3]), np.array(iop[3:])))
            if normal[0] > 0.5:
                orient = "Sagittal"
            elif normal[2] > 0.5:
                orient = "Axial"
            elif normal[1] > 0.5:
                orient = "Coronal"

        if "t2" in desc_lower or "stir" in desc_lower:
            weighting = "T2"
        elif "t1" in desc_lower:
            weighting = "T1"
        else:
            weighting = "Unknown"

        # Z position of middle frame — used to sort axial series by spinal level.
        # In HFS positioning, higher Z = more superior (toward L1), lower Z = toward S1.
        z_center = 0.0
        try:
            sorted_files = sorted(
                files,
                key=lambda p: int(os.path.splitext(os.path.basename(p))[0]),
            )
        except ValueError:
            sorted_files = sorted(files)
        try:
            dcm_mid = pydicom.dcmread(
                sorted_files[len(sorted_files) // 2], stop_before_pixels=True
            )
            z_center = float(dcm_mid.ImagePositionPatient[2])
        except Exception:
            pass

        rows.append({
            "study_id": study_id,
            "series_id": series_id,
            "series_description": description,
            "orient": orient,
            "weighting": weighting,
            "study_series": f"{study_id}_{series_id}",
            "data_path": extract_path + "/",
            "z_center": z_center,
        })

    df_meta = pd.DataFrame(rows)

    # Normalise descriptions for level-2 model compatibility
    df_meta.loc[
        (df_meta.orient == "Sagittal") & (df_meta.weighting == "T2"),
        "series_description"
    ] = "Sagittal T2/STIR"
    df_meta.loc[
        (df_meta.orient == "Sagittal") & (df_meta.weighting == "T1"),
        "series_description"
    ] = "Sagittal T1"
    df_meta.loc[df_meta.orient == "Axial", "series_description"] = "Axial T2"

    return df_meta, extract_path


def convert_to_npy(df_meta, npy_dir: str) -> None:
    """Convert each DICOM series to a .npy array and save in npy_dir."""
    _setup_paths()
    from data.processing import read_series_metadata

    os.makedirs(npy_dir, exist_ok=True)
    for _, row in df_meta.iterrows():
        try:
            _, imgs = read_series_metadata(
                row["study_id"], row["series_id"], row["series_description"],
                data_path=row["data_path"],
            )
            try:
                imgs = np.array(imgs)
            except Exception:
                shapes = Counter([img.shape for img in imgs])
                shape = shapes.most_common()[0][0]
                imgs = np.array([
                    cv2.resize(img, (shape[1], shape[0])) if img.shape != shape else img
                    for img in imgs
                ])
            np.save(f"{npy_dir}/{row['study_series']}.npy", imgs)
        except Exception as e:
            print(f"Failed to convert {row['study_series']}: {e}")


def run_coords_prediction(models: dict, df_meta, npy_dir: str, device: str):
    """Run the coordinate localisation model on sagittal series."""
    _setup_paths()
    from data.transforms import get_transfos
    from data.dataset import CoordsDataset
    from inference.dataset import SafeDataset
    from inference.lvl1 import predict

    if "coords" not in models:
        return None, None

    model_sag, config_sag = models["coords"]
    df_sag = df_meta[df_meta["orient"] == "Sagittal"].copy().reset_index(drop=True)
    if df_sag.empty:
        return None, None

    df_sag["img_path"] = df_sag["study_series"].apply(lambda x: f"{npy_dir}/{x}.npy")
    df_sag["target"] = [np.ones((5, 2)) for _ in range(len(df_sag))]
    transfos = get_transfos(augment=False, resize=config_sag.resize, use_keypoints=True)
    dataset = SafeDataset(CoordsDataset(df_sag, transforms=transfos))
    preds_sag, _ = predict(
        model_sag, dataset, config_sag.loss_config,
        batch_size=4, device=device, num_workers=0,
    )
    return preds_sag, df_sag


def generate_crops(
    preds_sag: np.ndarray,
    df_sag,
    df_meta,
    npy_dir: str,
    crops_dir: str,
):
    """Crop each vertebral level region and build the per-level inference DataFrame."""
    os.makedirs(crops_dir, exist_ok=True)

    df_crop = df_meta.copy()
    df_crop["target"] = 0
    df_crop["level"] = [["L1/L2", "L2/L3", "L3/L4", "L4/L5", "L5/S1"] for _ in range(len(df_crop))]
    df_crop["level_"] = [LEVELS_ for _ in range(len(df_crop))]
    df_crop = df_crop.explode(["level", "level_"]).reset_index(drop=True)
    df_crop["img_path_"] = df_crop["study_series"] + "_" + df_crop["level_"] + ".npy"

    delta = 0.1
    crops_info = []
    n = min(len(df_sag), len(preds_sag))
    if n < len(df_sag):
        print(f"WARNING: preds_sag has {len(preds_sag)} entries but df_sag has {len(df_sag)}; truncating")
    for idx in range(n):
        study_series = df_sag["study_series"].iloc[idx]
        imgs = np.load(f"{npy_dir}/{study_series}.npy")
        preds = preds_sag[idx].reshape(-1, 2).copy()
        crops_info.append({
            "study_series": study_series,
            "coords": [{"x": float(c[0]), "y": float(c[1])} for c in preds],
        })
        boxes = np.concatenate([preds, preds], axis=-1)
        boxes[:, [0, 1]] -= delta
        boxes[:, [2, 3]] += delta
        boxes = boxes.clip(0, 1)
        boxes[:, [0, 2]] *= imgs.shape[2]
        boxes[:, [1, 3]] *= imgs.shape[1]
        boxes = boxes.astype(int)
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            crop = imgs[:, y0:y1, x0:x1].copy()
            if crop.shape[1] == 0 or crop.shape[2] == 0:
                crop = imgs.copy()
            np.save(f"{crops_dir}/{study_series}_{LEVELS_[i]}.npy", crop)

    return crops_info, df_crop


def run_classifiers(models: dict, df_crop, crops_dir: str, device: str) -> dict:
    """Run all four crop classification models and collect per-level logits."""
    _setup_paths()
    from data.transforms import get_transfos
    from data.dataset import CropDataset
    from inference.dataset import SafeDataset
    from inference.lvl1 import predict

    crop_fts: dict = {}
    for mode in ["crop", "crop_2", "scs_crop_coords", "scs_crop_coords_2"]:
        if mode not in models:
            continue
        m, cfg = models[mode]
        df_mode = df_crop.copy()
        if mode in ["crop", "crop_2"]:
            df_mode = df_mode[df_mode["orient"] == "Sagittal"].reset_index(drop=True)
        else:
            # Accept T2 and Unknown-weighted sagittal (DICOM description may not say "t2")
            df_mode = df_mode[
                (df_mode["orient"] == "Sagittal") & (df_mode["weighting"] != "T1")
            ].reset_index(drop=True)
        if df_mode.empty:
            continue
        df_mode["side"] = "Center"
        df_mode["img_path"] = df_mode["img_path_"].apply(lambda x: f"{crops_dir}/{x}")
        transfos = get_transfos(augment=False, resize=cfg.resize, crop=cfg.crop)
        ds = SafeDataset(CropDataset(
            df_mode, transforms=transfos,
            frames_chanel=cfg.frames_chanel, n_frames=cfg.n_frames, stride=cfg.stride,
        ))
        preds_cls, _ = predict(m, ds, cfg.loss_config, batch_size=8, device=device, num_workers=0)
        idx_list = [
            "_".join(i)
            for i in df_mode[["study_id", "series_id", "level", "side"]].values.astype(str).tolist()
        ]
        crop_fts[mode] = dict(zip(idx_list, preds_cls))
    return crop_fts


def run_level2(models: dict, df_meta, crop_fts: dict, device: str):
    """Run the level-2 aggregation model. Returns (softmax_preds, targets) or (None, None)."""
    _setup_paths()
    from inference.dataset import SafeDataset, FeatureInfDataset

    if "lvl2" not in models or not crop_fts:
        return None, None

    m2, cfg2 = models["lvl2"]
    df_2 = (
        df_meta[["study_id", "series_id", "series_description"]]
        .groupby("study_id")
        .agg(list)
        .reset_index()
    )
    for exp_key in cfg2.exp_folders.keys():
        crop_fts.setdefault(exp_key, {})

    ds2 = FeatureInfDataset(df_2, cfg2.exp_folders, crop_fts)
    loader2 = torch.utils.data.DataLoader(SafeDataset(ds2), batch_size=1)

    m2.eval()
    with torch.no_grad():
        for x_dict, _, _ in loader2:
            if not isinstance(x_dict, dict):
                return None, None
            logits, _ = m2({k: v.to(device) for k, v in x_dict.items()})
            preds = softmax(logits.detach().cpu().numpy(), axis=-1)
            targets = list(cfg2.targets) if hasattr(cfg2, "targets") else None
            return preds, targets
    return None, None


def format_results(
    final_preds,
    targets,
    crops_info: list,
) -> list:
    """
    Format model output into the API response structure.
    Uses targets list for correct index mapping instead of hardcoded offsets.
    """
    real_coords = crops_info[0]["coords"] if crops_info else None

    def get_severity(p: np.ndarray) -> dict:
        idx = int(np.argmax(p))
        return {"severity": SEVERITIES[idx], "confidence": round(float(p[idx]), 3)}

    def get_pred(key: str) -> np.ndarray:
        if targets and key in targets:
            return final_preds[0, targets.index(key)]
        print(f"WARNING: key '{key}' not found in targets; defaulting to Normal/Mild")
        return np.array([1.0, 0.0, 0.0])

    results = []
    for i, (level, level_) in enumerate(zip(LEVELS, LEVELS_)):
        coords = (
            real_coords[i]
            if real_coords and i < len(real_coords)
            else {"x": 0.5, "y": 0.2 + i * 0.1}
        )
        if final_preds is not None:
            entry = {
                "level": level.replace("/", "-"),
                "coordinates": coords,
                "spinal_canal_stenosis": get_severity(get_pred(f"spinal_canal_stenosis_{level_}")),
                "neural_foraminal_narrowing": {
                    "left": get_severity(get_pred(f"left_neural_foraminal_narrowing_{level_}")),
                    "right": get_severity(get_pred(f"right_neural_foraminal_narrowing_{level_}")),
                },
                "subarticular_stenosis": {
                    "left": get_severity(get_pred(f"left_subarticular_stenosis_{level_}")),
                    "right": get_severity(get_pred(f"right_subarticular_stenosis_{level_}")),
                },
            }
        else:
            default = {"severity": "Normal/Mild", "confidence": 0.0}
            entry = {
                "level": level.replace("/", "-"),
                "coordinates": coords,
                "spinal_canal_stenosis": default,
                "neural_foraminal_narrowing": {"left": default, "right": default},
                "subarticular_stenosis": {"left": default, "right": default},
            }
        results.append(entry)
    return results


def extract_images(df_meta, npy_dir: str) -> dict:
    """Extract the middle frame of each series type as a base64 JPEG data-URI."""
    images: dict = {"Sagittal T2": None, "Sagittal T1": None, "Axial T2": None}
    for _, row in df_meta.iterrows():
        key = None
        if row["orient"] == "Sagittal":
            if row["weighting"] == "T2" and images["Sagittal T2"] is None:
                key = "Sagittal T2"
            elif row["weighting"] == "T1" and images["Sagittal T1"] is None:
                key = "Sagittal T1"
            elif row["weighting"] == "Unknown":
                if images["Sagittal T2"] is None:
                    key = "Sagittal T2"
                elif images["Sagittal T1"] is None:
                    key = "Sagittal T1"
        elif row["orient"] == "Axial" and images["Axial T2"] is None:
            key = "Axial T2"
        if key:
            npy_path = f"{npy_dir}/{row['study_series']}.npy"
            if os.path.exists(npy_path):
                imgs = np.load(npy_path)
                mid = imgs[len(imgs) // 2].astype(np.float32)
                if mid.max() != mid.min():
                    mid = (mid - mid.min()) / (mid.max() - mid.min()) * 255
                _, buf = cv2.imencode(".jpg", mid.astype(np.uint8))
                images[key] = "data:image/jpeg;base64," + base64.b64encode(buf).decode()
    return images


def _frame_to_jpeg(frame: np.ndarray) -> str:
    """Normalise a raw grayscale frame and encode as base64 JPEG data-URI."""
    f = frame.astype(np.float32)
    pmin, pmax = np.percentile(f, (1, 99))
    if pmax > pmin:
        f = np.clip(f, pmin, pmax)
        f = (f - pmin) / (pmax - pmin) * 255
    else:
        f = (f - f.min()) / (f.max() - f.min() + 1e-6) * 255
    _, buf = cv2.imencode(".jpg", f.astype(np.uint8))
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def run_axial_coords_prediction(
    models: dict,
    df_meta,
    preds_sag: np.ndarray,
    npy_dir: str,
    device: str,
) -> list:
    """
    For each disc level, find the corresponding axial series (or frame within a
    single series) and run the axial localisation model.

    Clinical lumbar MRI typically has 5 separate axial series, each prescribed
    parallel to one disc. They are sorted by their Z-center (physical position):
    descending Z = superior → inferior = L1/L2 → L5/S1. Sagittal Y predictions
    are also ordered L1→L5 (ascending Y = more inferior). Both lists are matched
    by rank after sorting, then the middle frame of each matched series is used —
    exactly replicating the training data setup.

    Fallback for a single axial series: frame is selected by linearly mapping
    the sagittal Y prediction to the frame index.

    Returns a list of 5 dicts:
      {"level": "L1-L2", "image": "<data-uri>", "left": {x,y}, "right": {x,y}}
    Empty list if no axial data is available.
    """
    _setup_paths()

    df_ax = df_meta[df_meta["orient"] == "Axial"].copy().reset_index(drop=True)
    if df_ax.empty:
        return []

    # Sagittal Y for each level (L1→L5, ascending Y = more inferior)
    if preds_sag is not None and len(preds_sag) > 0:
        sag_coords = preds_sag[0].reshape(5, 2)  # (5, 2): (x, y) per level
    else:
        sag_coords = np.array([[0.5, 0.2 + i * 0.12] for i in range(5)])

    # Sort axial series by Z descending: highest Z = most superior = L1 end
    df_ax_sorted = df_ax.sort_values("z_center", ascending=False).reset_index(drop=True)
    N_ax = len(df_ax_sorted)

    # Disc levels ranked by sagittal Y ascending: rank 0 = smallest Y = most superior
    level_rank = np.argsort(sag_coords[:, 1])  # e.g. [0,1,2,3,4] for L1→L5

    has_ax_model = "coords_ax" in models

    results_by_level = {}
    for rank, level_idx in enumerate(level_rank):
        level = LEVELS[level_idx]

        if N_ax == 1:
            # Single combined axial series: select frame by sagittal Y mapping
            ax_npy = f"{npy_dir}/{df_ax_sorted.iloc[0]['study_series']}.npy"
            if not os.path.exists(ax_npy):
                continue
            ax_imgs = np.load(ax_npy)
            N = len(ax_imgs)
            if N == 0:
                continue
            y = float(sag_coords[level_idx, 1])
            # Y=0 (superior) → high frame index (high Z end); Y=1 → frame 0
            frame_idx = int(round((1.0 - y) * (N - 1)))
            frame = ax_imgs[max(0, min(N - 1, frame_idx))]
        else:
            # Multiple axial series: map rank proportionally to series index
            ax_idx = round(rank * (N_ax - 1) / max(1, len(LEVELS) - 1))
            ax_idx = min(ax_idx, N_ax - 1)
            ax_npy = f"{npy_dir}/{df_ax_sorted.iloc[ax_idx]['study_series']}.npy"
            if not os.path.exists(ax_npy):
                continue
            ax_imgs = np.load(ax_npy)
            if len(ax_imgs) == 0:
                continue
            frame = ax_imgs[len(ax_imgs) // 2]  # middle frame = disc-level frame

        image_b64 = _frame_to_jpeg(frame)

        if has_ax_model:
            model_ax, cfg_ax = models["coords_ax"]
            f = frame.astype(np.float32)
            pmin, pmax = np.percentile(f, (1, 99))
            if pmax > pmin:
                f = np.clip(f, pmin, pmax)
                f = (f - pmin) / (pmax - pmin)
            else:
                f = (f - f.min()) / (f.max() - f.min() + 1e-6)

            resize_h, resize_w = cfg_ax.resize
            f_resized = cv2.resize(f, (resize_w, resize_h))
            img_3ch = np.stack([f_resized] * 3, axis=0).astype(np.float32)  # (3, H, W)
            tensor = torch.from_numpy(img_3ch).unsqueeze(0).to(device)  # (1, 3, H, W)

            with torch.no_grad():
                y_pred, _ = model_ax(tensor)
                y_pred = torch.sigmoid(y_pred).cpu().numpy()[0]  # (4,)

            x_left, y_left, x_right, y_right = (float(v) for v in y_pred)
        else:
            x_left, y_left = 0.3, 0.5
            x_right, y_right = 0.7, 0.5

        results_by_level[level] = {
            "level": level.replace("/", "-"),
            "image": image_b64,
            "left": {"x": x_left, "y": y_left},
            "right": {"x": x_right, "y": y_right},
        }

    return [results_by_level[lvl] for lvl in LEVELS if lvl in results_by_level]
