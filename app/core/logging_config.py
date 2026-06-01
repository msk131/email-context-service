"""Application logging helpers."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject the active request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render logs as structured JSON for production log pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> logging.Logger:
    """Configure the application logger once and return it."""
    logger = logging.getLogger("email_context_service")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the configured app logger or one of its children."""
    configure_logging()
    if name:
        return logging.getLogger(f"email_context_service.{name}")
    return logging.getLogger("email_context_service")
