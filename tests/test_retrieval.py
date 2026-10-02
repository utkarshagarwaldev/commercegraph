import json
from pathlib import Path

import networkx as nx
import pytest
from pydantic import ValidationError

from commercegraph.answers import default_answer_plan, render_answer, validate_answer_plan
from commercegraph.models import AnswerPlan, ResolvedPlan, make_query, to_paise
from commercegraph.queries import execute_query
from commercegraph.resolution import ResolutionError, resolve_entity, resolve_plan

CASES = json.loads((Path(__file__).parent / "fixtures/expected_cases.json").read_text())


@pytest.mark.parametrize("case", [c for c in CASES if "operation" in c], ids=lambda c: c["id"])
def test_independently_expected_cases(graph, case):
    query = make_query(case["operation"], **case["parameters"])
    if case["status"] == "entity_not_found":
        with pytest.raises(ResolutionError) as error:
            resolve_plan(graph, query)
        assert error.value.status == case["status"]
        return
    evidence = execute_query(graph, resolve_plan(graph, query))
    assert evidence.status == case["status"]
    fields = [r.fields for r in evidence.records]
    assert [f["id"] for f in fields] == case["ids"]
    assert evidence.aggregates["matching_count"] == len(case["ids"])
    for expected_key, field in [
        ("prices_paise", "price_paise"),
        ("totals_paise", "total_paise"),
        ("counts", "product_count"),
        ("product_ids", "product_id"),
        ("order_statuses", "status"),
    ]:
        if expected_key in case:
            assert [f[field] for f in fields] == case[expected_key]
    for edge in evidence.edges:
        assert graph.edges[edge.source, edge.target]["type"] == edge.relationship
    for node, attrs in evidence.nodes.items():
        assert attrs == graph.nodes[node]
    assert render_answer(default_answer_plan(evidence), evidence)


def test_strict_price_distinct_counts_and_empty_modes(graph):
    query = make_query("find_products", category_name="Outdoors", price_lt_inr="799")
    assert execute_query(graph, resolve_plan(graph, query)).status == "no_data"
    query = make_query(
        "find_products", category_name="Outdoors", price_lt_inr="799", output_mode="count"
    )
    bundle = execute_query(graph, resolve_plan(graph, query))
    assert bundle.status == "ok" and bundle.aggregates["matching_count"] == 0
    assert "0 matching distinct products" in render_answer(default_answer_plan(bundle), bundle)
    query = make_query("find_products", brand_name="NovaTech", output_mode="count")
    assert execute_query(graph, resolve_plan(graph, query)).aggregates["matching_count"] == 3


def test_all_order_totals_and_status_filter(graph):
    expected = [539700, 329800, 299700, 209600, 699800, 179600, 279800, 119500]
    for i, total in enumerate(expected, 1):
        plan = resolve_plan(graph, make_query("order_details", order_id=f"O{i:02}"))
        assert execute_query(graph, plan).aggregates["total_paise"] == total
    plan = resolve_plan(
        graph, make_query("orders_for_customer", customer_name="Rohan Shah", order_status="pending")
    )
    assert [r.fields["id"] for r in execute_query(graph, plan).records] == ["O08"]


def test_resolution_exact_normalized_ambiguous_and_missing(graph):
    assert resolve_entity(graph, "Brand", "  novatech ") == "B01"
    assert resolve_entity(graph, "Customer", " Asha   Mehta ") == "U01"
    assert resolve_entity(graph, "Product", "P01") == "P01"
    with pytest.raises(ResolutionError):
        resolve_entity(graph, "Brand", "NovaTec")
    ambiguous = nx.DiGraph(graph)
    ambiguous.add_node("brand:B99", type="Brand", id="B99", name="NovaTech")
    with pytest.raises(ResolutionError) as error:
        resolve_entity(ambiguous, "Brand", "NovaTech")
    assert error.value.status == "clarification_required"


