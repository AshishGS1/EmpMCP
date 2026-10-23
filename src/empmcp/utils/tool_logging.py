"""One-line, grep-friendly tool-call logs in key=value style."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any, Mapping


def log_tool_call(
    log: logging.Logger, tool: str, request_id: str, caller: str, arguments: Mapping[str, Any], jti: str = '-',
) -> None:
    """One line when a tool is invoked, so the terminal shows what ran."""
    log.info(
        "Tool called.",
        extra={
            "event": "tool_call_started",
            "request_id": request_id,
            "jti": jti,
            "caller": caller,
            "tool": tool,
            "arguments": dict(arguments),
        },
    )


def log_tool_success(
    log: logging.Logger, tool: str, request_id: str, caller: str, duration_ms: float, jti: str = '-',
) -> None:
    log.info(
        "Tool call completed.",
        extra={
            "event": "tool_call_completed",
            "request_id": request_id,
            "jti": jti,
            "caller": caller,
            "tool": tool,
            "status": "ok",
            "http_status": 200,
            "duration_ms": duration_ms,
        },
    )


def log_tool_failure(
    log: logging.Logger,
    tool: str,
    request_id: str,
    caller: str,
    duration_ms: float,
    *,
    code: str,
    status: HTTPStatus,
    message: str,
    error_type: str,
    exc: BaseException | None = None,
    jti: str = '-',
) -> None:
    """4xx logs as WARNING (the caller's mistake), 5xx as ERROR. A traceback is
    attached only when ``exc`` is given (unexpected exceptions)."""
    level = logging.WARNING if int(status) < 500 else logging.ERROR
    log.log(
        level,
        "Tool call failed.",
        extra={
            "event": "tool_call_failed",
            "request_id": request_id,
            "jti": jti,
            "caller": caller,
            "tool": tool,
            "status": "error",
            "http_status": int(status),
            "duration_ms": duration_ms,
            "error_code": code,
            "error_type": error_type,
            "error_message": message,
        },
        exc_info=exc,
    )


def _fmt(fields: Mapping[str, Any]) -> str:
    # repr() quotes strings, so values containing spaces stay unambiguous
    return " ".join(f"{key}={value!r}" for key, value in fields.items())