#auth
# Scopes. A caller may hold any combination.
SCOPE_EMPLOYEES_READ = "employees:read"  # employee tools
SCOPE_DEPARTMENTS_READ = "departments:read"  # department tools
SCOPE_SALARY_READ = "salary:read"  # not needed to call a tool: it decides whether salary figures are redacted
ALL_SCOPES = frozenset({SCOPE_EMPLOYEES_READ, SCOPE_DEPARTMENTS_READ, SCOPE_SALARY_READ})

JWT_ALGORITHM = "RS256"
MIN_RSA_KEY_BITS = 2048

#registry
TOOL_SCOPES = {
    "get_employee_details": {SCOPE_EMPLOYEES_READ},
    "search_employees": {SCOPE_EMPLOYEES_READ},
    "get_department_statistics": {SCOPE_DEPARTMENTS_READ},
}

#server
INSTRUCTIONS = (
    "Employee directory backed by Oracle. Use search_employees to find people by "
    "name, department or job title (it returns IDs), get_employee_details for one "
    "person's full record, and get_department_statistics for headcount and salary "
    "figures per department. Errors start with a stable code in square brackets."
)

