"""Modal Image configuration for Boonta ML."""

import modal

# Modal Image with Python 3.12 and AutoGluon 1.5.0
autogluon_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgomp1")  # Required for AutoGluon
    .pip_install(
        "autogluon.tabular==1.5.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
    )
)

# Modal Volume for persistent model storage
model_volume = modal.Volume.from_name("boonta-models", create_if_missing=True)
VOLUME_PATH = "/models"
