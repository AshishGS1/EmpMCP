"""Employee MCP tools. Thin wrappers: no SQL and no business rules live here."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from empmcp.auth import current_caller
from empmcp.models.employee import EmployeeDetails, EmployeeSearchResult
from empmcp.services import employee_service
from empmcp.consts import SCOPE_SALARY_READ


async def get_employee_details(
    employee_id: Annotated[int, Field(description="Numeric employee ID (e_id)")],
) -> EmployeeDetails:
    """Get the full record for ONE employee by ID: contact details, job title, join
    date, salary, department and manager. Fails if the ID does not exist. If you
    only know a name, call search_employees first to find the ID. Salary field is
    null unless caller has salary:read scope"""
    include_salary = current_caller().has_scope(SCOPE_SALARY_READ)
    return await employee_service.get_by_id(employee_id, include_salary=include_salary)


async def search_employees(
    name: Annotated[
        str | None, Field(description="Part of the employee name, case-insensitive")
    ] = None,
    department: Annotated[
        str | None, Field(description="Part of the department name, case-insensitive")
    ] = None,
    job_title: Annotated[
        str | None, Field(description="Part of the job title, case-insensitive")
    ] = None,
    limit: Annotated[
        int | None, Field(description="Page size (default 10, maximum 50)")
    ] = None,
    offset: Annotated[int, Field(description="Rows to skip, for paging")] = 0,
) -> EmployeeSearchResult:
    """Search employees by name, department and/or job title (all filters are
    combined with AND; at least one is required). Returns short summaries with IDs
    plus the total match count; no match gives an empty list, not an error. Use
    get_employee_details with an ID from the results for the full record."""
    return await employee_service.search(
        name=name,
        department=department,
        job_title=job_title,
        limit=limit,
        offset=offset,
    )
