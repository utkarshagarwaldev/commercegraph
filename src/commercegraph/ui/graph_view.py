"""Nonmutating Plotly views; evidence graphs contain only supporting edges."""

from html import escape

import networkx as nx
import plotly.graph_objects as go

COLORS = {
    "Product": "#087F72",
    "Brand": "#8971B5",
    "Category": "#C9943D",
    "Vendor": "#468BBD",
    "Customer": "#C16E93",
    "Order": "#3B586B",
    "OrderItem": "#93A5B1",
    "Marker": "#81A64D",
}


def evidence_graph(evidence: dict) -> nx.DiGraph:
    graph = nx.DiGraph()
    for key, attrs in evidence["nodes"].items():
        graph.add_node(key, **dict(attrs))
    for edge in evidence["edges"]:
        graph.add_edge(edge["source"], edge["target"], type=edge["relationship"])
    return graph


def graph_figure(graph: nx.DiGraph, selected=None, evidence_nodes=(), focused=False):
    figure = go.Figure()
    if not graph:
        figure.add_annotation(text="No nodes match the selected filters", showarrow=False)
        figure.update_layout(height=420, paper_bgcolor="#FFFFFF")
        return figure
    # Symmetric layout forces keep incoming neighbors separated; edges remain directed.
    positions = nx.spring_layout(graph.to_undirected(as_view=True), seed=42, iterations=120)
    xs, ys = [], []
    for source, target in sorted(graph.edges):
        xs.extend([float(positions[source][0]), float(positions[target][0]), None])
        ys.extend([float(positions[source][1]), float(positions[target][1]), None])
    figure.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            hoverinfo="skip",
            line={"width": 1.2, "color": "#D4E2E5"},
            showlegend=False,
        )
    )
    for kind, color in COLORS.items():
        keys = sorted(key for key, attrs in graph.nodes(data=True) if attrs["type"] == kind)
        if not keys:
            continue
        labels = [graph.nodes[key].get("name", graph.nodes[key]["id"]) for key in keys]
        figure.add_trace(
            go.Scatter(
                x=[float(positions[key][0]) for key in keys],
                y=[float(positions[key][1]) for key in keys],
                mode="markers+text" if len(graph) <= 25 else "markers",
                name=kind,
                text=[escape(label[:24]) for label in labels],
                textposition="top center",
                textfont={"size": 12, "color": "#304C57"},
                hovertext=[
                    f"{escape(label)}<br>{escape(key)}<br>{kind}"
                    for key, label in zip(keys, labels)
                ],
                hoverinfo="text",
                customdata=keys,
                marker={
                    "color": color,
                    "size": [22 if key == selected else 15 for key in keys],
                    "line": {
                        "width": [
                            3 if key in evidence_nodes or key == selected else 1.5 for key in keys
                        ],
                        "color": [
                            "#173D43" if key in evidence_nodes or key == selected else "#FFFFFF"
                            for key in keys
                        ],
                    },
                },
            )
        )
    if focused and len(graph.edges) <= 25:
        for source, target in sorted(graph.edges):
            a, b = positions[source], positions[target]
            figure.add_annotation(
                x=float(a[0] * 0.2 + b[0] * 0.8),
                y=float(a[1] * 0.2 + b[1] * 0.8),
                ax=float(a[0]),
                ay=float(a[1]),
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor="#94A3B8",
            )
    figure.update_layout(
        height=480,
        margin={"l": 25, "r": 25, "t": 30, "b": 35},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        hovermode="closest",
        dragmode="pan",
        legend={"orientation": "h", "y": -0.05, "x": 0, "font": {"size": 12}},
        xaxis={"visible": False},
        yaxis={"visible": False},
        hoverlabel={"bgcolor": "#173D43", "font": {"color": "#FFFFFF", "size": 12}},
        font={"family": "Arial, sans-serif", "color": "#304C57"},
    )
    return figure


def relationship_rows(graph: nx.DiGraph, selected: str) -> list[dict]:
    return [
        {
            "direction": "Outgoing" if source == selected else "Incoming",
            "source": source,
            "relationship": attrs["type"],
            "target": target,
        }
        for source, target, attrs in sorted(
            [*graph.in_edges(selected, data=True), *graph.out_edges(selected, data=True)]
        )
    ]
