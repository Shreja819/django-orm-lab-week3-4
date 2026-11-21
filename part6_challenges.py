"""Part 6: Advanced Challenge Exercises (Q objects & F expressions).

Setup (once):
  1. Add 'challenges' to INSTALLED_APPS in training_system/settings.py
  2. python manage.py makemigrations challenges
  3. python manage.py migrate
Run:
    python part6_challenges.py
"""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "training_system.settings")
django.setup()

from django.db import transaction  # noqa: E402
from django.db.models import Case, DecimalField, F, Q, When  # noqa: E402
from django.db.models.lookups import GreaterThan  # noqa: E402

from challenges.models import Category, Product  # noqa: E402


# ---------------------------------------------------------------- sample data
def seed():
    if Product.objects.exists():
        return
    elec, _ = Category.objects.get_or_create(name="Electronics")
    gadg, _ = Category.objects.get_or_create(name="Gadgets")
    home, _ = Category.objects.get_or_create(name="Home")

    def mk(name, cat, price, maxp, stock, reorder, promo, status, country):
        Product.objects.create(
            name=name, category=cat, price=Decimal(price), max_allowed_price=Decimal(maxp),
            stock_quantity=stock, reorder_level=reorder, is_promotional=promo,
            status=status, warehouse_country=country)

    mk("4K TV", elec, "25000", "30000", 5, 10, False, "NORMAL", "Japan")
    mk("Budget Phone", elec, "8000", "9000", 30, 10, False, "NORMAL", "China")
    mk("Gaming Laptop", elec, "45000", "50000", 12, 10, True, "NORMAL", "Taiwan")
    mk("Smart Watch", gadg, "1000", "1100", 15, 10, True, "NORMAL", "China")      # +15% = 1150 -> capped 1100
    mk("Earbuds", gadg, "2000", "3000", 8, 10, False, "DISCOUNTED", "Vietnam")    # +15% = 2300 -> OK
    mk("Desk Lamp", home, "500", "800", 40, 10, False, "DISCOUNTED", "China")
    mk("Sofa", home, "12000", "15000", 25, 10, True, "CLEARANCE", "Thailand")


def show(title, qs):
    print(f"\n--- {title} ---")
    for p in qs:
        print(f"  {p.name:15} cat={p.category.name:12} price={p.price:>10} "
              f"stock={p.stock_quantity:>3} reorder={p.reorder_level} promo={p.is_promotional} "
              f"status={p.status} country={p.warehouse_country}")


# ---------------------------------------------------------------- Challenge 1
def challenge_1():
    """(Electronics AND price > 10,000) OR (DISCOUNTED AND country != China)."""
    return Product.objects.select_related("category").filter(
        Q(category__name="Electronics", price__gt=10000)
        | (Q(status="DISCOUNTED") & ~Q(warehouse_country="China"))
    )


# ---------------------------------------------------------------- Challenge 2
def challenge_2():
    """stock <= reorder_level  OR  (promotional AND stock < reorder_level * 2)."""
    return Product.objects.select_related("category").filter(
        Q(stock_quantity__lte=F("reorder_level"))
        | Q(is_promotional=True, stock_quantity__lt=F("reorder_level") * 2)
    )


# ---------------------------------------------------------------- Challenge 3
def challenge_3():
    """Gadgets +15%, capped at max_allowed_price - one SQL UPDATE, no Python loop."""
    new_price = F("price") * Decimal("1.15")
    return Product.objects.filter(category__name="Gadgets").update(
        price=Case(
            When(GreaterThan(new_price, F("max_allowed_price")), then=F("max_allowed_price")),
            default=new_price,
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )
    # Equivalent shorter form (DB-side MIN):
    #   from django.db.models.functions import Least
    #   .update(price=Least(F("price") * Decimal("1.15"), F("max_allowed_price")))


# ---------------------------------------------------------------- Challenge 4
class InsufficientStock(Exception):
    pass


def purchase(product_id, qty):
    """Atomic purchase guard. The WHERE clause checks stock and the UPDATE
    changes it in the SAME SQL statement, so two concurrent buyers cannot both
    pass the check. 0 rows updated => not enough stock => purchase fails."""
    with transaction.atomic():
        rows = Product.objects.filter(
            pk=product_id, stock_quantity__gte=qty
        ).update(
            stock_quantity=F("stock_quantity") - qty,
            total_sold=F("total_sold") + qty,
            total_revenue=F("total_revenue") + F("price") * qty,
        )
        if rows == 0:
            raise InsufficientStock(f"Product {product_id}: cannot buy {qty} (not enough stock)")
    return rows


if __name__ == "__main__":
    seed()
    show("Challenge 1", challenge_1())
    show("Challenge 2", challenge_2())

    print("\n--- Challenge 3 ---")
    print("Rows updated:", challenge_3(), "(run once; each run adds another 15%)")
    show("Gadgets after update", Product.objects.filter(category__name="Gadgets").select_related("category"))

    print("\n--- Challenge 4 ---")
    tv = Product.objects.get(name="4K TV")  # stock 5 on a fresh DB
    purchase(tv.pk, 2)
    tv.refresh_from_db()
    print(f"After buying 2: stock={tv.stock_quantity}, sold={tv.total_sold}, revenue={tv.total_revenue}")
    try:
        purchase(tv.pk, 99)
    except InsufficientStock as e:
        print("Rejected as expected:", e)
