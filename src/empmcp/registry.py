from __future__ import annotations

from fastmcp import FastMCP

from empmcp.config import Settings
from empmcp.middleware.authorisation import ToolAuthorizationMiddleware
from empmcp.middleware.rate_limiting import build_rate_limiter
from empmcp.middleware.logging import ToolCallLoggingMiddleware
from empmcp.tools.department_tools import get_department_statistics
from empmcp.tools.employee_tools import get_employee_details, search_employees
from empmcp.consts import TOOL_SCOPES

TOOLS = [
    get_employee_details,
    search_employees,
    get_department_statistics,
]


def register_middleware(mcp: FastMCP, settings: Settings) -> None:
    mcp.add_middleware(ToolCallLoggingMiddleware())
    mcp.add_middleware(ToolAuthorizationMiddleware(TOOL_SCOPES))
    mcp.add_middleware(build_rate_limiter(settings))


def register_tools(mcp: FastMCP) -> None:
    for tool_fn in TOOLS:
        mcp.tool(tool_fn, name=tool_fn.__name__, annotations={"readOnlyHint": True})


def register_all(mcp: FastMCP, settings: Settings) -> None:
    register_middleware(mcp, settings)
    register_tools(mcp)
