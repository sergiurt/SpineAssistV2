"""
Run once to download model weights from Kaggle into the Modal Volume.

Usage:
    modal run backend/setup.py

Prerequisites:
    1. pip install modal
    2. modal token new   (authenticate)
    3. Create Modal Secret named "kaggle-credentials" in the Modal dashboard
       with keys KAGGLE_USERNAME and KAGGLE_KEY
"""
import os
import subprocess
import modal

app = modal.App("spineassist-setup")
weights_volume = modal.Volume.from_name("spineassist-weights", create_if_missing=True)

setup_image = modal.Image.debian_slim().pip_install("kaggle")


@app.function(
    image=setup_image,
    volumes={"/weights": weights_volume},
    secrets=[modal.Secret.from_name("kaggle-credentials")],
    timeout=1800,
)
def download_weights():
    os.makedirs("/weights", exist_ok=True)

    if not os.path.exists("/weights/2024-08-29_0"):
        print("Downloading weights part 1...")
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", "theoviel/rsna-2024-weights-1",
             "-p", "/weights", "--unzip"],
            check=True,
        )
    else:
        print("Weights part 1 already present.")

    if not os.path.exists("/weights/2024-10-08_2"):
        print("Downloading weights part 2...")
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", "theoviel/rsna-2024-weights-2",
             "-p", "/weights", "--unzip"],
            check=True,
        )
    else:
        print("Weights part 2 already present.")

    weights_volume.commit()
    print("Volume committed. Done.")


@app.local_entrypoint()
def main():
    download_weights.remote()
