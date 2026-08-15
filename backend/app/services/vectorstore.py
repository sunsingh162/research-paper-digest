"""FAISS vector store: build from documents, persist to disk, reload, and extend.

Uses langchain_community's FAISS integration. Note: langchain-community is in a
long-term deprecation/sunset process in favor of standalone integration packages,
but the standalone `langchain-faiss` package on PyPI is still an empty placeholder
as of this writing (checked: exports nothing usable) -- langchain_community.FAISS
remains the only working option and is still fully functional, just noisy about it.
"""

from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

from app.services.embeddings import get_embeddings

_INDEX_FILE = "index.faiss"


def build_index(documents: list[Document]) -> FAISS:
    """Build a fresh FAISS index. Embeddings are normalized (see embeddings.py),
    so MAX_INNER_PRODUCT is equivalent to cosine similarity."""
    return FAISS.from_documents(
        documents,
        get_embeddings(),
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
    )


def save_index(store: FAISS, index_dir: Path) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_dir))


def load_index(index_dir: Path) -> FAISS | None:
    if not (index_dir / _INDEX_FILE).exists():
        return None
    # Safe: we only ever load an index this app itself wrote via save_index above.
    return FAISS.load_local(
        str(index_dir),
        get_embeddings(),
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        allow_dangerous_deserialization=True,
    )


def add_documents(store: FAISS, documents: list[Document]) -> list[str]:
    return store.add_documents(documents)


def query_index(store: FAISS, question: str, k: int = 8) -> list[tuple[Document, float]]:
    """Top-k chunks with similarity scores (higher = more similar, since we use
    normalized embeddings + MAX_INNER_PRODUCT)."""
    return store.similarity_search_with_score(question, k=k)
