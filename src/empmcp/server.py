"""Builds the FastMCP server and runs it over streamable HTTP."""


import sys

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from empmcp.auth import build_token_verifier
from empmcp.config import Settings, get_settings
from empmcp.db.pool import close_pool, init_pool
from empmcp.exceptions import EmpMCPError
from empmcp.registry import register_all
from empmcp.utils.logging_config import configure_logging, get_logger
from empmcp.consts import INSTRUCTIONS


@lifespan
async def lifespan(_server: FastMCP):
    settings=get_settings()
    await init_pool(settings) 
    try:
        yield
    finally:
        await close_pool()
        

def create_server(settings: Settings) -> FastMCP:
    """Create the server."""
    auth = build_token_verifier(settings)

    logger = get_logger("server")
    
    logger.info(
        "Authentication enabled: RS256 JWT",
        extra={"issuer": settings.auth_issuer, "audience": settings.auth_audience},
    )

    mcp = FastMCP(
        settings.mcp_server_name,
        instructions=INSTRUCTIONS,
        lifespan=lifespan,
        auth=auth,
        mask_error_details=True,
    )
    register_all(mcp, settings)
    return mcp


def main() -> None:
    try:
        settings = get_settings()
    except EmpMCPError as exc:
        print(f"Configuration error: {exc} {exc.details}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level, settings.log_json)
    logger = get_logger("server")
    
    try:
        server = create_server(settings)
        logger.info(
                "Starting MCP server",
                extra={"host": settings.mcp_host, "port": settings.mcp_port,
                       "path": settings.mcp_path},
            )
        server.run(
            transport="http",
            host=settings.mcp_host,
            port=settings.mcp_port,
            path=settings.mcp_path,
            log_level=settings.log_level.lower(),
            show_banner=False,
        )
    except EmpMCPError as exc:
        logger.critical(
            "Server failed to start",
            extra={
                "error_code": exc.code,
                "error_message": exc.message,
                "error_details": exc.details,
            },
        )
        sys.exit(1)