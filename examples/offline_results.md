# CommerceGraph actual offline execution report

Offline fixtures do not demonstrate real LLM integration.

## Q01

Which products from NovaTech are supplied by MetroSupply?

Status: `ok` · presentation: `offline-fixture`

```text
Found 3 matching records in the sample graph.
P01 · Wireless Headphones — INR 3,999.00 (NovaTech; Electronics)
P02 · Portable Speaker — INR 2,499.00 (NovaTech; Electronics)
P03 · Smartwatch — INR 5,999.00 (NovaTech; Electronics)
```

## Q02

Which vendors supply Portable Speaker?

Status: `ok` · presentation: `offline-fixture`

```text
Found 2 matching records in the sample graph.
V01 · MetroSupply supplies Portable Speaker (P02) in the catalog.
V03 · EverydayWholesale supplies Portable Speaker (P02) in the catalog.
```

## Q03

Which Outdoors products cost under INR 1500?

Status: `ok` · presentation: `offline-fixture`

```text
Found 2 matching records in the sample graph.
P05 · Insulated Bottle — INR 799.00 (TrailWorks; Outdoors)
P06 · Camping Lantern — INR 1,299.00 (TrailWorks; Outdoors)
```

## Q04

Show all orders placed by Asha Mehta.

Status: `ok` · presentation: `offline-fixture`

```text
Found 2 matching records in the sample graph.
O01 · delivered · 2026-09-01 · Asha Mehta — merchandise total INR 5,397.00
O04 · delivered · 2026-09-04 · Asha Mehta — merchandise total INR 2,096.00
```

## Q05

What is the merchandise total for order O01?

Status: `ok` · presentation: `offline-fixture`

```text
Found 1 matching record in the sample graph.
O01 · delivered · 2026-09-01 · Asha Mehta — merchandise total INR 5,397.00
  L01 · Wireless Headphones: 1 × INR 3,899.00 = INR 3,899.00
  L02 · Insulated Bottle: 2 × INR 749.00 = INR 1,498.00
Merchandise total only; tax and shipping are not modeled.
```

## Q06

Which customers bought products from NovaTech?

Status: `ok` · presentation: `offline-fixture`

```text
Found 3 matching records in the sample graph. Purchases include delivered orders only.
U01 · Asha Mehta — delivered orders: O01
U03 · Neha Rao — delivered orders: O03
U04 · Kabir Sen — delivered orders: O05
```

## Q07

How many distinct products does each vendor supply?

Status: `ok` · presentation: `offline-fixture`

```text
Found 3 matching records in the sample graph.
V01 · MetroSupply: 5 distinct supplied products
V02 · GreenRoute: 4 distinct supplied products
V03 · EverydayWholesale: 5 distinct supplied products
```

## Q08

Find all graph markers whose value is banana and show their products.

Status: `ok` · presentation: `offline-fixture`

```text
Found 5 matching records in the sample graph. These are artificial assignment markers.
M01 · value 'banana' → P01 · Wireless Headphones
M02 · value 'banana' → P04 · Hiking Backpack
M03 · value 'banana' → P07 · Electric Kettle
M04 · value 'banana' → P10 · Rolled Oats
M05 · value 'banana' → P12 · Herbal Tea
```

## Q09

How many graph markers have the value banana?

Status: `ok` · presentation: `offline-fixture`

```text
Found 5 matching graph markers in the sample graph.
```

## Q10

Which HomeNest products are supplied by GreenRoute?

Status: `no_data` · presentation: `offline-fixture`

```text
No matching records in the sample graph for the interpreted filters.
```

## Q11

Which products are from AcmeBrand?

Status: `entity_not_found` · presentation: `None`

```text
Brand 'AcmeBrand' was not found in the sample graph.
```

## Q12

What is the capital of France?

Status: `unsupported` · presentation: `None`

```text
This question is outside the sample commerce graph's supported scope.
```

## Q13

Which customers bought TrailWorks products?

Status: `ok` · presentation: `offline-fixture`

```text
Found 2 matching records in the sample graph. Purchases include delivered orders only.
U01 · Asha Mehta — delivered orders: O01
U02 · Rohan Shah — delivered orders: O02
```

## Q14

What is the merchandise total for order O07?

Status: `ok` · presentation: `offline-fixture`

```text
Found 1 matching record in the sample graph.
O07 · cancelled · 2026-09-07 · Arjun Nair — merchandise total INR 2,798.00
  L13 · Hiking Backpack: 1 × INR 1,999.00 = INR 1,999.00
  L14 · Insulated Bottle: 1 × INR 799.00 = INR 799.00
Merchandise total only; tax and shipping are not modeled.
```
