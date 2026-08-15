from fastapi import APIRouter

from app.state import app_state

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "index_loaded": app_state.index_loaded,
        "num_chunks": app_state.num_chunks,
        "num_papers": len(app_state.papers),
    }
