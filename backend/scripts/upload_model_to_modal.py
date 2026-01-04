#!/usr/bin/env python3
"""Upload existing local model to Modal Volume.

Usage:
    modal run scripts/upload_model_to_modal.py

This script uploads the local AutoGluon model from backend/models/place_predictor/
to the Modal Volume 'boonta-models' for use by the Modal ML functions.
"""

import os
import shutil
from pathlib import Path

import modal

# Configuration
LOCAL_MODEL_PATH = Path(__file__).parent.parent / "models" / "place_predictor"
VOLUME_NAME = "boonta-models"
REMOTE_MODEL_NAME = "place_predictor"

# Create Modal app for this script
app = modal.App("boonta-model-upload")

# Get or create the volume
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


@app.function(
    volumes={"/models": volume},
    timeout=300,
)
def upload_model_files(files_data: dict[str, bytes]) -> dict:
    """Upload model files to Modal Volume.

    Args:
        files_data: Dict mapping relative paths to file contents

    Returns:
        Dict with upload status
    """
    import os
    from pathlib import Path

    model_path = Path(f"/models/{REMOTE_MODEL_NAME}")

    # Create directory structure
    model_path.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    for rel_path, content in files_data.items():
        file_path = model_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(content)
        uploaded_files.append(str(rel_path))
        print(f"Uploaded: {rel_path}")

    # Commit the volume to persist changes
    volume.commit()

    # List uploaded files
    all_files = list(model_path.rglob("*"))

    return {
        "success": True,
        "uploaded_count": len(uploaded_files),
        "uploaded_files": uploaded_files,
        "total_files_in_volume": len([f for f in all_files if f.is_file()]),
    }


@app.function(
    volumes={"/models": volume},
    timeout=60,
)
def verify_model() -> dict:
    """Verify the uploaded model can be loaded."""
    from pathlib import Path

    model_path = Path(f"/models/{REMOTE_MODEL_NAME}")

    if not model_path.exists():
        return {"success": False, "error": "Model directory not found"}

    # List all files
    files = list(model_path.rglob("*"))
    file_list = [str(f.relative_to(model_path)) for f in files if f.is_file()]

    # Check for required files
    required_files = ["predictor.pkl", "learner.pkl", "metadata.json"]
    missing = [f for f in required_files if f not in file_list]

    if missing:
        return {
            "success": False,
            "error": f"Missing required files: {missing}",
            "found_files": file_list,
        }

    # Try to load with AutoGluon
    try:
        from autogluon.tabular import TabularPredictor
        predictor = TabularPredictor.load(str(model_path))

        return {
            "success": True,
            "message": "Model loaded successfully",
            "model_path": str(model_path),
            "file_count": len(file_list),
            "files": file_list[:20],  # First 20 files
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to load model: {e}",
            "files": file_list,
        }


@app.local_entrypoint()
def main():
    """Main entry point for uploading the model."""
    print(f"Uploading model from: {LOCAL_MODEL_PATH}")
    print(f"To Modal Volume: {VOLUME_NAME}/{REMOTE_MODEL_NAME}")
    print()

    if not LOCAL_MODEL_PATH.exists():
        print(f"ERROR: Local model not found at {LOCAL_MODEL_PATH}")
        return

    # Collect all files
    files_data = {}
    for file_path in LOCAL_MODEL_PATH.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(LOCAL_MODEL_PATH)
            with open(file_path, "rb") as f:
                files_data[str(rel_path)] = f.read()

    print(f"Found {len(files_data)} files to upload")
    print()

    # Upload files
    print("Uploading files to Modal Volume...")
    result = upload_model_files.remote(files_data)

    if result["success"]:
        print(f"Successfully uploaded {result['uploaded_count']} files")
        print()

        # Verify the upload
        print("Verifying uploaded model...")
        verify_result = verify_model.remote()

        if verify_result["success"]:
            print(f"Model verification successful!")
            print(f"Model path: {verify_result['model_path']}")
            print(f"Total files: {verify_result['file_count']}")
        else:
            print(f"Model verification failed: {verify_result.get('error')}")
            if "files" in verify_result:
                print(f"Files found: {verify_result['files']}")
    else:
        print(f"Upload failed: {result}")


if __name__ == "__main__":
    print("Run this script with: modal run scripts/upload_model_to_modal.py")
