"""Structured logging for every tool call.

Per call it logs a "started" line and a "completed"/"failed" line carrying: a
request_id (also stamped on every log line the call causes further down, such as
service and database logs), tool name, redacted arguments, duration, status, and
for failures the error code and type.

Named request_logging.py rather than logging.py so it cannot shadow the stdlib.
"""


import time
import uuid
from http import HTTPStatus
from typing import Any, Mapping

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware

from empmcp.auth import caller_label, identify_jti
from empmcp.exceptions import EmpMCPError
from empmcp.utils.logging_config import get_logger, request_id_var
from empmcp.utils.tool_logging import (
    log_tool_call,
    log_tool_failure,
    log_tool_success,
)

logger = get_logger("tools")

_SENSITIVE_KEY_PARTS = ("password", "secret", "token", "authorization", "api_key")
_MAX_ARG_LENGTH = 100


def redact_arguments(arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    """Mask secret-looking values and truncate long strings before logging."""
    redacted: dict[str, Any] = {}
    for key, value in (arguments or {}).items():
        if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS):
            redacted[key] = "***"
        elif isinstance(value, str) and len(value) > _MAX_ARG_LENGTH:
            redacted[key] = value[:_MAX_ARG_LENGTH] + "..."
        else:
            redacted[key] = value
    return redacted



class ToolCallLoggingMiddleware(Middleware):
    async def on_call_tool(self, context, call_next):
        request_id = uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        tool = context.message.name
        caller=caller_label()
        jti=identify_jti()
        started = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started) * 1000, 2)

        log_tool_call(logger, tool, request_id, caller, redact_arguments(context.message.arguments), jti)
        try:
            result = await call_next(context)
        except EmpMCPError as exc:
            log_tool_failure(
                logger, tool, request_id, caller, elapsed_ms(),
                code=exc.code, status=exc.http_status,
                message=exc.message, error_type=type(exc).__name__, jti=jti,
            )
            raise
        except ToolError as exc:
            # Errors FastMCP itself raises as ToolError, e.g. bad argument types
            log_tool_failure(
                logger, tool, request_id, caller, elapsed_ms(),
                code="TOOL_ERROR", status=HTTPStatus.BAD_REQUEST,
                message=str(exc), error_type=type(exc).__name__, jti=jti,
            )
            raise
        except Exception as exc:
            log_tool_failure(
                logger, tool, request_id, caller, elapsed_ms(),
                code="UNEXPECTED_ERROR", status=HTTPStatus.INTERNAL_SERVER_ERROR,
                message=str(exc), error_type=type(exc).__name__, jti=jti, exc=exc, 
            )
            raise
        else:
            log_tool_success(logger, tool, request_id, caller, elapsed_ms(), jti)
            return result
        finally:
            request_id_var.reset(token)
