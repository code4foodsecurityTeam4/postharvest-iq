"""
ML metadata endpoint — exposes model_metadata.json over HTTP so the Streamlit
dashboard can display model performance without direct filesystem access.
"""

import json
from fastapi import APIRouter, HTTPException
from app.ml.config import METADATA_PATH

router = APIRouter()


@router.get("/metadata")
def get_model_metadata():
    """Return the full model_metadata.json produced by the training scripts."""
    try:
        with open(METADATA_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Model metadata not found. Run training scripts first."
        )
