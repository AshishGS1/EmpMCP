"""Department MCP tools."""


from typing import Annotated

from pydantic import Field

from empmcp.auth import current_caller
from empmcp.models.department import DepartmentStatisticsResult
from empmcp.services import department_service
from empmcp.consts import SCOPE_SALARY_READ


async def get_department_statistics(
    department_id: Annotated[
        int | None,
        Field(description="Department ID. Omit to get every department."),
    ] = None,
    include_inactive: Annotated[
        bool,
        Field(description="Include inactive departments when no ID is given"),
    ] = False,
) -> DepartmentStatisticsResult:
    """Headcount, salary statistics (total, average, min, max), budget utilisation,
    location and manager for one department, or for all active departments when no
    ID is given. A department with no employees reports headcount 0 and no
    average/min/max. Fails if a given department ID does not exist."""
    include_salary = current_caller().has_scope(SCOPE_SALARY_READ)
    return await department_service.get_statistics(
        department_id=department_id, include_inactive=include_inactive, include_salary=include_salary,
    )
