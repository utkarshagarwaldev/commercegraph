"""Maintainer utility: reproduce the fixed sample fixture, never query-time data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def named(prefix, names):
    return [{"id": f"{prefix}{i:02}", "name": name} for i, name in enumerate(names, 1)]


data = {
    "schema_version": 1,
    "currency": "INR",
    "brands": named("B", ["NovaTech", "TrailWorks", "HomeNest", "PantryCo"]),
    "categories": named("C", ["Electronics", "Outdoors", "Home", "Grocery"]),
    "vendors": named("V", ["MetroSupply", "GreenRoute", "EverydayWholesale"]),
    "customers": named(
        "U", ["Asha Mehta", "Rohan Shah", "Neha Rao", "Kabir Sen", "Meera Das", "Arjun Nair"]
    ),
}
names = [
    "Wireless Headphones",
    "Portable Speaker",
    "Smartwatch",
    "Hiking Backpack",
    "Insulated Bottle",
    "Camping Lantern",
    "Electric Kettle",
    "Desk Lamp",
    "Storage Basket",
    "Rolled Oats",
    "Mixed Nuts",
    "Herbal Tea",
]
prices = [399900, 249900, 599900, 199900, 79900, 129900, 149900, 99900, 49900, 24900, 39900, 19900]
data["products"] = [
    {
        **product,
        "brand_id": f"B{(i // 3) + 1:02}",
        "category_id": f"C{(i // 3) + 1:02}",
        "price_paise": prices[i],
    }
    for i, product in enumerate(named("P", names))
]
data["supplies"] = [
    {"vendor_id": f"V{vendor:02}", "product_id": f"P{product:02}"}
    for vendor, products in [(1, [1, 2, 3, 7, 8]), (2, [4, 5, 6, 10]), (3, [2, 9, 10, 11, 12])]
    for product in products
]
data["orders"] = [
    {
        "id": f"O{i:02}",
        "customer_id": f"U{customer:02}",
        "date": f"2026-09-{i:02}",
        "status": "delivered" if i <= 6 else "cancelled" if i == 7 else "pending",
    }
    for i, customer in enumerate([1, 2, 3, 1, 4, 5, 6, 2], 1)
]
lines = [
    (1, 1, 1, 389900),
    (1, 5, 2, 74900),
    (2, 4, 1, 199900),
    (2, 6, 1, 129900),
    (3, 2, 1, 249900),
    (3, 10, 2, 24900),
    (4, 7, 1, 149900),
    (4, 12, 3, 19900),
    (5, 3, 1, 599900),
    (5, 8, 1, 99900),
    (6, 11, 2, 39900),
    (6, 9, 2, 49900),
    (7, 4, 1, 199900),
    (7, 5, 1, 79900),
    (8, 10, 4, 24900),
    (8, 12, 1, 19900),
]
data["order_items"] = [
    {
        "id": f"L{i:02}",
        "order_id": f"O{order:02}",
        "product_id": f"P{product:02}",
        "quantity": quantity,
        "unit_price_paise": price,
    }
    for i, (order, product, quantity, price) in enumerate(lines, 1)
]
data["markers"] = [
    {"id": f"M{i:02}", "value": "banana", "product_id": f"P{product:02}"}
    for i, product in enumerate([1, 4, 7, 10, 12], 1)
]
for path in [ROOT / "data/ecommerce.json", ROOT / "src/commercegraph/data/ecommerce.json"]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print("Wrote canonical seed and identical packaged fixture.")
