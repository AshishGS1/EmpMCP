import sys

from empmcp.config import get_settings
from empmcp.exceptions import EmpMCPError
from empmcp.server import create_server
from empmcp.utils.logging_config import configure_logging, get_logger


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