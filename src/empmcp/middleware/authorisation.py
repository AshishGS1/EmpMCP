"""Per-tool scope checks, and publication of the caller for the rest of the call.

Scopes are enforced here instead of with FastMCP's per-tool ``auth=``. With that,
a caller lacking the scope gets "Unknown tool", which is hard to diagnose and cannot
be logged as a 403 with the caller's identity. Here a denial is an explicit
``[403 PERMISSION_DENIED]`` naming the missing scope.

Fails closed: with auth enabled, a tool missing from the policy map is not callable
(this also means an unknown tool name answers 403, not 404).
"""

from __future__ import annotations

from typing import Iterable, Mapping

from fastmcp.server.middleware import Middleware

from empmcp.auth import caller_var, identify_caller
from empmcp.exceptions import AuthenticationError, PermissionDeniedError


class ToolAuthorizationMiddleware(Middleware):
    def __init__(self, tool_scopes: Mapping[str, Iterable[str]]) -> None:
        self._tool_scopes = {tool: frozenset(s) for tool, s in tool_scopes.items()}
    async def on_call_tool(self, context, call_next):
        tool = context.message.name
        caller = identify_caller()
        if caller is None:
            # Real HTTP requests without a valid token are stopped earlier with 401
            raise AuthenticationError("Authentication is required to call tools")

        required = self._tool_scopes.get(tool)
        if required is None:
            raise PermissionDeniedError(
                f"No access policy is defined for tool '{tool}'",
                details={"tool": tool},
            )
        missing = required - caller.scopes
        if missing:
            raise PermissionDeniedError(
                f"Missing required scope(s) for {tool}: "
                f"{', '.join(sorted(missing))}",
                details={
                    "tool": tool,
                    "required_scopes": sorted(required),
                    "missing_scopes": sorted(missing),
                },
            )

        token = caller_var.set(caller)
        try:
            return await call_next(context)
        finally:
            caller_var.reset(token)