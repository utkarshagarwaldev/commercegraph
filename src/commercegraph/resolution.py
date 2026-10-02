"""Resolve exact IDs or normalized canonical names within an entity type."""

import networkx as nx

from commercegraph.models import QueryPlan, ResolvedPlan, to_paise


class ResolutionError(ValueError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


def catalog(graph: nx.DiGraph) -> dict:
    result = {}
    for _, attrs in graph.nodes(data=True):
        if attrs["type"] in {"Product", "Brand", "Category", "Vendor", "Customer", "Order"}:
            result.setdefault(attrs["type"], []).append(
                {"id": attrs["id"], "name": attrs.get("name", attrs["id"])}
            )
    return result


def resolve_entity(graph: nx.DiGraph, kind: str, value: str) -> str:
    records = [attrs for _, attrs in graph.nodes(data=True) if attrs["type"] == kind]
    # IDs take precedence over names to preserve unambiguous identity.
    matches = [attrs["id"] for attrs in records if attrs["id"] == value.strip()]
    if not matches:
        matches = [
            attrs["id"]
            for attrs in records
            if normalize(attrs.get("name", attrs["id"])) == normalize(value)
        ]
    if not matches:
        raise ResolutionError(
            "entity_not_found", f"{kind} '{value}' was not found in the sample graph."
        )
    if len(matches) != 1:
        raise ResolutionError(
            "clarification_required", f"Multiple {kind.lower()}s match '{value}'; use an ID."
        )
    return matches[0]


def resolve_plan(graph: nx.DiGraph, query: QueryPlan) -> ResolvedPlan:
    # Revalidate at this boundary, even when passed a manually constructed instance.
    query = QueryPlan.model_validate(query.model_dump())
    if query.decision != "query":
        raise ValueError("Only a query decision can be resolved")
    params = query.parameters
    result = {"operation": query.operation}
    fields = {
        "brand": "Brand",
        "vendor": "Vendor",
        "category": "Category",
        "customer": "Customer",
        "product": "Product",
    }
    for field, kind in fields.items():
        value = getattr(params, f"{field}_name")
        if value is not None:
            result[f"{field}_id"] = resolve_entity(graph, kind, value)
    if params.order_id is not None:
        result["order_id"] = resolve_entity(graph, "Order", params.order_id)
    if params.price_lt_inr is not None:
        result["price_lt_paise"] = to_paise(params.price_lt_inr)
    result.update(
        value=params.value,
        output_mode=(params.output_mode or "list")
        if query.operation in {"find_products", "lookup_value"}
        else None,
        order_status=params.order_status,
    )
    return ResolvedPlan(**result)
