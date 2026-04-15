from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = [item.strip() for item in raw.split(",")]
    return [item for item in values if item]


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: list[str]
    app_log_level: str
    app_log_file_path: str
    pipeline_log_storage_path: str
    pipeline_log_db_api_url: str
    pipeline_log_db_api_path: str
    pipeline_log_forward_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./threat_copilot.db"),
        cors_origins=_list_env(
            "FRONTEND_CORS_ORIGINS",
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        ),
        app_log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
        app_log_file_path=os.getenv("APP_LOG_FILE_PATH", "./runtime_logs/app/app.log"),
        pipeline_log_storage_path=os.getenv(
            "PIPELINE_LOG_STORAGE_PATH", "./runtime_logs/pipeline"
        ),
        pipeline_log_db_api_url=os.getenv("PIPELINE_LOG_DB_API_URL", "").strip(),
        pipeline_log_db_api_path=os.getenv(
            "PIPELINE_LOG_DB_API_PATH", "/pipeline/logs"
        ).strip(),
        pipeline_log_forward_enabled=_bool_env(
            "PIPELINE_LOG_FORWARD_ENABLED", default=True
        ),
    )
