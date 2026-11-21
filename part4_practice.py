"""Part 4: QuerySet API, Advanced Logic & Optimization (Tasks 4.1 - 4.4).

Run from the project root (where manage.py is):
    python part4_practice.py          # clean output, repeatable (changes are rolled back)
    python part4_practice.py --sql    # also print the generated SQL
    python part4_practice.py --keep   # keep the salary changes in the database
"""
import os
import sys
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "training_system.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402
from django.db.models import F, Q  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

from core.models import Course, Employee  # noqa: E402

SHOW_SQL = "--sql" in sys.argv
KEEP = "--keep" in sys.argv


class Rollback(Exception):
    pass


# ------------------------------------------------------------ print helpers
def title(text):
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def table(headers, rows):
    rows = [[str(c) for c in r] for r in rows]
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    line = "-+-".join("-" * w for w in widths)
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(line)
    for r in rows:
        print(" | ".join(c.ljust(w) for c, w in zip(r, widths)))


def emp_rows(qs):
    return [
        (e.employee_code, f"{e.first_name} {e.last_name}", e.department.code, f"{e.salary:,.2f}")
        for e in qs.select_related("department")
    ]


EMP_HEADERS = ["Code", "Name", "Dept", "Salary"]


def show_sql(label, qs):
    if SHOW_SQL:
        print(f"\n  SQL ({label}):\n  {qs.query}")


def run():
    # Reset to the starting salaries so every run gives the same result.
    Employee.objects.filter(employee_code="EMP001").update(salary=Decimal("65000.00"))
    Employee.objects.filter(employee_code="EMP002").update(salary=Decimal("75000.00"))

    # ------------------------------------------------------------ Task 4.1
    title("TASK 4.1  Q objects (OR / AND / NOT)")

    query_or = Employee.objects.filter(Q(department__code="IT") | Q(salary__gt=70000))
    print("\nQuery 1: department = IT  OR  salary > 70,000")
    table(EMP_HEADERS, emp_rows(query_or))
    show_sql("Query 1", query_or)

    query_not = Employee.objects.filter(
        Q(first_name__icontains="John") & ~Q(department__code="HR")
    )
    print("\nQuery 2: first name contains 'John'  AND NOT  department = HR")
    table(EMP_HEADERS, emp_rows(query_not))
    show_sql("Query 2", query_not)

    # ------------------------------------------------------------ Task 4.2
    title("TASK 4.2  F() expression: 10% raise for IT, done inside the database")

    it_before = {e.pk: e.salary for e in Employee.objects.filter(department__code="IT")}
    # Decimal('1.10'), not 1.10: DecimalField * float raises a mixed-types error.
    updated = Employee.objects.filter(department__code="IT").update(
        salary=F("salary") * Decimal("1.10")
    )
    print(f"\nRows updated with ONE SQL UPDATE: {updated}\n")
    rows = []
    for e in Employee.objects.filter(department__code="IT"):
        rows.append((e.employee_code, f"{e.first_name} {e.last_name}",
                     f"{it_before[e.pk]:,.2f}", f"{e.salary:,.2f}"))
    table(["Code", "Name", "Old salary", "New salary (+10%)"], rows)

    # ------------------------------------------------------------ Task 4.3
    title("TASK 4.3  N+1 problem: counting queries")

    with CaptureQueriesContext(connection) as unopt:
        rows = [(e.first_name, e.department.name) for e in Employee.objects.all()]
    with CaptureQueriesContext(connection) as sel:
        rows2 = [(e.first_name, e.department.name)
                 for e in Employee.objects.select_related("department").all()]
    with CaptureQueriesContext(connection) as pre:
        course_rows = []
        for c in Course.objects.prefetch_related("attendees").all():
            course_rows.append((c.code, c.title,
                                ", ".join(e.first_name for e in c.attendees.all())))

    print("\nEmployee -> Department (ForeignKey):")
    table(["Employee", "Department"], rows2)
    print("\nCourse -> Attendees (ManyToMany):")
    table(["Course", "Title", "Attendees"], course_rows)

    print("\nQuery count comparison:")
    table(
        ["Approach", "Queries", "Expected"],
        [
            ("Unoptimized loop (N+1)", len(unopt), "1 + one per employee"),
            ("select_related('department')", len(sel), "exactly 1"),
            ("prefetch_related('attendees')", len(pre), "exactly 2"),
        ],
    )
    if SHOW_SQL:
        for label, ctx in (("select_related", sel), ("prefetch_related", pre)):
            for q in ctx.captured_queries:
                print(f"\n  SQL ({label}):\n  {q['sql']}")

    # ------------------------------------------------------------ Summary
    title("SELF-CHECK")
    checks = [
        ("4.1 Q objects return the correct records",
         [e.employee_code for e in query_or] == ["EMP001", "EMP002"]
         and [e.employee_code for e in query_not] == ["EMP001"]),
        ("4.2 F() update ran as one UPDATE, no Python loop", updated == 2),
        ("4.3 select_related uses exactly 1 query", len(sel) == 1),
        ("4.3 prefetch_related uses exactly 2 queries", len(pre) == 2),
    ]
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    if not KEEP:
        raise Rollback


if __name__ == "__main__":
    try:
        with transaction.atomic():
            run()
    except Rollback:
        print("\n(Demo mode: salary changes were rolled back. Use --keep to save them.)")
    print("\nTask 4.4 comparison table is documentation - see SOLUTIONS.md")
