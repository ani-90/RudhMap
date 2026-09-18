"""Reshape an assembled/sliced NetworkX graph into the flat IR. Pure
restructuring only -- no filtering, no dropping, nothing added (spec
invariant 5); dropping unresolvable evidence is the verifier's job, not
this step's.

Node and edge order is fixed by sorting rather than left at NetworkX's
iteration order, so that the same graph always reshapes into the same IR
regardless of insertion order (spec invariant 4: same commit -> byte-
identical diagram).
"""
from __future__ import annotations

import networkx as nx

from rudhmap.ir.schema import IREdge, IRGraph, IRNode


def graph_to_ir(graph: nx.MultiDiGraph) -> IRGraph:
    nodes = [
        IRNode(id=node_id, evidence=graph.nodes[node_id]["evidence"])
        for node_id in sorted(graph.nodes)
    ]

    edges_data = graph.edges(keys=True, data=True)
    sorted_edges = sorted(
        edges_data,
        key=lambda e: (e[0], e[1], e[3]["evidence"].file, e[3]["evidence"].line or -1),
    )
    edges = [
        IREdge(src=u, dst=v, evidence=data["evidence"]) for u, v, _key, data in sorted_edges
    ]

    return IRGraph(nodes=nodes, edges=edges)
