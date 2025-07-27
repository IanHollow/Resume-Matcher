import os
import sys
import logging
from logging.handlers import RotatingFileHandler

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Literal


class Settings(BaseSettings):
    PROJECT_NAME: str = "Resume Matcher"
    FRONTEND_PATH: str = os.path.join(os.path.dirname(__file__), "frontend", "assets")
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    SYNC_DATABASE_URL: Optional[str]
    ASYNC_DATABASE_URL: Optional[str]
    SESSION_SECRET_KEY: Optional[str]
    DB_ECHO: bool = False
    PYTHONDONTWRITEBYTECODE: int = 1
    EMBED_PATH: str = "Qwen3-Embedding-8B.Q4_0.gguf"
    RERANK_PATH: str = "Qwen3-Reranker-0.6B-Q8_0.safetensors"
    LLAMA_ARGS: str = ""
    ENABLE_RERANK: bool = False
    PARSER_MODEL_PATH: str = "resume-parser.bin"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENV = os.getenv("ENV", "dev").lower()


_LEVEL_BY_ENV: dict[Literal["production", "staging", "local"], int] = {
    "production": logging.INFO,
    "staging": logging.DEBUG,
    "local": logging.DEBUG,
}


def setup_logging() -> None:
    """
    Configure the root logger exactly once,

    * Console only (StreamHandler -> stderr)
    * ISO - 8601 timestamps
    * Env - based log level: production -> INFO, else DEBUG
    * Prevents duplicate handler creation if called twice
    """
    root = logging.getLogger()
    if root.handlers:
        return

    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", "backend.log")

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    console_handler = logging.StreamHandler(sys.stderr)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(message)s",
        handlers=[file_handler, console_handler],
    )

    renderer = (
        structlog.processors.JSONRenderer()
        if ENV == "prod"
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, LOG_LEVEL, logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    for noisy in ("sqlalchemy.engine", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
