"""Reviewer-facing screens. Inference occurs only on explicit form submission."""

import hashlib
from collections import Counter

import streamlit as st

from commercegraph.answers import money
from commercegraph.audit import audit_graph
from commercegraph.config import Settings
from commercegraph.dataset import load_dataset
from commercegraph.export import graph_export, json_bytes, records_csv
from commercegraph.llm import example_cases
from commercegraph.service import create_service
from commercegraph.ui.design import (
    answer_text,
    apply_styles,
    ask_heading,
    empty_state,
    page_heading,
    section_heading,
    top_line,
)
from commercegraph.ui.graph_view import COLORS, evidence_graph, graph_figure, relationship_rows

PLOT_CONFIG = {
    "scrollZoom": True,
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}
EXAMPLE_LABELS = {
    "Q01": "Brand + vendor",
    "Q03": "Price filter",
    "Q05": "Order total",
    "Q06": "Customer purchases",
    "Q07": "Vendor counts",
    "Q08": "Graph markers",
}
EXAMPLE_ICONS = {
    "Q01": ":material/hub:",
    "Q03": ":material/sell:",
    "Q05": ":material/receipt_long:",
    "Q06": ":material/person:",
    "Q07": ":material/storefront:",
    "Q08": ":material/share:",
}


def fill_question(question):
    st.session_state["question"] = question


def readable_rows(records):
    rows = []
    for record in records:
        row = {"Evidence ID": record["record_id"]}
        for field, value in record["fields"].items():
            if field == "items":
                continue  # Purchase lines are shown in the answer and supporting evidence.
            if field.endswith("_paise"):
                row[field.removesuffix("_paise").replace("_", " ").title()] = money(value)
            elif isinstance(value, list):
                row[field.replace("_", " ").title()] = ", ".join(map(str, value))
            else:
                row[field.replace("_", " ").title()] = value
        rows.append(row)
    return rows


