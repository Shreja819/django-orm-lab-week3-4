"""Part 6: Advanced Challenge Exercises (Q objects & F expressions).

Standalone script: it does NOT need a 'challenges' app, migrations or your
project database. It creates the Category/Product tables in a temporary
in-memory SQLite database, runs the four challenges, and then discards it.

Run from anywhere (the virtual environment must be active):
    python part6_challenges.py
"""
import sys
from decimal import Decimal

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
    )
django.setup()

from django.db import connection, models, transaction  # noqa: E402
from django.db.models import Case, DecimalField, F, Q, When  # noqa: E402
from django.db.models.lookups import GreaterThan  # noqa: E402


# ------------------------------------------------------------ schema (from the lab sheet)
class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "part6_demo"


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_allowed_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)  # Minimum stock threshold
    is_promotional = models.BooleanField(default=False)
    status = models.CharField(max_length=50)  # 'NORMAL', 'DISCOUNTED', 'CLEARANCE'
    warehouse_country = models.CharField(max_length=50)
    total_sold = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        app_label = "part6_demo"


def create_tables():
    with connection.schema_editor() as editor:
        editor.create_model(Category)
        editor.create_model(Product)


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


PRODUCT_HEADERS = ["Product", "Category", "Price", "Stock", "Reorder", "Promo", "Status", "Country"]


def product_rows(qs):
    return [
        (p.name, p.category.name, f"{p.price:,.2f}", p.stock_quantity, p.reorder_level,
         "Yes" if p.is_promotional else "No", p.status, p.warehouse_country)
        for p in qs.select_related("category").order_by("id")
    ]


# ------------------------------------------------------------ sample data
def seed():
    elec = Category.objects.create(name="Electronics")
    gadg = Category.objects.create(name="Gadgets")
    home = Category.objects.create(name="Home")

    def mk(name, cat, price, maxp, stock, reorder, promo, status, country):
        Product.objects.create(
            name=name, category=cat, price=Decimal(price), max_allowed_price=Decimal(maxp),
            stock_quantity=stock, reorder_level=reorder, is_promotional=promo,
            status=status, warehouse_country=country)

    mk("4K TV", elec, "25000", "30000", 5, 10, False, "NORMAL", "Japan")
    mk("Budget Phone", elec, "8000", "9000", 30, 10, False, "NORMAL", "China")
    mk("Gaming Laptop", elec, "45000", "50000", 12, 10, True, "NORMAL", "Taiwan")
    mk("Smart Watch", gadg, "1000", "1100", 15, 10, True, "NORMAL", "China")     # +15% = 1150 -> capped at 1100
    mk("Earbuds", gadg, "2000", "3000", 8, 10, False, "DISCOUNTED", "Vietnam")   # +15% = 2300 -> allowed
    mk("Desk Lamp", home, "500", "800", 40, 10, False, "DISCOUNTED", "China")
    mk("Sofa", home, "12000", "15000", 25, 10, True, "CLEARANCE", "Thailand")


# ------------------------------------------------------------ Challenge 1
def challenge_1():
    """(Electronics AND price > 10,000) OR (DISCOUNTED AND country != China)."""
    return Product.objects.filter(
        Q(category__name="Electronics", price__gt=10000)
        | (Q(status="DISCOUNTED") & ~Q(warehouse_country="China"))
    )


# ------------------------------------------------------------ Challenge 2
def challenge_2():
    """stock <= reorder_level  OR  (promotional AND stock < reorder_level * 2)."""
    return Product.objects.filter(
        Q(stock_quantity__lte=F("reorder_level"))
        | Q(is_promotional=True, stock_quantity__lt=F("reorder_level") * 2)
    )


# ------------------------------------------------------------ Challenge 3
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
    # Shorter alternative (DB-side MIN):
    #   from django.db.models.functions import Least
    #   .update(price=Least(F("price") * Decimal("1.15"), F("max_allowed_price")))


# ------------------------------------------------------------ Challenge 4
class InsufficientStock(Exception):
    pass


