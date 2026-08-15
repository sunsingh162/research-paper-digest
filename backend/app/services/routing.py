"""Query routing/decomposition: one structured-output Claude call that classifies
the query and, for multi-part questions, decomposes it into atomic sub-queries."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import get_settings

SYSTEM_PROMPT = """You classify questions about research papers and, when needed, break them \
into atomic sub-questions for retrieval.

query_type:
- "single_fact": one focused question with a single, direct answer.
- "multi_part": the question asks about two or more distinct things (e.g. joined with "and", \
"vs", "compare", or containing multiple question words).
- "summarization": asks for an overview/summary of a paper or section, not a specific fact.

sub_queries:
- For "single_fact" and "summarization": a list containing just the original question, unchanged.
- For "multi_part": break the question into 2+ atomic, independently-searchable sub-questions, \
each retrievable on its own. Preserve the original meaning; don't add new claims."""

USER_PROMPT = "Question: {question}"

_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", USER_PROMPT)])


class RouteDecision(BaseModel):
    query_type: Literal["single_fact", "multi_part", "summarization"]
    sub_queries: list[str] = Field(min_length=1)


@lru_cache
def _build_structured_llm():
    settings = get_settings()
    llm = ChatAnthropic(
        model=settings.routing_model,
        api_key=settings.anthropic_api_key,
        temperature=0,
        max_tokens=512,
    )
    return llm.with_structured_output(RouteDecision, method="json_schema")


def classify_and_decompose(question: str) -> RouteDecision:
    chain = _prompt | _build_structured_llm()
    return chain.invoke({"question": question})
