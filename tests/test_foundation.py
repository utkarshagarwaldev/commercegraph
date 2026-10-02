import copy
from pathlib import Path

import networkx as nx
import pytest
from pydantic import ValidationError

from commercegraph.audit import audit_graph, count_occurrences, require_audit
from commercegraph.dataset import Dataset, load_dataset
from commercegraph.graph import build_graph, validate_graph


def test_seed_counts_and_reproducible_graph(graph, dataset):
    assert validate_graph(graph) == {
        "nodes": 58,
        "edges": 83,
        "audit": {"marker_nodes": 5, "occurrences": 5, "passed": True},
    }
    other = build_graph(dataset)
    assert dict(graph.nodes(data=True)) == dict(other.nodes(data=True))
    assert set(graph.edges) == set(other.edges)
    assert sum(a["type"] == "SUPPLIES" for _, _, a in graph.edges(data=True)) == 14
    assert nx.is_frozen(graph)
    root = Path(__file__).resolve().parents[1]
    assert load_dataset(root / "data/ecommerce.json")[1] == load_dataset()[1]


@pytest.mark.parametrize(
    "collection",
    [
        "products",
        "brands",
        "categories",
        "vendors",
        "customers",
        "orders",
        "order_items",
        "markers",
    ],
)
def test_duplicate_ids(raw, collection):
    raw[collection].append(copy.deepcopy(raw[collection][0]))
    with pytest.raises(ValidationError, match="Duplicate IDs"):
        Dataset.model_validate(raw)


@pytest.mark.parametrize(
    "collection,field,value",
    [
        ("products", "price_paise", True),
        ("products", "price_paise", -1),
        ("products", "price_paise", 1.2),
        ("order_items", "quantity", False),
        ("order_items", "quantity", 0),
        ("order_items", "quantity", -2),
        ("order_items", "unit_price_paise", True),
        ("orders", "date", "2026-02-30"),
        ("orders", "status", "shipped"),
        ("products", "brand_id", "B99"),
        ("products", "category_id", "C99"),
        ("orders", "customer_id", "U99"),
        ("order_items", "order_id", "O99"),
        ("order_items", "product_id", "P99"),
        ("supplies", "vendor_id", "V99"),
        ("markers", "product_id", "P99"),
        ("products", "unexpected", "value"),
    ],
)
def test_invalid_values_and_references(raw, collection, field, value):
    raw[collection][0][field] = value
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)


def test_duplicate_supplies_and_empty_order(raw):
    broken = copy.deepcopy(raw)
    broken["supplies"].append(broken["supplies"][0])
    with pytest.raises(ValidationError, match="Duplicate supply"):
        Dataset.model_validate(broken)
    raw["order_items"] = [r for r in raw["order_items"] if r["order_id"] != "O01"]
    with pytest.raises(ValidationError, match="at least one"):
        Dataset.model_validate(raw)


@pytest.mark.parametrize(
    "location",
    ["graph", "node_key", "node_value", "node_attr_key", "edge_value", "edge_key", "nested"],
)
def test_audit_detects_extra_occurrences(graph, location):
    mutable = nx.DiGraph(graph)
    if location == "graph":
        mutable.graph["description"] = "banana"
    elif location == "node_key":
        mutable.add_node("banana")
    elif location == "node_value":
        mutable.nodes["product:P01"]["description"] = "BANANA"
    elif location == "node_attr_key":
        mutable.nodes["product:P01"]["banana"] = "unused"
    elif location == "edge_value":
        mutable.edges["product:P01", "brand:B01"]["extra"] = "banana"
    elif location == "edge_key":
        mutable.edges["product:P01", "brand:B01"]["banana"] = "unused"
    else:
        mutable.graph["extra"] = {"nested": ["none", ("banana",)]}
    assert audit_graph(mutable)["occurrences"] == 6
    with pytest.raises(ValueError, match="Marker integrity"):
        require_audit(mutable)


def test_audit_four_six_and_word_boundaries(graph):
    mutable = nx.DiGraph(graph)
    mutable.nodes["marker:M01"]["value"] = "missing"
    assert audit_graph(mutable)["occurrences"] == 4
    mutable.nodes["marker:M01"]["value"] = "banana banana"
    assert audit_graph(mutable)["occurrences"] == 6
    assert count_occurrences("Banana, BANANA! bananas prebanana banana_split") == 2


def test_invalid_graph_relationship_and_cardinality(graph):
    mutable = nx.DiGraph(graph)
    mutable.edges["product:P01", "brand:B01"]["type"] = "SUPPLIES"
    with pytest.raises(ValueError, match="Invalid relationship"):
        validate_graph(mutable)
    mutable = nx.DiGraph(graph)
    mutable.remove_edge("product:P01", "brand:B01")
    with pytest.raises(ValueError, match="cardinality"):
        validate_graph(mutable)


def test_six_marker_nodes_and_non_iso_dates_fail(graph, raw):
    mutable = nx.DiGraph(graph)
    mutable.add_node("marker:M06", type="Marker", id="M06", value="banana", product_id="P02")
    mutable.add_edge("product:P02", "marker:M06", type="HAS_MARKER")
    assert audit_graph(mutable)["marker_nodes"] == 6
    with pytest.raises(ValueError, match="Marker integrity"):
        require_audit(mutable)
    raw["schema_version"] = True
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)
    raw["schema_version"] = 1
    for invalid in [0, True, "2026-09-01T00:00:00", "20260901"]:
        raw["orders"][0]["date"] = invalid
        with pytest.raises(ValidationError):
            Dataset.model_validate(raw)