def purchase(product_id, qty):
    """The stock check lives in the WHERE clause of the UPDATE itself, so check and
    change are one atomic SQL statement. 0 rows updated => not enough stock."""
    with transaction.atomic():
        rows = Product.objects.filter(
            pk=product_id, stock_quantity__gte=qty
        ).update(
            stock_quantity=F("stock_quantity") - qty,
            total_sold=F("total_sold") + qty,
            total_revenue=F("total_revenue") + F("price") * qty,
        )
        if rows == 0:
            raise InsufficientStock(f"cannot buy {qty}: not enough stock")
    return rows


def run():
    create_tables()
    seed()
    checks = []

    title("SAMPLE DATA (7 products)")
    table(PRODUCT_HEADERS, product_rows(Product.objects.all()))

    # ---- Challenge 1
    title("CHALLENGE 1  Q objects: (Electronics AND price > 10,000) OR (DISCOUNTED AND NOT China)")
    c1 = challenge_1()
    table(PRODUCT_HEADERS, product_rows(c1))
    names1 = sorted(p.name for p in c1)
    print("\nNot returned: Budget Phone (price too low), Smart Watch (not discounted),")
    print("              Desk Lamp (discounted but ships from China), Sofa (not discounted)")
    checks.append(("Challenge 1 returns 4K TV, Earbuds, Gaming Laptop",
                   names1 == ["4K TV", "Earbuds", "Gaming Laptop"]))

    # ---- Challenge 2
    title("CHALLENGE 2  F + Q: stock <= reorder_level OR (promotional AND stock < reorder_level x 2)")
    c2 = challenge_2()
    table(PRODUCT_HEADERS, product_rows(c2))
    names2 = sorted(p.name for p in c2)
    print("\nNot returned: Budget Phone (30 stock), Desk Lamp (40 stock), Sofa (25 is not below 20)")
    checks.append(("Challenge 2 returns 4K TV, Earbuds, Gaming Laptop, Smart Watch",
                   names2 == ["4K TV", "Earbuds", "Gaming Laptop", "Smart Watch"]))

    # ---- Challenge 3
    title("CHALLENGE 3  Atomic +15% price rise for Gadgets, capped at max_allowed_price")
    before = {p.pk: p.price for p in Product.objects.filter(category__name="Gadgets")}
    updated = challenge_3()
    print(f"\nRows updated with ONE SQL UPDATE: {updated}\n")
    rows = []
    after = {}
    for p in Product.objects.filter(category__name="Gadgets").order_by("id"):
        after[p.name] = p.price
        note = "capped at max" if p.price == p.max_allowed_price else "+15%"
        rows.append((p.name, f"{before[p.pk]:,.2f}", f"{p.max_allowed_price:,.2f}",
                     f"{p.price:,.2f}", note))
    table(["Product", "Old price", "Max allowed", "New price", "Result"], rows)
    checks.append(("Challenge 3 caps Smart Watch at 1,100.00 and raises Earbuds to 2,300.00",
                   after.get("Smart Watch") == Decimal("1100.00")
                   and after.get("Earbuds") == Decimal("2300.00")))

    # ---- Challenge 4
    title("CHALLENGE 4  Atomic purchase guard (no race condition)")
    tv = Product.objects.get(name="4K TV")
    print(f"\nStart:  stock={tv.stock_quantity}, total_sold={tv.total_sold}, "
          f"total_revenue={tv.total_revenue:,.2f}  (price {tv.price:,.2f})")
    purchase(tv.pk, 2)
    tv.refresh_from_db()
    print(f"Buy 2:  stock={tv.stock_quantity}, total_sold={tv.total_sold}, "
          f"total_revenue={tv.total_revenue:,.2f}   -> SUCCESS")
    ok_buy = (tv.stock_quantity, tv.total_sold, tv.total_revenue) == (3, 2, Decimal("50000.00"))
    rejected = False
    try:
        purchase(tv.pk, 99)
    except InsufficientStock as e:
        rejected = True
        print(f"Buy 99: {e}   -> REJECTED (nothing changed)")
    tv.refresh_from_db()
    checks.append(("Challenge 4 buy 2 succeeds (stock 5 -> 3, sold 2, revenue 50,000)", ok_buy))
    checks.append(("Challenge 4 buy 99 is rejected and stock stays at 3",
                   rejected and tv.stock_quantity == 3))

    # ---- Summary
    title("SELF-CHECK")
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    print("\n(Temporary in-memory database: nothing was saved, so you can run this again.)")


if __name__ == "__main__":
    run()
