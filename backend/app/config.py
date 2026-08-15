from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
    generation_model: str = "claude-haiku-4-5-20251001"
    routing_model: str = "claude-haiku-4-5-20251001"
    ragas_judge_model: str = "claude-haiku-4-5-20251001"

    # Embeddings / re-ranking (local, zero-cost)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Retrieval
    top_k_retrieval: int = 8
    top_n_rerank: int = 4

    # Storage paths
    papers_dir: Path = BACKEND_ROOT / "app" / "data" / "papers"
    faiss_index_dir: Path = BACKEND_ROOT / "storage" / "faiss_index"
    logs_dir: Path = BACKEND_ROOT / "storage" / "logs"

    # CORS — accepts either a JSON array or a plain comma-separated string
    # (e.g. "http://localhost:3000,https://myapp.vercel.app"), since PaaS env
    # var dashboards typically don't support JSON-array-valued env vars cleanly.
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
