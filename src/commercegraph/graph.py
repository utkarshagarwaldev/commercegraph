"""Graph construction and relationship invariants."""

import networkx as nx

from commercegraph.audit import require_audit
from commercegraph.dataset import Dataset

COLLECTION_TYPES = {
    "products": "Product",
    "brands": "Brand",
    "categories": "Category",
    "vendors": "Vendor",
    "customers": "Customer",
    "orders": "Order",
    "order_items": "OrderItem",
    "markers": "Marker",
}
RELATIONSHIPS = {
    "BELONGS_TO_BRAND": ("Product", "Brand"),
    "IN_CATEGORY": ("Product", "Category"),
    "SUPPLIES": ("Vendor", "Product"),
    "PLACED": ("Customer", "Order"),
    "HAS_ITEM": ("Order", "OrderItem"),
    "FOR_PRODUCT": ("OrderItem", "Product"),
    "HAS_MARKER": ("Product", "Marker"),
}


def node_key(kind: str, identifier: str) -> str:
    return f"{kind.lower()}:{identifier}"


def build_graph(dataset: Dataset) -> nx.DiGraph:
    graph = nx.DiGraph(schema_version=dataset.schema_version, currency=dataset.currency)
    for collection, kind in COLLECTION_TYPES.items():
        for record in getattr(dataset, collection):
            graph.add_node(node_key(kind, record.id), type=kind, **record.model_dump(mode="json"))

    def edge(source_type, source_id, relation, target_type, target_id):
        graph.add_edge(
            node_key(source_type, source_id), node_key(target_type, target_id), type=relation
        )

    for product in dataset.products:
        edge("Product", product.id, "BELONGS_TO_BRAND", "Brand", product.brand_id)
        edge("Product", product.id, "IN_CATEGORY", "Category", product.category_id)
    for supply in dataset.supplies:
        edge("Vendor", supply.vendor_id, "SUPPLIES", "Product", supply.product_id)
    for order in dataset.orders:
        edge("Customer", order.customer_id, "PLACED", "Order", order.id)
    for item in dataset.order_items:
        edge("Order", item.order_id, "HAS_ITEM", "OrderItem", item.id)
        edge("OrderItem", item.id, "FOR_PRODUCT", "Product", item.product_id)
    for marker in dataset.markers:
        edge("Product", marker.product_id, "HAS_MARKER", "Marker", marker.id)
    validate_graph(graph)
    return nx.freeze(graph)


def validate_graph(graph: nx.DiGraph) -> dict:
    for key, attrs in graph.nodes(data=True):
        kind = attrs.get("type")
        if kind not in COLLECTION_TYPES.values() or key != node_key(kind, attrs.get("id")):
            raise ValueError(f"Invalid node: {key}")
    for source, target, attrs in graph.edges(data=True):
        allowed = RELATIONSHIPS.get(attrs.get("type"))
        actual = (graph.nodes[source]["type"], graph.nodes[target]["type"])
        if allowed != actual:
            raise ValueError(f"Invalid relationship: {source} -> {target}")
    requirements = {
        "Product": ([("BELONGS_TO_BRAND", 1), ("IN_CATEGORY", 1)], []),
        "Order": ([("HAS_ITEM", None)], [("PLACED", 1)]),
        "OrderItem": ([("FOR_PRODUCT", 1)], [("HAS_ITEM", 1)]),
        "Marker": ([], [("HAS_MARKER", 1)]),
    }
    for key, attrs in graph.nodes(data=True):
        outgoing, incoming = requirements.get(attrs["type"], ([], []))
        for rules, edges in (
            (outgoing, graph.out_edges(key, data=True)),
            (incoming, graph.in_edges(key, data=True)),
        ):
            edges = list(edges)
            for relation, required in rules:
                count = sum(a["type"] == relation for _, _, a in edges)
                if (required is None and count < 1) or (required is not None and count != required):
                    raise ValueError(f"Invalid {relation} cardinality for {key}")
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "audit": require_audit(graph),
    }