@pytest.mark.parametrize(
    "operation,params",
    [
        ("find_products", {}),
        ("find_products", {"customer_name": "Asha Mehta"}),
        ("vendors_for_product", {"product_name": "P01", "output_mode": "count"}),
        ("customers_bought_brand", {"brand_name": "B01", "order_status": "cancelled"}),
        ("vendor_product_counts", {"vendor_name": "V01"}),
        ("order_details", {"order_id": "O01", "price_lt_inr": "100"}),
        ("lookup_value", {"value": " "}),
        ("orders_for_customer", {}),
        ("__import__('os').system", {}),
    ],
)
def test_operation_parameter_contract(operation, params):
    with pytest.raises(ValidationError):
        make_query(operation, **params)


@pytest.mark.parametrize("value", ["1.001", "-1", "NaN", "Infinity", "1e3", "1,000", " 1"])
def test_invalid_money(value):
    with pytest.raises(ValueError):
        to_paise(value)


def test_exact_money_and_invalid_execution_ids(graph):
    assert to_paise("0.29") == 29
    with pytest.raises(ResolutionError):
        execute_query(graph, ResolvedPlan(operation="order_details", order_id="O99"))
    with pytest.raises(ValidationError):
        execute_query(graph, ResolvedPlan(operation="vendor_product_counts", vendor_id="V01"))


@pytest.mark.parametrize(
    "mutation",
    [
        "template",
        "invented_record",
        "omit",
        "duplicate",
        "invented_aggregate",
        "omit_aggregate",
        "duplicate_aggregate",
    ],
)
def test_grounding_rejects_incorrect_references(graph, mutation):
    bundle = execute_query(graph, resolve_plan(graph, make_query("order_details", order_id="O01")))
    raw = default_answer_plan(bundle).model_dump()
    if mutation == "template":
        raw["template_id"] = "product_list"
    elif mutation == "invented_record":
        raw["record_ids"] = ["R999"]
    elif mutation == "omit":
        raw["record_ids"] = []
    elif mutation == "duplicate":
        raw["record_ids"] *= 2
    elif mutation == "invented_aggregate":
        raw["aggregate_keys"].append("imaginary_total")
    elif mutation == "omit_aggregate":
        raw["aggregate_keys"] = []
    else:
        raw["aggregate_keys"] *= 2
    with pytest.raises(ValueError):
        validate_answer_plan(AnswerPlan(**raw), bundle)


def test_zero_vendor_and_evidence_complete_paths(graph):
    mutable = nx.DiGraph(graph)
    mutable.add_node("vendor:V99", type="Vendor", id="V99", name="NoSupply")
    bundle = execute_query(mutable, ResolvedPlan(operation="vendor_product_counts"))
    assert bundle.records[-1].fields["product_count"] == 0
    assert bundle.records[-1].node_ids == ["vendor:V99"]
    bundle = execute_query(graph, resolve_plan(graph, make_query("order_details", order_id="O01")))
    assert {"orderitem:L01", "orderitem:L02"} <= bundle.nodes.keys()
    assert {(e.source, e.target) for e in bundle.edges} == {
        ("customer:U01", "order:O01"),
        ("order:O01", "orderitem:L01"),
        ("order:O01", "orderitem:L02"),
        ("orderitem:L01", "product:P01"),
        ("orderitem:L02", "product:P05"),
    }


def test_repeated_product_lines_preserve_historical_amounts(raw):
    from commercegraph.dataset import Dataset
    from commercegraph.graph import build_graph

    raw["order_items"].append(
        {
            "id": "L17",
            "order_id": "O01",
            "product_id": "P01",
            "quantity": 1,
            "unit_price_paise": 389900,
        }
    )
    graph = build_graph(Dataset.model_validate(raw))
    bundle = execute_query(graph, resolve_plan(graph, make_query("order_details", order_id="O01")))
    assert bundle.aggregates["total_paise"] == 929600
    assert len(bundle.records[0].fields["items"]) == 3
    with pytest.raises(ValidationError):
        ResolvedPlan(operation="find_products", price_lt_paise=True)
