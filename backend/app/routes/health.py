from fastapi import APIRouter
from app.services.model_service import model, threshold

router = APIRouter()

@router.get("/health")
def health_check():

    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "threshold": threshold
    }