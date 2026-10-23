"""Authentication: token verification and the per-call caller identity.

Flow of a request:
  1. FastMCP's HTTP layer runs StrictJWTVerifier on every request. A missing,
     malformed, expired or wrongly signed token is answered with HTTP 401 before any
     MCP message (so before any of our middleware) is processed.
  2. ToolAuthorizationMiddleware turns the verified token into a Caller, checks the
     scopes the tool requires, and publishes the Caller for the rest of the call.
  3. Tools read it with current_caller(), e.g. to decide whether salary is shown.

Tokens are RS256 JWTs signed by the FastAPI service. This server holds only the
public key, so a compromised MCP server cannot mint tokens.
"""

from __future__ import annotations

import time
import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from empmcp.config import Settings
from empmcp.exceptions import AuthenticationError, ConfigurationError
from empmcp.utils.logging_config import get_logger
from empmcp.consts import JWT_ALGORITHM, MIN_RSA_KEY_BITS

logger = get_logger("auth")

# Fixed on purpose. Never configurable.
_JTI_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")


@dataclass(frozen=True)
class Caller:
    subject: str
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


caller_var: ContextVar[Caller | None] = ContextVar("caller", default=None)


def identify_caller() -> Caller | None:
    """The caller behind the current request's verified token, or None."""
    token = get_access_token()
    if token is None:
        return None
    return Caller(
        subject=token.subject or token.client_id,
        scopes=frozenset(token.scopes),
    )

def identify_jti() -> str:
    """The token's ``jti`` (FastAPI's request ID) for log correlation, or "-". Optional"""
    token = get_access_token()
    value = (token.claims or {}).get("jti") if token else None
    if isinstance(value, str) and _JTI_RE.fullmatch(value):
        return value
    return "-"

def caller_label() -> str:
    """Caller name for log lines; 'anonymous' when there is no verified token."""
    caller = identify_caller()
    return caller.subject if caller else "anonymous"


def current_caller() -> Caller:
    """The caller published by ToolAuthorizationMiddleware for this tool call"""
    caller = caller_var.get()
    if caller is None:
        raise AuthenticationError("No authenticated caller for this request")
    return caller


class StrictJWTVerifier(JWTVerifier):
    """JWTVerifier plus the rules it does not enforce on its own.
    * ``exp`` is mandatory: stock JWTVerifier accepts a token without one forever.
    * ``exp`` may be at most ``max_ttl_seconds`` away, capping a leaked token's life.
    * ``sub`` is mandatory: every call must be attributable to a user.
    """

    def __init__(self, *, max_ttl_seconds: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._max_ttl_seconds = max_ttl_seconds

    async def verify_token(self, token: str) -> AccessToken | None:
        access = await super().verify_token(token)
        if access is None:
            return None  # signature, issuer, audience or expiry check failed

        if access.expires_at is None:
            return self._reject(access, "token has no exp claim")
        if access.expires_at - time.time() > self._max_ttl_seconds:
            return self._reject(
                access, f"token lifetime exceeds {self._max_ttl_seconds}s"
            )
        if not access.subject:
            return self._reject(access, "token has no sub claim")
        return access

    @staticmethod
    def _reject(access: AccessToken, reason: str) -> None:
        # Never log the token itself.
        logger.warning(
            "Bearer token rejected: %s",
            reason,
            extra={"event": "token_rejected", "client_id": access.client_id},
        )
        return None


def load_public_key_pem(path: str | None) -> str:
    """Read and validate the PEM public key used to verify tokens."""
    if not path:
        raise ConfigurationError("AUTH_PUBLIC_KEY_PATH is required when AUTH_MODE=jwt")
    try:
        pem = Path(path).read_bytes()
    except OSError as exc:
        raise ConfigurationError(
            f"Cannot read AUTH_PUBLIC_KEY_PATH ({path})",
            details={"path": path, "reason": exc.strerror},
        ) from exc

    try:
        key = serialization.load_pem_public_key(pem)
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise ConfigurationError(
            "AUTH_PUBLIC_KEY_PATH must point to a PEM-encoded RSA public key. A "
            "private key is rejected on purpose: this server only needs the public half.",
            details={"path": path},
        ) from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise ConfigurationError(
            "AUTH_PUBLIC_KEY_PATH must be an RSA public key", details={"path": path}
        )
    if key.key_size < MIN_RSA_KEY_BITS:
        raise ConfigurationError(
            f"RSA key must be at least {MIN_RSA_KEY_BITS} bits",
            details={"path": path, "key_bits": key.key_size},
        )
    return pem.decode()


def build_token_verifier(settings: Settings) -> TokenVerifier:
    """The verifier for FastMCP's HTTP layer"""
    return StrictJWTVerifier(
        public_key=load_public_key_pem(settings.auth_public_key_path),
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        algorithm=JWT_ALGORITHM,
        max_ttl_seconds=settings.auth_max_token_ttl_seconds,
    )