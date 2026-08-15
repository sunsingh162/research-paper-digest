import time
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.config import get_settings
from app.services import evaluation, pipeline
from app.state import app_state

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str


async def _score_and_log(
    query_id: str,
    question: str,
    answer: str,
    contexts: list[str],
    route_type: str,
    sub_queries: list[str],
    chunk_ids: list[str],
    pipeline_ms: int,
) -> None:
    """Runs after the response has already been sent -- RAGAS scoring (a handful
    of extra LLM calls) adds ~15-30s, which would blow well past a usable
    response time if the client had to wait on it. The score still gets logged
    per query as required; the client can poll GET /api/eval/logs to pick it up."""
    settings = get_settings()
    t0 = time.perf_counter()
    ragas_scores = await evaluation.score_live_query(question, answer, contexts)
    eval_ms = round((time.perf_counter() - t0) * 1000)

    evaluation.log_eval(
        {
            "timestamp": evaluation.now_iso(),
            "query_id": query_id,
            "question": question,
            "answer_preview": answer[:200],
            "route_type": route_type,
            "num_sub_queries": len(sub_queries),
            "retrieved_chunk_ids": chunk_ids,
            "faithfulness": ragas_scores["faithfulness"],
            "answer_relevancy": ragas_scores["answer_relevancy"],
            "context_precision": None,
            "context_precision_source": None,
            "latency_ms": {"pipeline_total": pipeline_ms, "eval": eval_ms},
            "generation_model": settings.generation_model,
            "judge_model": settings.ragas_judge_model,
        }
    )


@router.post("/query")
async def query(request: QueryRequest, background_tasks: BackgroundTasks) -> dict:
    if app_state.vectorstore is None:
        raise HTTPException(status_code=503, detail="No documents indexed yet. Upload a PDF first.")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty.")

    query_id = uuid.uuid4().hex

    t0 = time.perf_counter()
    # Runs in a thread: the pipeline does blocking network (Anthropic) and local
    # model (embeddings/cross-encoder) calls that would otherwise stall the loop.
    result = await run_in_threadpool(pipeline.answer_question, app_state.vectorstore, question)
    pipeline_ms = round((time.perf_counter() - t0) * 1000)

    contexts = [doc.page_content for doc in result.retrieved_documents]
    chunk_ids = [doc.metadata.get("chunk_id") for doc in result.retrieved_documents]

    # RAGAS scoring (faithfulness + answer_relevancy) is a handful of extra LLM
    # calls -- ~15-30s on top of the ~5-15s pipeline itself. Deferred to a
    # background task so the answer comes back promptly; still logged per query
    # (GET /api/eval/logs) as the assignment requires, just not inline here.
    background_tasks.add_task(
        _score_and_log,
        query_id,
        question,
        result.answer.answer,
        contexts,
        result.route_type,
        result.sub_queries,
        chunk_ids,
        pipeline_ms,
    )

    return {
        "query_id": query_id,
        "answer": result.answer.answer,
        "sources": [s.model_dump() for s in result.sources],
        "route_type": result.route_type,
        "sub_queries": result.sub_queries,
        "ragas": None,
        "ragas_pending": True,
        "latency_ms": {"pipeline_total": pipeline_ms},
    }
