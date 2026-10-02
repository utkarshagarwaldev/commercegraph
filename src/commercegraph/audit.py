"""Count logical graph values, not duplicated IDs in serialized edge endpoints."""

import re

import networkx as nx

WORD = re.compile(r"\bbanana\b", re.IGNORECASE)


def count_occurrences(value) -> int:
    if isinstance(value, str):
        return len(WORD.findall(value))
    if isinstance(value, dict):
        return sum(count_occurrences(k) + count_occurrences(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return sum(count_occurrences(item) for item in value)
    return 0


def audit_graph(graph: nx.DiGraph) -> dict:
    marker_count = sum(
        attrs.get("type") == "Marker" and attrs.get("value") == "banana"
        for _, attrs in graph.nodes(data=True)
    )
    total = count_occurrences(graph.graph)
    total += sum(
        count_occurrences(key) + count_occurrences(attrs) for key, attrs in graph.nodes(data=True)
    )
    total += sum(count_occurrences(attrs) for _, _, attrs in graph.edges(data=True))
    return {
        "marker_nodes": marker_count,
        "occurrences": total,
        "passed": marker_count == 5 and total == 5,
    }


def require_audit(graph: nx.DiGraph) -> dict:
    report = audit_graph(graph)
    if not report["passed"]:
        raise ValueError(f"Marker integrity check failed: {report}")
    return report
