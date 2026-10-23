#department
STATS_SQL = """
SELECT d.dept_id, d.name, d.location, d.is_active, d.budget, d.created_date,
       d.mgr_id AS manager_id, m.name AS manager_name,
       COUNT(e.e_id)            AS headcount,
       NVL(SUM(e.salary), 0)    AS total_salary,
       AVG(e.salary)            AS avg_salary,
       MIN(e.salary)            AS min_salary,
       MAX(e.salary)            AS max_salary
FROM departments d
LEFT JOIN employees m ON m.e_id   = d.mgr_id
LEFT JOIN employees e ON e.dept_id = d.dept_id
{where}
GROUP BY d.dept_id, d.name, d.location, d.is_active, d.budget, d.created_date,
         d.mgr_id, m.name
ORDER BY d.dept_id
"""

#employee
DETAILS_SQL = """
SELECT e.e_id, e.name, e.email, e.phone, e.job_title, e.join_date, e.salary,
       e.dept_id AS department_id, d.name AS department_name,
       e.mgr_id  AS manager_id,    m.name AS manager_name
FROM employees e
LEFT JOIN departments d ON d.dept_id = e.dept_id
LEFT JOIN employees   m ON m.e_id   = e.mgr_id
WHERE e.e_id = :e_id
"""

SEARCH_FROM = """
FROM employees e
LEFT JOIN departments d ON d.dept_id = e.dept_id
"""