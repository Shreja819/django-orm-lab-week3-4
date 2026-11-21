"""Populate sample data (Step 3.5). Safe to run more than once.

Run from the project root (where manage.py is):
    python seed_data.py
"""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "training_system.settings")
django.setup()

from core.models import Department, Employee, Course, TrainingRecord  # noqa: E402

hr, _ = Department.objects.get_or_create(code="HR", defaults={"name": "Human Resources"})
it, _ = Department.objects.get_or_create(code="IT", defaults={"name": "Information Technology"})
fin, _ = Department.objects.get_or_create(code="FIN", defaults={"name": "Finance"})


def emp(code, first, last, email, salary, dept):
    obj, _ = Employee.objects.get_or_create(
        employee_code=code,
        defaults=dict(first_name=first, last_name=last, email=email,
                      salary=Decimal(salary), department=dept),
    )
    return obj


e1 = emp("EMP001", "John", "Doe", "john@example.com", "65000.00", it)
e2 = emp("EMP002", "Jane", "Smith", "jane@example.com", "75000.00", it)
e3 = emp("EMP003", "Alice", "Johnson", "alice@example.com", "55000.00", hr)
e4 = emp("EMP004", "Bob", "Brown", "bob@example.com", "60000.00", fin)

c1, _ = Course.objects.get_or_create(code="SEC101", defaults=dict(title="Cybersecurity Essentials", capacity=25))
c2, _ = Course.objects.get_or_create(code="DEV201", defaults=dict(title="Advanced Django ORM", capacity=30))

TrainingRecord.objects.get_or_create(employee=e1, course=c1,
                                     defaults=dict(completion_status="COMPLETED", score=Decimal("88.50")))
TrainingRecord.objects.get_or_create(employee=e1, course=c2,
                                     defaults=dict(completion_status="IN_PROGRESS"))
TrainingRecord.objects.get_or_create(employee=e2, course=c2,
                                     defaults=dict(completion_status="COMPLETED", score=Decimal("95.00")))
TrainingRecord.objects.get_or_create(employee=e3, course=c1,
                                     defaults=dict(completion_status="REGISTERED"))

print("Seed complete:",
      Department.objects.count(), "departments,",
      Employee.objects.count(), "employees,",
      Course.objects.count(), "courses,",
      TrainingRecord.objects.count(), "training records")
