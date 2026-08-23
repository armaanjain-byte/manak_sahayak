from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # RAGFlow connection — must be set in environment before production use.
    # No defaults: fail fast if a consumer tries to use the client without config.
    ragflow_base_url: str = "http://localhost"
    ragflow_api_key: str = ""
    # The RAGFlow dataset/knowledge-base ID to search against.
    ragflow_dataset_id: str = ""

    # Postgres connection — also used by Alembic (alembic.ini reads from env).
    database_url: str = "sqlite:///./test.db"

    # LLM configuration (Phase 10: generation and actions)
    llm_api_key: str = ""
    llm_model: str = "claude-3-5-sonnet-20241022"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Use this everywhere instead of
    constructing Settings() directly so we read the env file only once."""
    return Settings()
