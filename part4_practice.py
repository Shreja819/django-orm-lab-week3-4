"""Part 4: QuerySet API, Advanced Logic & Optimization (Tasks 4.1 - 4.4).

Run from the project root (where manage.py is):
    python part4_practice.py
or, as the lab guide describes:
    python manage.py shell < part4_practice.py
"""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "training_system.settings")
django.setup()

from django.db import connection, reset_queries  # noqa: E402
from django.db.models import F, Q  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from core.models import Course, Employee  # noqa: E402

# ---------------------------------------------------------------- Task 4.1
print("\n=== Task 4.1: Q objects ===")

# Query 1: IT department OR salary > 70,000
query_or = Employee.objects.filter(Q(department__code="IT") | Q(salary__gt=70000))
print("OR Query Results:", list(query_or))
print("SQL:", query_or.query)

# Query 2: first name contains "John" AND NOT in HR
query_not = Employee.objects.filter(
    Q(first_name__icontains="John") & ~Q(department__code="HR")
)
print("AND NOT Query Results:", list(query_not))
print("SQL:", query_not.query)

# ---------------------------------------------------------------- Task 4.2
print("\n=== Task 4.2: F() expressions ===")
# NOTE: Run this only ONCE per database - every run adds another 10%.
# NOTE: Use Decimal('1.10'), not 1.10. Multiplying a DecimalField by a Python
#       float raises "Expression contains mixed types: DecimalField, FloatField".
updated = Employee.objects.filter(department__code="IT").update(
    salary=F("salary") * Decimal("1.10")
)
print(f"Rows updated in a single SQL UPDATE: {updated}")
for emp in Employee.objects.filter(department__code="IT"):
    print(f"{emp.first_name} New Salary: {emp.salary}")

# ---------------------------------------------------------------- Task 4.3
print("\n=== Task 4.3: N+1 problem ===")

# Unoptimized: 1 query for employees + 1 per employee for the department
with CaptureQueriesContext(connection) as ctx:
    for emp in Employee.objects.all():
        print(f"Employee: {emp.first_name}, Department: {emp.department.name}")
print(f"Total Queries Executed (Unoptimized): {len(ctx)}")

# Solution 1: select_related -> one JOIN, exactly 1 query
with CaptureQueriesContext(connection) as ctx:
    for emp in Employee.objects.select_related("department").all():
        print(f"Employee: {emp.first_name}, Department: {emp.department.name}")
print(f"Total Queries with select_related: {len(ctx)}")
for q in ctx.captured_queries:
    print(f"SQL: {q['sql']} | Time: {q['time']}s")

# Solution 2: prefetch_related -> exactly 2 queries (courses + attendees via IN)
with CaptureQueriesContext(connection) as ctx:
    for course in Course.objects.prefetch_related("attendees").all():
        names = [emp.first_name for emp in course.attendees.all()]
        print(f"Course: {course.code}, Attendees: {', '.join(names)}")
print(f"Total Queries with prefetch_related: {len(ctx)}")
for q in ctx.captured_queries:
    print(f"SQL: {q['sql']} | Time: {q['time']}s")

print("\nTask 4.4 comparison table is documentation - see SOLUTIONS.md")
