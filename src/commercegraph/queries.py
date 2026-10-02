"""Seven allowlisted traversals. Retrieval never reads source JSON."""

import networkx as nx

from commercegraph.evidence import EvidenceBuilder, EvidenceBundle
from commercegraph.graph import node_key
from commercegraph.models import ResolvedPlan, make_query
from commercegraph.resolution import normalize, resolve_plan


def related(graph: nx.DiGraph, key: str, relationship: str, incoming=False) -> list[str]:
    edges = graph.in_edges(key, data=True) if incoming else graph.out_edges(key, data=True)
    return sorted(
        source if incoming else target
        for source, target, attrs in edges
        if attrs["type"] == relationship
    )


def order_facts(graph: nx.DiGraph, order: str) -> tuple[dict, set, set]:
    attrs = graph.nodes[order]
    owner = related(graph, order, "PLACED", incoming=True)[0]
    nodes = {order, owner}
    pairs = {(owner, order)}
    lines = []
    for item in related(graph, order, "HAS_ITEM"):
        line = graph.nodes[item]
        product = related(graph, item, "FOR_PRODUCT")[0]
        nodes.update([item, product])
        pairs.update([(order, item), (item, product)])
        lines.append(
            {
                "item_id": line["id"],
                "product_id": graph.nodes[product]["id"],
                "product_name": graph.nodes[product]["name"],
                "quantity": line["quantity"],
                "unit_price_paise": line["unit_price_paise"],
                "line_total_paise": line["quantity"] * line["unit_price_paise"],
            }
        )
    return (
        {
            "id": attrs["id"],
            "date": attrs["date"],
            "status": attrs["status"],
            "customer_id": graph.nodes[owner]["id"],
            "customer_name": graph.nodes[owner]["name"],
            "total_paise": sum(line["line_total_paise"] for line in lines),
            "items": lines,
        },
        nodes,
        pairs,
    )


def _validated_plan(graph: nx.DiGraph, plan: ResolvedPlan) -> ResolvedPlan:
    """Apply the same operation contract and existence checks at execution boundary."""
    plan = ResolvedPlan.model_validate(plan.model_dump())
    fields = {
        "brand_id": "brand_name",
        "vendor_id": "vendor_name",
        "category_id": "category_name",
        "customer_id": "customer_name",
        "product_id": "product_name",
    }
    params = {}
    for field, value in plan.model_dump(exclude_none=True).items():
        if field == "operation":
            continue
        if field == "price_lt_paise":
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("Invalid price in paise")
            params["price_lt_inr"] = f"{value // 100}.{value % 100:02}"
        else:
            params[fields.get(field, field)] = value
    return resolve_plan(graph, make_query(plan.operation, **params))


def execute_query(graph: nx.DiGraph, plan: ResolvedPlan) -> EvidenceBundle:
    plan = _validated_plan(graph, plan)
    builder = EvidenceBuilder(graph)
    operation = plan.operation
    if operation == "find_products":
        for product, attrs in sorted(graph.nodes(data=True)):
            if attrs["type"] != "Product":
                continue
            brand = related(graph, product, "BELONGS_TO_BRAND")[0]
            category = related(graph, product, "IN_CATEGORY")[0]
            suppliers = related(graph, product, "SUPPLIES", incoming=True)
            if plan.brand_id and graph.nodes[brand]["id"] != plan.brand_id:
                continue
            if plan.category_id and graph.nodes[category]["id"] != plan.category_id:
                continue
            if plan.vendor_id and node_key("Vendor", plan.vendor_id) not in suppliers:
                continue
            if plan.price_lt_paise is not None and attrs["price_paise"] >= plan.price_lt_paise:
                continue
            pairs = {(product, brand), (product, category)}
            if plan.vendor_id:
                pairs.add((node_key("Vendor", plan.vendor_id), product))
            builder.add(
                "Product",
                {
                    "id": attrs["id"],
                    "name": attrs["name"],
                    "brand": graph.nodes[brand]["name"],
                    "category": graph.nodes[category]["name"],
                    "price_paise": attrs["price_paise"],
                },
                [product],
                pairs,
            )
    elif operation == "vendors_for_product":
        product = node_key("Product", plan.product_id)
        for vendor in related(graph, product, "SUPPLIES", incoming=True):
            attrs = graph.nodes[vendor]
            builder.add(
                "Vendor",
                {
                    "id": attrs["id"],
                    "name": attrs["name"],
                    "product_id": graph.nodes[product]["id"],
                    "product_name": graph.nodes[product]["name"],
                },
                pairs=[(vendor, product)],
            )
    elif operation in {"orders_for_customer", "order_details"}:
        orders = (
            [node_key("Order", plan.order_id)]
            if operation == "order_details"
            else related(graph, node_key("Customer", plan.customer_id), "PLACED")
        )
        for order in orders:
            if plan.order_status and graph.nodes[order]["status"] != plan.order_status:
                continue
            fields, nodes, pairs = order_facts(graph, order)
            builder.add("Order", fields, nodes, pairs)
        if operation == "order_details":
            return builder.bundle(plan, total_paise=builder.records[0].fields["total_paise"])
    elif operation == "customers_bought_brand":
        brand = node_key("Brand", plan.brand_id)
        for customer, attrs in sorted(graph.nodes(data=True)):
            if attrs["type"] != "Customer":
                continue
            pairs = set()
            matched_orders = set()
            for order in related(graph, customer, "PLACED"):
                if graph.nodes[order]["status"] != "delivered":
                    continue
                for item in related(graph, order, "HAS_ITEM"):
                    product = related(graph, item, "FOR_PRODUCT")[0]
                    if brand in related(graph, product, "BELONGS_TO_BRAND"):
                        pairs.update(
                            [(customer, order), (order, item), (item, product), (product, brand)]
                        )
                        matched_orders.add(graph.nodes[order]["id"])
            if pairs:
                builder.add(
                    "Customer",
                    {
                        "id": attrs["id"],
                        "name": attrs["name"],
                        "brand": graph.nodes[brand]["name"],
                        "delivered_order_ids": sorted(matched_orders),
                    },
                    pairs=pairs,
                )
    elif operation == "vendor_product_counts":
        for vendor, attrs in sorted(graph.nodes(data=True)):
            if attrs["type"] != "Vendor":
                continue
            products = related(graph, vendor, "SUPPLIES")
            builder.add(
                "Vendor",
                {
                    "id": attrs["id"],
                    "name": attrs["name"],
                    "product_count": len(set(products)),
                    "product_ids": [graph.nodes[key]["id"] for key in products],
                },
                nodes=[vendor],
                pairs=[(vendor, product) for product in products],
            )
    elif operation == "lookup_value":
        for marker, attrs in sorted(graph.nodes(data=True)):
            if attrs["type"] != "Marker" or normalize(attrs["value"]) != normalize(plan.value):
                continue
            product = related(graph, marker, "HAS_MARKER", incoming=True)[0]
            builder.add(
                "Marker",
                {
                    "id": attrs["id"],
                    "value": attrs["value"],
                    "product_id": graph.nodes[product]["id"],
                    "product_name": graph.nodes[product]["name"],
                },
                pairs=[(product, marker)],
            )
    else:
        raise ValueError("Operation is not allowed")
    return builder.bundle(plan)
