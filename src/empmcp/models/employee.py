"""Employee tool outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from empmcp.models.shared import DateOnly


class EmployeeDetails(BaseModel):
    """Full record for one employee."""

    e_id: int
    name: str
    email: str
    phone: str | None = None
    job_title: str
    join_date: DateOnly
    salary: float | None = Field(None, description="None uwithout salary:read")
    department_id: int | None = None
    department_name: str | None = None
    manager_id: int | None = None
    manager_name: str | None = None


class EmployeeSummary(BaseModel):
    """Lightweight row returned by search; use the e_id to fetch full details."""

    e_id: int
    name: str
    job_title: str
    department_id: int | None = None
    department_name: str | None = None


class EmployeeSearchResult(BaseModel):
    items: list[EmployeeSummary]
    total: int = Field(description="Total matches ignoring limit/offset")
    limit: int
    offset: int
