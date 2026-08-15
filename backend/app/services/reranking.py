"""Cross-encoder re-ranking of FAISS-retrieved candidates. Every call logs the
pre-rerank (FAISS bi-encoder) and post-rerank (cross-encoder) ordering to
rerank_log.jsonl -- this is the README's required before/after evidence."""

from __future__ import annotations

import json
import time
import uuid
from functools import lru_cache

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from app.config import get_settings


@lru_cache
def _get_cross_encoder() -> CrossEncoder:
    settings = get_settings()
    return CrossEncoder(settings.cross_encoder_model)


def rerank(
    question: str,
    candidates: list[tuple[Document, float]],
    top_n: int | None = None,
    query_id: str | None = None,
) -> list[tuple[Document, float]]:
    """Rescore candidates with a cross-encoder, log pre/post ordering, return top_n."""
    settings = get_settings()
    n = top_n or settings.top_n_rerank

    if not candidates:
        return []

    pre_order = [
        {
            "chunk_id": doc.metadata.get("chunk_id"),
            "page": doc.metadata.get("page"),
            "faiss_score": round(float(score), 4),
            "rank": i + 1,
        }
        for i, (doc, score) in enumerate(candidates)
    ]

    pairs = [(question, doc.page_content) for doc, _ in candidates]
    ce_scores = _get_cross_encoder().predict(pairs)

    rescored = sorted(
        zip((doc for doc, _ in candidates), ce_scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    post_order = [
        {
            "chunk_id": doc.metadata.get("chunk_id"),
            "page": doc.metadata.get("page"),
            "cross_encoder_score": round(float(score), 4),
            "rank": i + 1,
        }
        for i, (doc, score) in enumerate(rescored)
    ]

    pre_rank_by_id = {entry["chunk_id"]: entry["rank"] for entry in pre_order}
    rank_changes = [
        {
            "chunk_id": entry["chunk_id"],
            "old_rank": pre_rank_by_id.get(entry["chunk_id"]),
            "new_rank": entry["rank"],
        }
        for entry in post_order
        if pre_rank_by_id.get(entry["chunk_id"]) != entry["rank"]
    ]

    _log_rerank(question, pre_order, post_order, rank_changes, query_id)

    return [(doc, float(score)) for doc, score in rescored[:n]]


def _log_rerank(
    question: str,
    pre_order: list[dict],
    post_order: list[dict],
    rank_changes: list[dict],
    query_id: str | None,
) -> None:
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "query_id": query_id or uuid.uuid4().hex,
        "question": question,
        "pre_rerank_order": pre_order,
        "post_rerank_order": post_order,
        "rank_changes": rank_changes,
    }
    log_path = settings.logs_dir / "rerank_log.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
