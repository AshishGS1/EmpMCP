"""Employee business rules and SQL.

Failure semantics:
  * get_by_id  -> unknown id is an error (EmployeeNotFoundError)
  * search     -> no match is a valid answer (empty list), but a malformed or
                  unbounded request is an error (InvalidSearchCriteriaError)
"""


from typing import Any

from empmcp.config import get_settings
from empmcp.db import queries
from empmcp.services.queries import DETAILS_SQL, SEARCH_FROM
from empmcp.exceptions import (
    EmployeeNotFoundError,
    InvalidEmployeeIdError,
    InvalidSearchCriteriaError,
)
from empmcp.models.employee import (
    EmployeeDetails,
    EmployeeSearchResult,
    EmployeeSummary,
)

MAX_FILTER_LENGTH = 100


async def get_by_id(employee_id: int, *, include_salary: bool = False) -> EmployeeDetails:    
    if (
        isinstance(employee_id, bool)
        or not isinstance(employee_id, int)
        or employee_id <= 0
    ):
        raise InvalidEmployeeIdError(
            "employee_id must be a positive integer",
            details={"employee_id": employee_id},
        )

    row = await queries.fetch_one(DETAILS_SQL, {"e_id": employee_id})
    if row is None:
        raise EmployeeNotFoundError(
            f"No employee with id {employee_id}", details={"employee_id": employee_id}
        )
    if not include_salary:
        row = {**row, "salary": None}
    return EmployeeDetails(**row)


async def search(
    name: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> EmployeeSearchResult:
    settings = get_settings()

    filters = {
        "name": _clean(name, "name"),
        "department": _clean(department, "department"),
        "job_title": _clean(job_title, "job_title"),
    }
    if not any(filters.values()):
        raise InvalidSearchCriteriaError(
            "Provide at least one filter: name, department or job_title"
        )

    limit = settings.search_default_limit if limit is None else limit
    if limit < 1 or limit > settings.search_max_limit:
        raise InvalidSearchCriteriaError(
            f"limit must be between 1 and {settings.search_max_limit}",
            details={"limit": limit, "max_limit": settings.search_max_limit},
        )
    if offset < 0:
        raise InvalidSearchCriteriaError(
            "offset must be 0 or greater", details={"offset": offset}
        )

    # Only fixed SQL fragments are concatenated; every value is a bind variable.
    conditions: list[str] = []
    params: dict[str, Any] = {}
    if filters["name"]:
        conditions.append("UPPER(e.name) LIKE UPPER(:name) ESCAPE '\\'")
        params["name"] = _like_pattern(filters["name"])
    if filters["department"]:
        conditions.append("UPPER(d.name) LIKE UPPER(:department) ESCAPE '\\'")
        params["department"] = _like_pattern(filters["department"])
    if filters["job_title"]:
        conditions.append("UPPER(e.job_title) LIKE UPPER(:job_title) ESCAPE '\\'")
        params["job_title"] = _like_pattern(filters["job_title"])
    where = " AND ".join(conditions)

    count_row = await queries.fetch_one(
        f"SELECT COUNT(*) AS total {SEARCH_FROM} WHERE {where}", params
    )
    total = int(count_row["total"]) if count_row else 0

    items: list[EmployeeSummary] = []
    if total > offset:
        rows = await queries.fetch_all(
            f"""
            SELECT e.e_id, e.name, e.job_title,
                   e.dept_id AS department_id, d.name AS department_name
            {SEARCH_FROM}
            WHERE {where}
            ORDER BY e.name, e.e_id
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """,
            {**params, "offset": offset, "limit": limit},
        )
        items = [EmployeeSummary(**row) for row in rows]

    return EmployeeSearchResult(items=items, total=total, limit=limit, offset=offset)


def _clean(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > MAX_FILTER_LENGTH:
        raise InvalidSearchCriteriaError(
            f"{field} must be at most {MAX_FILTER_LENGTH} characters",
            details={"field": field},
        )
    return value or None


def _like_pattern(value: str) -> str:
    """Contains-match pattern with LIKE wildcards in the user's text escaped."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
