"""Logging setup: structured JSON (default) or plain text.

Anything passed via ``extra={...}`` on a log call becomes a top-level JSON field.
The logging middleware also sets ``request_id_var`` for the duration of a tool
call, and a handler filter stamps that id on every record logged meanwhile
(service, database, ...), so one tool call can be traced across all its log lines.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

LOGGER_NAME = "empmcp"
_MAX_EXCEPTION_LENGTH = 500

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else came from ``extra``.
_STANDARD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            request_id = request_id_var.get()
            if request_id:
                record.request_id = request_id
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
            if record.exc_info:
                exception = self.formatException(record.exc_info)
                if len(exception) > _MAX_EXCEPTION_LENGTH:
                    marker = "\n... exception truncated ...\n"
                    available = _MAX_EXCEPTION_LENGTH - len(marker)
                    head_length = available // 2
                    tail_length = available - head_length
                    exception = (
                        exception[:head_length]
                        + marker
                        + exception[-tail_length:]
                    )
                payload["exception"] = exception
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", as_json: bool = True) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter()
        if as_json
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.handlers.clear()  # safe to call more than once
    logger.addHandler(handler)
    return logger


def get_logger(suffix: str | None = None) -> logging.Logger:
    """Child of the app logger, e.g. get_logger('db.pool') -> 'empmcp.db.pool'."""
    return logging.getLogger(f"{LOGGER_NAME}.{suffix}" if suffix else LOGGER_NAME)
