import copy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from commercegraph.config import Settings
from commercegraph.models import make_query
from commercegraph.queries import execute_query
from commercegraph.resolution import resolve_plan
from commercegraph.ui.graph_view import evidence_graph, graph_figure, relationship_rows

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def offline_app(monkeypatch):
    monkeypatch.setenv("APP_MODE", "offline")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.delenv("COMMERCEGRAPH_DATASET", raising=False)
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def test_explicit_submit_navigation_no_duplicate_inference(offline_app):
    app = offline_app
    calls = []
    provider = app.session_state["service"].provider
    original = provider.plan_query
    provider.plan_query = lambda *args: (calls.append("query"), original(*args))[1]
    app.button(key="example_Q05").click().run()
    assert app.text_area[0].value == "What is the merchandise total for order O01?"
    assert calls == []
    button(app, "Run offline example").click().run()
    assert not app.exception
    assert calls == ["query"]
    assert "5,397.00" in app.session_state["result"]["answer"]
    app.radio[0].set_value("Explore the graph").run()
    assert not app.exception
    app.selectbox[0].set_value("product:P01").run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception
    app.multiselect[0].set_value(["Product", "Brand"]).run()
    assert not app.exception
    app.radio[0].set_value("Dataset & checks").run()
    assert not app.exception
    assert [m.value for m in app.metric] == ["58", "83", "5"]
    app.selectbox[0].set_value("order_items").run()
    assert not app.exception
    app.radio[0].set_value("Ask the graph").run()
    assert calls == ["query"] and len(app.session_state["history"]) == 1


def test_failed_new_request_does_not_show_old_answer_as_current(offline_app):
    app = offline_app
    app.button(key="example_Q05").click().run()
    button(app, "Run offline example").click().run()
    app.text_area[0].set_value("unlisted question").run()
    button(app, "Run offline example").click().run()
    assert not app.exception
    assert app.session_state["result"]["question"] == "unlisted question"
    assert app.session_state["result"]["status"] == "llm_unavailable"
    assert app.session_state["history"][0]["status"] == "ok"


@pytest.mark.parametrize(
    "identifier,status",
    [
        ("Q01", "ok"),
        ("Q08", "ok"),
        ("Q10", "no_data"),
        ("Q11", "entity_not_found"),
        ("Q12", "unsupported"),
    ],
)
def test_ui_fixture_states(offline_app, identifier, status):
    from commercegraph.llm import example_cases

    app = offline_app
    question = next(c["question"] for c in example_cases() if c["id"] == identifier)
    app.text_area[0].set_value(question).run()
    button(app, "Run offline example").click().run()
    assert not app.exception and app.session_state["result"]["status"] == status


def test_missing_key_keeps_exploration_available(monkeypatch):
    monkeypatch.setenv("APP_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception and button(app, "Ask the graph").disabled
    app.radio[0].set_value("Explore the graph").run()
    assert not app.exception


def test_invalid_dataset_blocks_app(monkeypatch, tmp_path):
    broken = tmp_path / "invalid.json"
    broken.write_text("{}")
    monkeypatch.setenv("COMMERCEGRAPH_DATASET", str(broken))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception and app.error
    assert "Dataset/configuration error" in app.error[0].value
    assert not app.text_area


def test_config_refresh_does_not_cache_dotenv(monkeypatch, tmp_path):
    for name in ["GEMINI_API_KEY", "APP_MODE", "GEMINI_MODEL", "COMMERCEGRAPH_DATASET"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=first\nAPP_MODE=live\n")
    assert Settings.from_env().api_key == "first"
    (tmp_path / ".env").write_text("GEMINI_API_KEY=second\nAPP_MODE=live\n")
    assert Settings.from_env().api_key == "second"


def test_graph_visuals_preserve_graph_and_only_show_evidence(graph):
    before = copy.deepcopy(dict(graph.nodes(data=True)))
    bundle = execute_query(graph, resolve_plan(graph, make_query("order_details", order_id="O01")))
    visual = evidence_graph(bundle.model_dump())
    assert set(visual.edges) == {(e.source, e.target) for e in bundle.edges}
    figure = graph_figure(visual, focused=True, evidence_nodes=visual.nodes)
    assert figure.layout.annotations
    graph_figure(graph)
    assert dict(graph.nodes(data=True)) == before
    assert {r["direction"] for r in relationship_rows(graph, "product:P01")} == {
        "Incoming",
        "Outgoing",
    }
    assert graph_figure(visual.subgraph([])).layout.annotations[0].text


@pytest.mark.parametrize("state", ["clarification", "fallback", "zero", "api_error"])
def test_ui_remaining_states(monkeypatch, state):
    from commercegraph.answers import default_answer_plan
    from commercegraph.llm import LLMError, ModelReply
    from commercegraph.models import Parameters, QueryPlan
    from commercegraph.service import create_service

    class StateProvider:
        def plan_query(self, question, catalog):
            if state == "api_error":
                raise LLMError("api_429", "Gemini quota or rate limit reached.")
            if state == "clarification":
                return ModelReply(
                    QueryPlan(
                        decision="clarify",
                        operation=None,
                        parameters=Parameters(**dict.fromkeys(Parameters.model_fields)),
                        clarification_code="missing_entity",
                        unsupported_code=None,
                    )
                )
            if state == "zero":
                return ModelReply(
                    make_query(
                        "find_products",
                        category_name="Outdoors",
                        price_lt_inr="799",
                        output_mode="count",
                    )
                )
            return ModelReply(make_query("order_details", order_id="O01"))

        def plan_answer(self, question, query, evidence):
            if state == "fallback":
                raise LLMError("invalid_plan", "Invalid presentation")
            return ModelReply(default_answer_plan(evidence))

    monkeypatch.setenv("APP_MODE", "offline")
    monkeypatch.setattr(
        "commercegraph.ui.views.create_service",
        lambda settings: create_service(settings, StateProvider()),
    )
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_area[0].set_value("Test question").run()
    button(app, "Run offline example").click().run()
    assert not app.exception
    result = app.session_state["result"]
    if state == "fallback":
        assert result["answer_presentation_source"] == "deterministic_fallback" and app.warning
    elif state == "zero":
        assert result["status"] == "ok" and "0 matching" in result["answer"]
    else:
        expected = "clarification_required" if state == "clarification" else "llm_unavailable"
        assert result["status"] == expected


def test_readable_rows_use_currency_and_avoid_nested_objects():
    from commercegraph.ui.views import readable_rows

    rows = readable_rows(
        [
            {
                "record_id": "R001",
                "fields": {
                    "total_paise": 539700,
                    "items": [{"name": "item"}],
                    "product_ids": ["P01", "P02"],
                },
            }
        ]
    )
    assert rows == [{"Evidence ID": "R001", "Total": "INR 5,397.00", "Product Ids": "P01, P02"}]
