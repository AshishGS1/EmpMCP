"""Global rate limiting for tool calls only.

Only ``on_call_tool`` is overridden, so initialize / list_tools / pings are never
throttled. One limit is shared by every client (global scope). Rejected calls do
not count against the window.
"""

from __future__ import annotations

from fastmcp.server.middleware.rate_limiting import (
    RateLimitError,
    RateLimitingMiddleware,
)

from empmcp.config import Settings
from empmcp.exceptions import RateLimitExceededError


class ToolCallRateLimiter(RateLimitingMiddleware):
    async def on_request(self, context, call_next):
        # Let everything except tool calls through untouched.
        return await call_next(context)

    async def on_call_tool(self, context, call_next):
        # Just scoped to tool calls.
        try:
            return await super().on_request(context, call_next)
        except RateLimitError as exc:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {self.max_requests_per_second:g} calls/second ",
                details={
                    "max_requests_per_second": self.max_requests_per_second,
                },
            ) from exc


def build_rate_limiter(settings: Settings) -> ToolCallRateLimiter:
    return ToolCallRateLimiter(
        max_requests_per_second=settings.rate_lim_rps,
        global_limit=True,
    )