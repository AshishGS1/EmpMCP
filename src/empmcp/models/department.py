"""Department tool outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from empmcp.models.shared import DateOnly


class DepartmentStatistics(BaseModel):
    dept_id: int
    name: str
    location: str | None = None
    is_active: bool
    created_date: DateOnly
    manager_id: int | None = None
    manager_name: str | None = None
    headcount: int
    total_salary: float | None = Field(None, description="None without salary:read")
    avg_salary: float | None = Field(None, description="None without salary:read, or None when headcount is 0")
    min_salary: float | None = Field(None, description="None without salary:read")
    max_salary: float | None = Field(None, description="None without salary:read")
    budget: float | None = None
    budget_utilization_pct: float | None = Field(
        None, description="total_salary / budget * 100; None without salary:read, or None when no budget is set"
    )


class DepartmentStatisticsResult(BaseModel):
    departments: list[DepartmentStatistics]
    count: int
