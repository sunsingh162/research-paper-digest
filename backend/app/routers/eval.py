import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.services import evaluation
from app.state import app_state

router = APIRouter(prefix="/api/eval")


@router.post("/run")
async def run_eval() -> dict:
    if app_state.vectorstore is None:
        raise HTTPException(status_code=503, detail="No documents indexed yet.")
    return await evaluation.run_golden_eval(app_state.vectorstore)


def _tail_jsonl(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]


@router.get("/logs")
def get_eval_logs(limit: int = 50) -> list[dict]:
    settings = get_settings()
    return _tail_jsonl(settings.logs_dir / "eval_log.jsonl", limit)


@router.get("/rerank-log")
def get_rerank_log(limit: int = 20) -> list[dict]:
    settings = get_settings()
    return _tail_jsonl(settings.logs_dir / "rerank_log.jsonl", limit)
