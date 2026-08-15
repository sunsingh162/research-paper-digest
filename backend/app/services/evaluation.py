"""RAGAS evaluation: faithfulness + answer_relevancy computed on every live query
(both are reference-free metrics -- they work without a ground-truth answer, so
they're safe to run on real user questions); context_precision only in the
golden-set batch path, since it requires a reference answer a live query doesn't
have. Every score is logged to eval_log.jsonl.

Implementation notes (ragas 0.4.3, verified against the actually-installed
package rather than assumed -- see PROGRESS.md for the full investigation):

- ragas.evaluate()/aevaluate() are avoided in favor of the newer per-metric async
  ascore() API in ragas.metrics.collections (Faithfulness, AnswerRelevancy,
  ContextPrecisionWithReference) -- also a better fit for logging per query.
- ragas.llms.llm_factory(provider="anthropic") needs a client with async support
  (anthropic.AsyncAnthropic) -- ascore()/agenerate() raise at call time on a sync
  client.
- WORKAROUND: ragas's InstructorLLM always sends both `temperature` and `top_p`
  to the provider by default (InstructorModelArgs). Current Claude models reject
  that combination outright (and claude-sonnet-5 deprecates `temperature`
  entirely), so the constructed LLM's `model_args` is overwritten post-construction
  down to just `{"max_tokens": ...}`, falling back to Claude's own default
  sampling. There's no public llm_factory parameter to omit these individually.
- ragas depends on `langchain-community` with no upper bound; the installed
  latest (0.4.2) removed `langchain_community.chat_models.vertexai`, which
  ragas.llms.base imports unconditionally at module load (purely to support the
  legacy, now-deprecated LangchainLLMWrapper path we don't even use) -- this
  breaks importing ragas at all. Pinned langchain-community==0.3.31 as the fix;
  our own FAISS usage (vectorstore.py) is unaffected by this pin.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, ContextPrecisionWithReference, Faithfulness

from app.config import get_settings

GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent / "data" / "golden_eval_set.json"


@lru_cache
def _get_ragas_llm():
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    llm = llm_factory(settings.ragas_judge_model, provider="anthropic", client=client)
    # See module docstring: current Claude models reject temperature+top_p together.
    # max_tokens raised from the ragas default (1024) -- faithfulness's NLI-verdict
    # step can emit enough statements+explanations to hit that ceiling and truncate.
    llm.model_args = {"max_tokens": 4096}
    return llm


@lru_cache
def _get_ragas_embeddings():
    settings = get_settings()
    return RagasHFEmbeddings(model=settings.embedding_model)


@lru_cache
def _get_faithfulness():
    return Faithfulness(llm=_get_ragas_llm())


@lru_cache
def _get_answer_relevancy():
    return AnswerRelevancy(llm=_get_ragas_llm(), embeddings=_get_ragas_embeddings())


@lru_cache
def _get_context_precision():
    return ContextPrecisionWithReference(llm=_get_ragas_llm())


async def score_live_query(question: str, answer: str, contexts: list[str]) -> dict[str, float | None]:
    """faithfulness + answer_relevancy -- reference-free, safe on live traffic."""
    if not contexts:
        return {"faithfulness": None, "answer_relevancy": None}
    faithfulness_result = await _get_faithfulness().ascore(
        user_input=question, response=answer, retrieved_contexts=contexts
    )
    relevancy_result = await _get_answer_relevancy().ascore(user_input=question, response=answer)
    return {
        "faithfulness": faithfulness_result.value,
        "answer_relevancy": relevancy_result.value,
    }


async def score_context_precision(question: str, reference: str, contexts: list[str]) -> float:
    """Requires a reference answer -- golden-set batch path only."""
    result = await _get_context_precision().ascore(
        user_input=question, reference=reference, retrieved_contexts=contexts
    )
    return result.value


def log_eval(entry: dict[str, Any]) -> None:
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.logs_dir / "eval_log.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_golden_set() -> list[dict[str, str]]:
    return json.loads(GOLDEN_SET_PATH.read_text())


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


async def run_golden_eval(store) -> dict[str, Any]:
    """Run the full pipeline against the golden Q&A set, scoring all three RAGAS
    metrics (context_precision only possible here, since it needs a reference).
    Logs each item to eval_log.jsonl and returns an aggregate + per-item summary.
    """
    from app.services import pipeline  # local import: avoids a circular import with generation/routing

    per_item = []
    for item in load_golden_set():
        question, reference = item["question"], item["reference"]
        result = pipeline.answer_question(store, question)
        contexts = [doc.page_content for doc in result.retrieved_documents]

        live_scores = await score_live_query(question, result.answer.answer, contexts)
        context_precision = await score_context_precision(question, reference, contexts)

        entry = {
            "timestamp": now_iso(),
            "question": question,
            "answer_preview": result.answer.answer[:200],
            "route_type": result.route_type,
            "num_sub_queries": len(result.sub_queries),
            "retrieved_chunk_ids": [doc.metadata.get("chunk_id") for doc in result.retrieved_documents],
            "faithfulness": live_scores["faithfulness"],
            "answer_relevancy": live_scores["answer_relevancy"],
            "context_precision": context_precision,
            "context_precision_source": "golden_set",
        }
        log_eval(entry)
        per_item.append(entry)

    def _avg(key: str) -> float | None:
        values = [e[key] for e in per_item if e[key] is not None]
        return sum(values) / len(values) if values else None

    aggregate = {
        "faithfulness": _avg("faithfulness"),
        "answer_relevancy": _avg("answer_relevancy"),
        "context_precision": _avg("context_precision"),
        "num_items": len(per_item),
    }
    return {"aggregate": aggregate, "per_item": per_item}
