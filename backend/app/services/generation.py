"""LCEL generation chain: prompt -> Claude, with structured, citation-honest output.

This module owns just the "generate an answer from already-retrieved context" stage.
Retrieval, routing/decomposition, and re-ranking (services/retrieval.py,
services/routing.py, services/reranking.py) run upstream and hand this module a
final list of Documents to answer from.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.models.schemas import GenerationOutput, SourceChunk

SYSTEM_PROMPT = """You are a research paper assistant. Answer the user's question using ONLY the \
provided context chunks below -- never use outside knowledge, even if you know the answer.

Rules:
- If the context does not contain the answer, say so explicitly (e.g. "This isn't covered in the \
provided document(s).") instead of guessing or filling gaps with general knowledge.
- Every claim in your answer must be traceable to one or more of the provided chunks.
- In `cited_chunk_ids`, list the chunk_id values (shown in each context block's header) of the \
specific chunks you actually drew on. Leave it empty if you could not answer from the context.
- Be concise and precise -- this is a technical research-paper Q&A tool, not a chat assistant."""

USER_PROMPT = """Question: {question}

Context:
{context}"""

_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", USER_PROMPT)])


@lru_cache
def _build_structured_llm():
    settings = get_settings()
    llm = ChatAnthropic(
        model=settings.generation_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=1024,
    )
    return llm.with_structured_output(GenerationOutput, method="json_schema")


def format_context(documents: list[Document]) -> str:
    if not documents:
        return "(no relevant context found)"
    blocks = []
    for doc in documents:
        meta = doc.metadata
        header = (
            f"[chunk_id={meta.get('chunk_id')} | paper={meta.get('paper_id')} "
            f"| page={meta.get('page')} | section={meta.get('section') or 'n/a'}]"
        )
        blocks.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(blocks)


def build_generation_chain():
    return _prompt | _build_structured_llm()


def generate_answer(question: str, documents: list[Document]) -> tuple[GenerationOutput, list[SourceChunk]]:
    """Run generation given already-retrieved (and, ideally, reranked) documents.

    Returns the raw structured output plus resolved SourceChunk objects built from
    the actual Document metadata for whichever chunk_ids the model cited.
    """
    chain = build_generation_chain()
    context = format_context(documents)
    result: GenerationOutput = chain.invoke({"question": question, "context": context})

    by_id = {doc.metadata.get("chunk_id"): doc for doc in documents}
    sources = [
        SourceChunk(
            chunk_id=chunk_id,
            paper_id=doc.metadata.get("paper_id", ""),
            page=doc.metadata.get("page", 0),
            section=doc.metadata.get("section"),
            snippet=doc.page_content[:280],
        )
        for chunk_id in result.cited_chunk_ids
        if (doc := by_id.get(chunk_id)) is not None
    ]
    return result, sources
