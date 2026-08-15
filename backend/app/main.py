from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health
from app.services import ingestion
from app.services import vectorstore as vs
from app.state import PaperMeta, app_state

settings = get_settings()


def _load_papers_metadata() -> dict[str, PaperMeta]:
    papers: dict[str, PaperMeta] = {}
    for chunk in ingestion.chunk_papers_in_dir(settings.papers_dir):
        meta = chunk.metadata
        entry = papers.setdefault(
            meta["paper_id"],
            PaperMeta(paper_id=meta["paper_id"], filename=meta["filename"]),
        )
        entry.num_chunks += 1
        entry.num_pages = max(entry.num_pages, meta["page"])
    return papers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build (or load a cached) FAISS index from the seeded corpus at startup.
    # With only 1-3 papers this is fast (seconds), so no persistence dependency
    # is required for the demo corpus to work on a fresh deploy.
    app_state.papers = _load_papers_metadata()

    store = vs.load_index(settings.faiss_index_dir)
    if store is None:
        chunks = ingestion.chunk_papers_in_dir(settings.papers_dir)
        if chunks:
            store = vs.build_index(chunks)
            vs.save_index(store, settings.faiss_index_dir)
    app_state.vectorstore = store

    yield


app = FastAPI(title="Research Paper Digest API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
