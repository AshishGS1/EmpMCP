"""Oracle connection pool (python-oracledb, thin mode, asyncio).

Thin mode needs no Oracle Client install. The async API keeps the event loop free
while queries run, which matters because FastMCP serves requests concurrently.

Lifecycle: ``init_pool`` on server startup, ``close_pool`` on shutdown (wired up
through the FastMCP lifespan in server.py).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import oracledb

from empmcp.config import Settings
from empmcp.exceptions import DatabaseConnectionError, PoolExhaustedError
from empmcp.utils.logging_config import get_logger

logger = get_logger("db.pool")

_pool: oracledb.AsyncConnectionPool | None = None


def oracle_error_code(exc: oracledb.Error) -> str:
    """Best-effort 'ORA-xxxxx'/'DPY-xxxx' code from a driver exception."""
    error = exc.args[0] if exc.args else None
    return getattr(error, "full_code", "") or ""


async def init_pool(settings: Settings) -> None:
    """Create the pool and verify the database is reachable."""
    global _pool
    try:
        _pool = oracledb.create_pool_async(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
            wait_timeout=settings.oracle_pool_timeout_seconds * 1000,  # milliseconds
        )
        async with _pool.acquire() as connection:
            await connection.ping()
    except oracledb.Error as exc:
        _pool = None
        code = oracle_error_code(exc)
        logger.error(
            "Failed to initialise Oracle pool",
            extra={"oracle_code": code, "dsn": settings.oracle_dsn},
            exc_info=True,
        )
        raise DatabaseConnectionError(
            "Could not connect to the Oracle database",
            details={"oracle_code": code},
        ) from exc
    logger.info(
        "Oracle pool ready",
        extra={"dsn": settings.oracle_dsn},
    )


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            await _pool.close(force=True)
        except oracledb.Error:
            logger.warning("Error while closing Oracle pool", exc_info=True)
        finally:
            _pool = None
            logger.info("Oracle pool closed")


def get_pool() -> oracledb.AsyncConnectionPool:
    if _pool is None:
        raise DatabaseConnectionError("Database pool is not initialised")
    return _pool


@asynccontextmanager
async def acquire_connection() -> AsyncIterator[oracledb.AsyncConnection]:
    """Borrow a connection; translate acquisition failures into our errors."""
    pool = get_pool()
    try:
        connection = await pool.acquire()
    except oracledb.Error as exc:
        code = oracle_error_code(exc)
        logger.error(
            "Could not acquire connection", extra={"oracle_code": code}, exc_info=True
        )
        raise DatabaseConnectionError(
            "Could not obtain a database connection",
            details={"oracle_code": code},
        ) from exc

    try:
        yield connection
    finally:
        try:
            await pool.release(connection)
        except oracledb.Error:
            logger.warning("Error releasing connection to pool", exc_info=True)
