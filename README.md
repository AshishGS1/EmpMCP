# empmcp-server

An MCP (Model Context Protocol) server for an employee directory, built with
[FastMCP](https://gofastmcp.com) and backed by Oracle. It speaks the real MCP
protocol over streamable HTTP, so any MCP client (for example the FastAPI project)
can discover and call its tools.

## Tools

| Tool | Purpose | No match |
|---|---|---|
| `get_employee_details(employee_id)` | Full record for one employee (department and manager names included) | `EMPLOYEE_NOT_FOUND` error |
| `search_employees(name?, department?, job_title?, limit?, offset?)` | Case-insensitive contains-search, filters ANDed, at least one required, paged (default 10, max 50) | Empty list, not an error |
| `get_department_statistics(department_id?, include_inactive?)` | Headcount, total/avg/min/max salary, budget utilisation, manager, location | `DEPARTMENT_NOT_FOUND` if an ID is given and missing |

## Layout

```
src/empmcp/
  server.py          builds FastMCP, DB pool lifespan, runs HTTP transport
  registry.py        the only place middleware and tools are registered
  config.py          environment settings (pydantic-settings)
  exceptions.py      custom error hierarchy
  middleware/
    rate_limit.py        global sliding-window limiter, tool calls only
    request_logging.py   structured per-call logging with a request_id
  tools/             thin MCP tool functions (no SQL, no business rules)
  services/          business rules + SQL, raise domain errors
  db/                async Oracle pool and query helpers, raise database errors
  schemas/           pydantic output models
sql/                 schema + seed data, run automatically by docker compose
tests/
```

Flow: `tool -> service -> db`. Middleware order is logging (outermost), then rate
limiting, so rate-limited calls are still logged.

## Run it

```bash
# 1. Oracle (first start takes a couple of minutes; sql/ scripts run once)
cp .env.example .env
docker compose up -d
docker compose ps        # wait for "healthy"

# 2. Server
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
python -m empmcp         # or: empmcp
```

The MCP endpoint is `http://127.0.0.1:8001/mcp` (change with `MCP_HOST`,
`MCP_PORT`, `MCP_PATH`). If Oracle is unreachable the server exits at startup
with `DATABASE_CONNECTION_ERROR` instead of starting half-working.

To reset the database (re-run the SQL scripts): `docker compose down -v`.

## Errors

Every deliberate error is an `EmpMCPError` (a FastMCP `ToolError`), so the client
sees a stable code at the start of the message, e.g.
`[EMPLOYEE_NOT_FOUND] No employee with id 9999`. Unexpected exceptions are masked
from clients and logged with a traceback.

| Code | Raised in | Meaning |
|---|---|---|
| `CONFIGURATION_ERROR` | config | Missing or invalid environment settings |
| `DATABASE_CONNECTION_ERROR` | db | Pool or connection failure |
| `DATABASE_POOL_EXHAUSTED` | db | No free connection within the pool timeout |
| `QUERY_EXECUTION_ERROR` | db | SQL failed (client sees only the Oracle code) |
| `INVALID_EMPLOYEE_ID` / `INVALID_DEPARTMENT_ID` | services | ID is not a positive integer |
| `EMPLOYEE_NOT_FOUND` / `DEPARTMENT_NOT_FOUND` | services | No row for that ID |
| `INVALID_SEARCH_CRITERIA` | services | No filter, filter too long, or limit/offset out of range |
| `RATE_LIMIT_EXCEEDED` | middleware | Global tool-call limit hit; details include `retry_after_seconds` |

## Rate limiting

One global sliding window shared by all clients, applied to tool calls only
(`initialize` and `tools/list` are never throttled). Defaults: 30 calls per 60 s
(`RATE_LIMIT_MAX_CALLS`, `RATE_LIMIT_WINDOW_SECONDS`). Rejected calls do not count
toward the window. The counter lives in process memory, so it resets on restart
and is per server process.

## Logging

JSON lines on stderr (`LOG_JSON=false` for plain text). Each tool call logs
`tool call started` and then `completed` or `failed` with `request_id`, `tool`,
redacted `arguments`, `duration_ms`, `status` and, on failure, `error_code` and
`error_type`. The `request_id` is also stamped on every log line produced during
that call (service and database logs), so one call can be traced end to end.

## Tests

```bash
pytest                                   # no Oracle needed (database is faked)
RUN_ORACLE_TESTS=1 pytest tests/test_integration_oracle.py   # needs the container
```