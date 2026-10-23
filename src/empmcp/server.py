"""Builds the FastMCP server and runs it over streamable HTTP."""


from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from empmcp.auth import build_token_verifier
from empmcp.config import Settings, get_settings
from empmcp.db.pool import close_pool, init_pool
from empmcp.registry import register_all
from empmcp.utils.logging_config import get_logger
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