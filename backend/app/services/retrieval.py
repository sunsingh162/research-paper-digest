"""Multi-sub-query retrieval: run similarity search per sub-query and merge,
deduping by chunk_id and keeping each chunk's best score across sub-queries."""

from __future__ import annotations

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import get_settings
from app.services.vectorstore import query_index


def retrieve_merged(
    store: FAISS, sub_queries: list[str], k: int | None = None
) -> list[tuple[Document, float]]:
    """Retrieve top-k per sub-query, merge across sub-queries, dedupe by chunk_id
    keeping the best score seen, sorted descending (higher = more similar)."""
    settings = get_settings()
    top_k = k or settings.top_k_retrieval

    best_by_chunk: dict[str, tuple[Document, float]] = {}
    for sub_query in sub_queries:
        for doc, score in query_index(store, sub_query, k=top_k):
            chunk_id = doc.metadata.get("chunk_id")
            existing = best_by_chunk.get(chunk_id)
            if existing is None or score > existing[1]:
                best_by_chunk[chunk_id] = (doc, score)

    return sorted(best_by_chunk.values(), key=lambda pair: pair[1], reverse=True)
