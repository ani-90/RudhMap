"""Graph assembly: turn the flat EvidenceRecord/EdgeRecord lists produced by
tiers 0-2 into a single NetworkX graph. This step performs no identity
resolution -- every EvidenceRecord's `identity` string becomes its own graph
node exactly as extracted. Merging same-component nodes across tiers is a
separate, later step (identity resolution) so that assembly stays a pure,
lossless restructuring: every node produced by extraction appears in the
graph, and nothing is added that extraction didn't already produce (spec
invariant 5).

An edge whose src or dst has no corresponding extracted node (e.g. a tier 2
import edge pointing at a third-party package that was never scanned) is
dropped rather than auto-vivifying a placeholder node -- NetworkX's
add_edge() would otherwise silently create an evidence-less node for it,
which violates invariant 3 (every node must carry resolvable evidence).
Dropped edges are counted and returned so a large count can still surface as
a signal (e.g. an infra reference to a resource that should have been
scanned but wasn't), rather than disappearing silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord


@dataclass
class AssemblyResult:
    graph: nx.MultiDiGraph
    dropped_edges: list[EdgeRecord] = field(default_factory=list)


def assemble_graph(
    nodes: list[EvidenceRecord], edges: list[EdgeRecord]
) -> AssemblyResult:
    graph = nx.MultiDiGraph()

    for node in nodes:
        if graph.has_node(node.identity):
            graph.nodes[node.identity]["evidence"].append(node)
        else:
            graph.add_node(node.identity, evidence=[node])

    dropped_edges: list[EdgeRecord] = []
    for edge in edges:
        if not graph.has_node(edge.src) or not graph.has_node(edge.dst):
            dropped_edges.append(edge)
            continue
        graph.add_edge(edge.src, edge.dst, evidence=edge)

    return AssemblyResult(graph=graph, dropped_edges=dropped_edges)
