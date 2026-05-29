"""Application logging helpers."""
import logging
from contextvars import ContextVar


request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject the active request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get() or "-"
        return True


def configure_logging() -> logging.Logger:
    """Configure the application logger once and return it."""
    logger = logging.getLogger("email_context_service")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [ReqID: %(request_id)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the configured app logger or one of its children."""
    configure_logging()
    if name:
        return logging.getLogger(f"email_context_service.{name}")
    return logging.getLogger("email_context_service")