def show_result(result: dict, key: str):
    with st.container(border=True, key=f"{key}_answer"):
        section_heading("Your answer", "Grounded in the graph")
        st.caption(f"{result['mode'].upper()} · {result['status'].replace('_', ' ')}")
        source = result["answer_presentation_source"]
        if source == "deterministic_fallback":
            st.warning("Evidence-based fallback: the presentation stage failed or was unavailable.")
        elif source == "gemini":
            st.success("Evidence validated · Gemini presentation")
        elif source == "offline-fixture":
            st.info("Offline fixture demonstration · no LLM was called")
        elif result["status"] in {"llm_unavailable", "invalid_plan", "dataset_error"}:
            st.error("This question could not be completed.")
        aggregates = (result.get("evidence") or {}).get("aggregates", {})
        if "total_paise" in aggregates:
            summary = st.columns(2)
            summary[0].metric("Merchandise total", money(aggregates["total_paise"]))
            summary[1].metric("Matching records", aggregates.get("matching_count", 0))
        answer_text(result)
    bundle = result.get("evidence")
    if bundle is not None:
        records = bundle["records"]
        count_label = "record" if len(records) == 1 else "records"
        section_heading("Retrieved records", f"{len(records)} {count_label} · ready to export")
        if records:
            st.dataframe(
                readable_rows(records),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("No matching rows. Count queries can still return a valid zero.")
        downloads = st.columns(2)
        downloads[0].download_button(
            "Download records CSV",
            records_csv(records),
            file_name="commercegraph_records.csv",
            mime="text/csv",
            key=f"{key}_csv",
            icon=":material/download:",
            width="stretch",
        )
        downloads[1].download_button(
            "Download result JSON",
            json_bytes(result),
            file_name="commercegraph_result.json",
            mime="application/json",
            key=f"{key}_json",
            icon=":material/data_object:",
            width="stretch",
        )
        with st.expander("Inspect supporting evidence"):
            st.caption(
                "These relationships support the records above. IDs are application-assigned."
            )
            st.dataframe(bundle["edges"], hide_index=True, width="stretch")
            st.json({"aggregates": bundle["aggregates"], "nodes": bundle["nodes"]}, expanded=False)
            graph = evidence_graph(bundle)
            st.plotly_chart(
                graph_figure(graph, evidence_nodes=graph.nodes, focused=True),
                width="stretch",
                config=PLOT_CONFIG,
                key=f"{key}_proof_graph",
            )
    with st.expander("Inspect the interpreted query"):
        st.caption(
            "Review the filters: evidence validation cannot prove correct intent interpretation."
        )
        st.json(
            {
                "raw_plan": result["raw_plan"],
                "resolved_plan": result["resolved_plan"],
                "stage_durations_seconds": result["stage_durations_seconds"],
                "token_usage": result["token_usage"],
            },
            expanded=True,
        )


def ask_view(service):
    has_result = bool(st.session_state.get("result"))
    if has_result:
        page_heading(
            "Commerce intelligence",
            "Ask the graph.",
            "Keep exploring. Every answer comes with the records behind it.",
        )
    else:
        ask_heading()
    settings = service.settings
    offline = settings.mode == "offline"
    if offline and not has_result:
        st.info("Offline demonstration: choose a predefined example. No LLM inference runs.")
    elif not settings.api_key:
        st.info(
            "Set GEMINI_API_KEY in local .env, then refresh. Graph exploration is available now."
        )
    cases = example_cases()
    if "question" not in st.session_state:
        st.session_state["question"] = ""
    with st.form("question_panel", border=True):
        section_heading("What would you like to know?", "Natural language → graph evidence")
        question = st.text_area(
            "Your question",
            key="question",
            height=110,
            max_chars=1000,
            placeholder="Which products from NovaTech are supplied by MetroSupply?",
        )
        form_columns = st.columns([2.3, 1.2], vertical_alignment="center")
        form_columns[0].caption("Be specific. Include a product, brand, customer, or order ID.")
        submitted = form_columns[1].form_submit_button(
            "Ask the graph" if not offline else "Run offline example",
            type="primary",
            disabled=not offline and not settings.api_key,
            width="stretch",
            icon=":material/arrow_forward:",
        )
    suggestions = st.expander("Try another example") if has_result else st.container()
    with suggestions:
        if not has_result:
            section_heading("A few ways to get started", "Choose an example to fill the question")
        for row in range(2):
            columns = st.columns(3)
            for column, (identifier, label) in zip(
                columns, list(EXAMPLE_LABELS.items())[row * 3 : (row + 1) * 3]
            ):
                question_example = next(
                    case["question"] for case in cases if case["id"] == identifier
                )
                column.button(
                    label,
                    on_click=fill_question,
                    args=(question_example,),
                    key=f"example_{identifier}",
                    width="stretch",
                    icon=EXAMPLE_ICONS[identifier],
                    help=question_example,
                )
    st.caption("Each question stands alone. Name entities again in follow-up questions.")
    if submitted:
        with st.status("Processing your question", expanded=True) as progress:
            result = service.ask(question, on_stage=lambda label: progress.update(label=label))
            failed = result["status"] in {"llm_unavailable", "invalid_plan", "dataset_error"}
            progress.update(
                label="Request failed" if failed else "Request complete",
                state="error" if failed else "complete",
                expanded=False,
            )
        st.session_state["result"] = result
        st.session_state.setdefault("history", []).append(result)
        st.rerun()
    result = st.session_state.get("result")
    if result:
        show_result(result, "current")
    else:
        empty_state()
    history = st.session_state.get("history", [])
    if len(history) > 1:
        st.subheader("Earlier questions")
        for index, previous in reversed(list(enumerate(history[:-1]))):
            with st.expander(f"Question {index + 1} · {previous['status'].replace('_', ' ')}"):
                show_result(previous, f"history_{index}")


def explore_view(service):
    graph = service.graph
    page_heading(
        "Relationship explorer",
        "See how everything connects.",
        "Explore the commerce network. Select an entity to follow its relationships.",
    )
    with st.container(border=True, key="explorer_controls"):
        controls = st.columns(2)
        kinds = controls[0].multiselect("Entity types", list(COLORS), default=list(COLORS))
        keys = [None, *sorted(graph.nodes)]
        selected = controls[1].selectbox(
            "Search or select an entity",
            keys,
            format_func=lambda key: (
                "Choose an entity"
                if key is None
                else f"{graph.nodes[key].get('name', graph.nodes[key]['id'])} · {key}"
            ),
        )
        neighborhood = st.toggle(
            "Show selected entity's neighborhood", value=False, disabled=selected is None
        )
    visible = {key for key, attrs in graph.nodes(data=True) if attrs["type"] in kinds}
    if selected and neighborhood:
        visible &= {selected, *graph.predecessors(selected), *graph.successors(selected)}
    subgraph = graph.subgraph(visible).copy()
    result = st.session_state.get("result") or {}
    proof_nodes = set((result.get("evidence") or {}).get("nodes", {}))
    with st.container(border=True):
        section_heading(
            "Commerce network", f"{len(subgraph)} entities · {len(subgraph.edges)} links"
        )
        st.caption(
            "Pan, zoom, hover, or use Reset axes. Dark outlines highlight the latest evidence."
        )
        st.plotly_chart(
            graph_figure(subgraph, selected, proof_nodes, focused=neighborhood),
            config=PLOT_CONFIG,
            width="stretch",
            key="explorer_graph",
        )
    if selected:
        st.subheader("Selected entity")
        if selected not in visible:
            st.info("The selected entity is hidden by the current type filters.")
        st.dataframe(
            readable_rows([{"record_id": selected, "fields": dict(graph.nodes[selected])}]),
            hide_index=True,
            width="stretch",
        )
        with st.expander("Raw entity attributes"):
            st.json(dict(graph.nodes[selected]), expanded=True)
        st.subheader("Incoming and outgoing relationships")
        st.dataframe(relationship_rows(graph, selected), hide_index=True, width="stretch")
    else:
        st.info("Select an entity to inspect its attributes and relationship directions.")
    st.caption(
        "SUPPLIES represents catalog supply. It does not identify historical order fulfillment."
    )


def dataset_view(service):
    page_heading(
        "Data foundation",
        "Good answers start with good data.",
        "Browse the source records and the integrity checks behind every answer.",
    )
    audit = audit_graph(service.graph)
    metrics = st.columns(3)
    metrics[0].metric("Graph nodes", len(service.graph))
    metrics[1].metric("Directed relationships", len(service.graph.edges))
    metrics[2].metric("Marker occurrences", audit["occurrences"])
    if audit["passed"]:
        st.success(
            "Marker audit passed: five matching marker nodes and five standalone graph occurrences."
        )
    else:
        st.error("Dataset integrity failed. Questions are blocked.")
    st.write(
        "All entities and purchases are fictional. Currency is INR. Historical totals use "
        "purchase line prices and quantities; tax and shipping are not modeled."
    )
    dataset, _ = load_dataset(service.settings.dataset_path)
    collections = [
        "products",
        "brands",
        "categories",
        "vendors",
        "customers",
        "orders",
        "order_items",
        "supplies",
        "markers",
    ]
    collection = st.selectbox(
        "Source table", collections, format_func=lambda x: x.replace("_", " ").title()
    )
    st.dataframe(
        [record.model_dump(mode="json") for record in getattr(dataset, collection)],
        hide_index=True,
        width="stretch",
    )
    columns = st.columns(2)
    columns[0].download_button(
        "Download source JSON",
        json_bytes(dataset.model_dump(mode="json")),
        file_name="ecommerce.json",
        mime="application/json",
        width="stretch",
        icon=":material/download:",
    )
    columns[1].download_button(
        "Download graph JSON",
        json_bytes(graph_export(service.graph)),
        file_name="commercegraph_graph.json",
        mime="application/json",
        width="stretch",
        icon=":material/hub:",
    )
    with st.expander("Supported queries and scope", expanded=True):
        st.dataframe(
            [
                {
                    "operation": case.get("operation", case.get("decision")),
                    "example": case["question"],
                }
                for case in example_cases()[:9]
            ],
            hide_index=True,
            width="stretch",
        )
        st.write(
            "Supported: relationship filters, strict upper prices, customer orders, order details, "
            "delivered brand purchases, vendor counts, and marker lookup."
        )
        st.caption(
            "Date ranges, rankings, recommendations, inventory, ratings, taxes, actual seller, "
            "vendor revenue, and external facts are unsupported."
        )
    with st.expander("Integrity details"):
        st.json(
            {
                "audit": audit,
                "dataset_sha256": service.dataset_hash,
                "node_types": dict(Counter(a["type"] for _, a in service.graph.nodes(data=True))),
            }
        )


def main():
    st.set_page_config(page_title="CommerceGraph", page_icon="◈", layout="wide")
    apply_styles()
    try:
        settings = Settings.from_env()
        _, digest = load_dataset(settings.dataset_path)
        signature = (
            settings.mode,
            settings.model,
            settings.dataset_path,
            digest,
            settings.tls12,
            hashlib.sha256(settings.api_key.encode()).hexdigest(),
        )
        if st.session_state.get("service_signature") != signature:
            st.session_state["service"] = create_service(settings)
            st.session_state["service_signature"] = signature
        service = st.session_state["service"]
    except (ValueError, OSError):
        st.title("CommerceGraph")
        st.error(
            "Dataset/configuration error. Check JSON schema, IDs, references, and the marker audit."
        )
        st.stop()
    with st.sidebar:
        st.markdown(
            '<div class="cg-brand"><div class="cg-logo">◇</div>'
            '<div class="cg-brand-name">CommerceGraph</div></div>'
            '<div class="cg-brand-sub">Connected data. Clear answers.</div>'
            '<div class="cg-sidebar-label">WORKSPACE</div>',
            unsafe_allow_html=True,
        )
        view = st.radio(
            "Workspace",
            ["Ask the graph", "Explore the graph", "Dataset & checks"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown('<div class="cg-sidebar-label">EXECUTION MODE</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="cg-status"><span class="cg-dot"></span>'
            + ("Live · Gemini" if settings.mode == "live" else "Offline demonstration")
            + "</div>",
            unsafe_allow_html=True,
        )
        if settings.mode == "live":
            st.caption(f"Gemini · {settings.model}")
            last = st.session_state.get("result") or {}
            if last.get("answer_presentation_source") == "gemini":
                st.success("Last query completed with Gemini")
            else:
                st.caption("Key configured" if settings.api_key else "Gemini key required")
        else:
            st.caption("Predefined fixtures · no LLM calls")
        st.divider()
        st.markdown('<div class="cg-sidebar-label">YOUR DATASET</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cg-sidebar-foot">{len(service.graph)} entities &nbsp;·&nbsp; '
            f"{len(service.graph.edges)} relationships<br>Synthetic commerce sample · INR</div>",
            unsafe_allow_html=True,
        )
        if settings.mode == "live" and not settings.api_key:
            st.caption("Set GEMINI_API_KEY in .env and refresh to enable questions.")
        st.button("Refresh configuration", width="stretch", icon=":material/refresh:")
    with st.container(key="workspace_content"):
        top_line(view, settings.mode)
        {
            "Ask the graph": ask_view,
            "Explore the graph": explore_view,
            "Dataset & checks": dataset_view,
        }[view](service)
