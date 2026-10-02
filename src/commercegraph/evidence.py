"""Application-owned records and real graph edges used to support each result."""

from typing import Any, Literal

import networkx as nx

from commercegraph.dataset import StrictModel
from commercegraph.models import ResolvedPlan


class EvidenceEdge(StrictModel):
    source: str
    relationship: str
    target: str


class EvidenceRecord(StrictModel):
    record_id: str
    kind: str
    fields: dict[str, Any]
    node_ids: list[str]
    edges: list[EvidenceEdge]


class EvidenceBundle(StrictModel):
    query: ResolvedPlan
    status: Literal["ok", "no_data"]
    records: list[EvidenceRecord]
    aggregates: dict[str, int]
    nodes: dict[str, dict[str, Any]]
    edges: list[EvidenceEdge]
    currency: str


class EvidenceBuilder:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.records = []

    def add(self, kind: str, fields: dict, nodes=(), pairs=()):
        node_ids = set(nodes)
        edges = []
        for source, target in sorted(set(pairs)):
            if not self.graph.has_edge(source, target):
                raise ValueError("Evidence contains a nonexistent edge")
            edges.append(
                EvidenceEdge(
                    source=source,
                    target=target,
                    relationship=self.graph.edges[source, target]["type"],
                )
            )
            node_ids.update([source, target])
        if not node_ids <= set(self.graph.nodes):
            raise ValueError("Evidence contains a nonexistent node")
        self.records.append(
            EvidenceRecord(
                record_id=f"R{len(self.records) + 1:03}",
                kind=kind,
                fields=fields,
                node_ids=sorted(node_ids),
                edges=edges,
            )
        )

    def bundle(self, query: ResolvedPlan, **aggregates: int) -> EvidenceBundle:
        node_ids = sorted({node for record in self.records for node in record.node_ids})
        edges = {
            (edge.source, edge.target): edge for record in self.records for edge in record.edges
        }
        status = "ok" if self.records or query.output_mode == "count" else "no_data"
        return EvidenceBundle(
            query=query,
            status=status,
            records=self.records,
            aggregates={"matching_count": len(self.records), **aggregates},
            nodes={key: dict(self.graph.nodes[key]) for key in node_ids},
            edges=[edges[key] for key in sorted(edges)],
            currency=self.graph.graph["currency"],
        )
