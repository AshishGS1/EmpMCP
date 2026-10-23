"""Custom exception hierarchy.

Every error subclasses fastmcp's ToolError, so when one is raised inside a tool
(or by middleware on a tool call) its message reaches the MCP client instead of
being masked. The message is prefixed with the HTTP status and a stable code
"""


from typing import Any
from http import HTTPStatus

from fastmcp.exceptions import ToolError


class EmpMCPError(ToolError):
    """Base class for every error this server raises on purpose."""

    code: str = "EMP_MCP_ERROR"
    http_status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(f"[{int(self.http_status)} {self.code}] {message}")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


# Config
class ConfigurationError(EmpMCPError):
    code = "CONFIGURATION_ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


# Db
class DatabaseError(EmpMCPError):
    code = "DATABASE_ERROR"
    http_status = HTTPStatus.BAD_GATEWAY


class DatabaseConnectionError(DatabaseError):
    """Pool creation or connection acquisition failed (DB down, bad credentials)."""

    code = "DATABASE_CONNECTION_ERROR"
    http_status = HTTPStatus.BAD_GATEWAY


class PoolExhaustedError(DatabaseError):
    """No connection became available within the pool timeout."""

    code = "DATABASE_POOL_EXHAUSTED"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class QueryExecutionError(DatabaseError):
    """A SQL statement failed while executing."""

    code = "QUERY_EXECUTION_ERROR"
    http_status = HTTPStatus.BAD_GATEWAY


# Services
class ServiceError(EmpMCPError):
    code = "SERVICE_ERROR"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class InvalidEmployeeIdError(ServiceError):
    code = "INVALID_EMPLOYEE_ID"
    http_status = HTTPStatus.BAD_REQUEST


class EmployeeNotFoundError(ServiceError):
    code = "EMPLOYEE_NOT_FOUND"
    http_status = HTTPStatus.NOT_FOUND


class InvalidDepartmentIdError(ServiceError):
    code = "INVALID_DEPARTMENT_ID"
    http_status = HTTPStatus.BAD_REQUEST


class DepartmentNotFoundError(ServiceError):
    code = "DEPARTMENT_NOT_FOUND"
    http_status = HTTPStatus.NOT_FOUND


class InvalidSearchCriteriaError(ServiceError):
    code = "INVALID_SEARCH_CRITERIA"
    http_status = HTTPStatus.BAD_REQUEST


# Auth
class AuthenticationError(EmpMCPError):
    """No verified caller identity reached the tool call (fail closed)."""

    code = "AUTHENTICATION_REQUIRED"
    http_status = HTTPStatus.UNAUTHORIZED


class PermissionDeniedError(EmpMCPError):
    """The caller is authenticated but lacks a scope the tool requires."""

    code = "PERMISSION_DENIED"
    http_status = HTTPStatus.FORBIDDEN


# middleware
class RateLimitExceededError(EmpMCPError):
    code = "RATE_LIMIT_EXCEEDED"
    http_status = HTTPStatus.TOO_MANY_REQUESTS
