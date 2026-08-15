from fastapi import APIRouter

from app.state import app_state

router = APIRouter(prefix="/api")


@router.get("/papers")
def list_papers() -> list[dict]:
    return [
        {
            "paper_id": p.paper_id,
            "filename": p.filename,
            "num_pages": p.num_pages,
            "num_chunks": p.num_chunks,
        }
        for p in app_state.papers.values()
    ]
