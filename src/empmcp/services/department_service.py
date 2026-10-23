"""Department statistics: business rules and SQL."""


from typing import Any

from empmcp.db import queries
from empmcp.exceptions import DepartmentNotFoundError, InvalidDepartmentIdError
from empmcp.models.department import DepartmentStatistics, DepartmentStatisticsResult
from empmcp.services.queries import STATS_SQL



async def get_statistics(
    department_id: int | None = None, include_inactive: bool = False, *, include_salary: bool = False,
) -> DepartmentStatisticsResult:
    """Statistics for one department, or for all (active only unless asked)."""
    params: dict[str, Any] = {}
    if department_id is not None:
        if (
            isinstance(department_id, bool)
            or not isinstance(department_id, int)
            or department_id <= 0
        ):
            raise InvalidDepartmentIdError(
                "department_id must be a positive integer",
                details={"department_id": department_id},
            )
        where = "WHERE d.dept_id = :dept_id"
        params["dept_id"] = department_id
    elif include_inactive:
        where = ""
    else:
        where = "WHERE d.is_active = 1"

    rows = await queries.fetch_all(STATS_SQL.format(where=where), params)
    if department_id is not None and not rows:
        raise DepartmentNotFoundError(
            f"No department with id {department_id}",
            details={"department_id": department_id},
        )

    departments = [_to_statistics(row, include_salary) for row in rows]
    return DepartmentStatisticsResult(departments=departments, count=len(departments))


def _to_statistics(row: dict[str, Any], include_salary: bool) -> DepartmentStatistics:
    total = float(row["total_salary"] or 0)
    budget = row["budget"]
    salary_fields: dict[str, float | None] = {
        "total_salary": None,
        "avg_salary": None,
        "min_salary": None,
        "max_salary": None,
        "budget_utilization_pct": None,
    }
    if include_salary:
        salary_fields = {
            "total_salary": round(total, 2),
            "avg_salary": _round(row["avg_salary"]),
            "min_salary": _round(row["min_salary"]),
            "max_salary": _round(row["max_salary"]),
            "budget_utilization_pct": (
                round(total / float(budget) * 100, 2) if budget else None
            ),
        }
    return DepartmentStatistics(
        dept_id=row["dept_id"],
        name=row["name"],
        location=row["location"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
        manager_id=row["manager_id"],
        manager_name=row["manager_name"],
        headcount=int(row["headcount"]),
        budget=float(budget) if budget is not None else None,
        **salary_fields,
    )


def _round(value: Any) -> float | None:
    return None if value is None else round(float(value), 2)
