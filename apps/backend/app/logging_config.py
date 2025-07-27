import os
import logging
from logging.handlers import RotatingFileHandler

import structlog

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENV = os.getenv("ENV", "dev").lower()

os.makedirs("logs", exist_ok=True)
log_file = os.path.join("logs", "backend.log")

handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(message)s",
    handlers=[handler, logging.StreamHandler()],
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
