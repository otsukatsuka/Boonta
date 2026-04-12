"""Modal container image definition for AutoGluon ML environment."""
import modal

autogluon_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgomp1")
    .pip_install(
        "autogluon.tabular[all]==1.4.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    )
)

model_volume = modal.Volume.from_name("boonta-models", create_if_missing=True)
VOLUME_PATH = "/models"
