"""End-to-end RAG pipeline: route -> multi-query retrieve -> rerank -> generate.

This is the composition described in the architecture: routing, multi-query
retrieval, and re-ranking form the retrieval stage feeding into the
prompt | ChatAnthropic LCEL chain in generation.py. Kept as a plain function
composing the service modules (rather than folding everything into one literal
RunnableSequence) because each stage has its own side effects (rerank logging)
and is independently testable -- see PROGRESS.md for the fuller rationale.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import get_settings
from app.models.schemas import GenerationOutput, SourceChunk
from app.services import generation, reranking, retrieval, routing


@dataclass
class PipelineResult:
    answer: GenerationOutput
    sources: list[SourceChunk]
    route_type: str
    sub_queries: list[str]
    retrieved_documents: list[Document]  # post-rerank; also used as RAGAS contexts


def answer_question(store: FAISS, question: str) -> PipelineResult:
    settings = get_settings()
    route = routing.classify_and_decompose(question)
    candidates = retrieval.retrieve_merged(store, route.sub_queries, k=settings.top_k_retrieval)
    reranked = reranking.rerank(question, candidates, top_n=settings.top_n_rerank)
    documents = [doc for doc, _ in reranked]

    result, sources = generation.generate_answer(question, documents)

    return PipelineResult(
        answer=result,
        sources=sources,
        route_type=route.query_type,
        sub_queries=route.sub_queries,
        retrieved_documents=documents,
    )
