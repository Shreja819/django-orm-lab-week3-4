# Lab 3-4 — Solutions & Explanations (Part 4.4 and Part 6)

## Task 4.4 — Comparative analysis
| Method | Target relationship | SQL mechanism | Query count in lab | Use case |
|---|---|---|---|---|
| `select_related()` | ForeignKey / OneToOne | One `JOIN` | exactly 1 | Employee -> Department |
| `prefetch_related()` | ManyToMany / reverse FK | 2 queries, second uses `IN (...)` | exactly 2 | Course -> Attendees |
| Database indexing | fields used in filter/order_by | B-tree lookup | n/a | speed up `filter()`, `order_by()` |

## Challenge 1 — Q objects
```python
Product.objects.filter(
    Q(category__name="Electronics", price__gt=10000)
    | (Q(status="DISCOUNTED") & ~Q(warehouse_country="China"))
)
```
Keyword arguments inside one `Q(...)` are ANDed. `|` is OR, `&` is AND, `~` is NOT. Parentheses make the grouping explicit. The whole thing becomes a single `WHERE (A AND B) OR (C AND NOT D)`.

## Challenge 2 — F expression + Q
```python
Product.objects.filter(
    Q(stock_quantity__lte=F("reorder_level"))
    | Q(is_promotional=True, stock_quantity__lt=F("reorder_level") * 2)
)
```
`F("reorder_level")` compares one column with another column of the same row inside the database, so each product uses its own threshold. No Python loop is needed.

## Challenge 3 — Atomic price rise with ceiling
```python
new_price = F("price") * Decimal("1.15")
Product.objects.filter(category__name="Gadgets").update(
    price=Case(
        When(GreaterThan(new_price, F("max_allowed_price")), then=F("max_allowed_price")),
        default=new_price,
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
)
```
One `UPDATE ... SET price = CASE WHEN price*1.15 > max_allowed_price THEN max_allowed_price ELSE price*1.15 END`. Use `Decimal("1.15")`, not `1.15` (a float causes a mixed-types error with DecimalField).
Shorter alternative: `price=Least(F("price") * Decimal("1.15"), F("max_allowed_price"))`.

## Challenge 4 — Purchase guard (race-condition safe)
```python
rows = Product.objects.filter(pk=product_id, stock_quantity__gte=X).update(
    stock_quantity=F("stock_quantity") - X,
    total_sold=F("total_sold") + X,
    total_revenue=F("total_revenue") + F("price") * X,
)
if rows == 0:
    raise InsufficientStock(...)
```
The stock check is in the `WHERE` clause of the same `UPDATE`, so the check and the change are one atomic operation in the database. Two simultaneous buyers can't both pass the check on stale data (which a Python `if product.stock_quantity >= X` would allow). `rows == 0` means the guard failed. All three columns change together in one statement, wrapped in `transaction.atomic()`.
