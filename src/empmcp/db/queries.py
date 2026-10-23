"""Query helpers. Services call these; they never touch the pool or cursors.

All values must be passed as bind variables (``:name``), never formatted into the
SQL string. Rows come back as dicts with lower-case column names.
"""

from __future__ import annotations

from typing import Any, Mapping

import oracledb

from empmcp.db.pool import acquire_connection, oracle_error_code
from empmcp.exceptions import QueryExecutionError
from empmcp.utils.logging_config import get_logger

logger = get_logger("db.queries")


async def fetch_all(
    sql: str, params: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    async with acquire_connection() as connection:
        try:
            with connection.cursor() as cursor:
                await cursor.execute(sql, params or {})
                columns = [col[0].lower() for col in cursor.description]
                cursor.rowfactory = lambda *values: dict(zip(columns, values))
                return await cursor.fetchall()
        except oracledb.Error as exc:
            raise _query_error(exc, sql) from exc


async def fetch_one(
    sql: str, params: Mapping[str, Any] | None = None
) -> dict[str, Any] | None:
    async with acquire_connection() as connection:
        try:
            with connection.cursor() as cursor:
                await cursor.execute(sql, params or {})
                columns = [col[0].lower() for col in cursor.description]
                cursor.rowfactory = lambda *values: dict(zip(columns, values))
                return await cursor.fetchone()
        except oracledb.Error as exc:
            raise _query_error(exc, sql) from exc


def _query_error(exc: oracledb.Error, sql: str) -> QueryExecutionError:
    code = oracle_error_code(exc)
    # Full detail goes to the log; the client only sees the Oracle error code.
    logger.error(
        "Query failed",
        extra={"oracle_code": code, "sql": " ".join(sql.split())},
        exc_info=True,
    )
    return QueryExecutionError(
        "Database query failed", details={"oracle_code": code}
    )
