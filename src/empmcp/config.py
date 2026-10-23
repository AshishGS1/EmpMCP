from __future__ import annotations

from functools import lru_cache

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from empmcp.exceptions import ConfigurationError

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Oracle
    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    oracle_pool_timeout_seconds: int = Field(30, ge=1)

    # MCP server
    mcp_server_name: str = "empmcp-server"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(8001, ge=1, le=65535)
    mcp_path: str = "/mcp"

    # Authentication: self-signed RS256 JWTs. The server only ever holds the PUBLIC key.
    auth_public_key_path: str 
    auth_issuer: str 
    auth_audience: str 
    auth_max_token_ttl_seconds: int = Field(3600, ge=1)  # reject longer-lived tokens

    # Rate limiting (global, applied to tool calls only)
    rate_lim_rps: float = Field(10.0, gt=0)  # sustained calls per second

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # Query limits
    search_max_limit: int = Field(50, ge=1)
    search_default_limit: int = Field(10, ge=1)

    @model_validator(mode="after")
    def _check_consistency(self) -> "Settings":
        if self.search_default_limit > self.search_max_limit:
            raise ValueError("SEARCH_DEFAULT_LIMIT must be <= SEARCH_MAX_LIMIT")
        return self


@lru_cache
def get_settings() -> Settings:
    """Load settings once; turn validation failures into a ConfigurationError."""
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        problems = [
            {
                "field": ".".join(str(p) for p in err["loc"]) or "settings",
                "problem": err["msg"],
            }
            for err in exc.errors()
        ]
        raise ConfigurationError(
            "Invalid or missing configuration", details={"errors": problems}
        ) from exc

