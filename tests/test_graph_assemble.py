from pathlib import Path

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.graph.assemble import assemble_graph

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def _node(identity: str, **kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=identity,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
    )


def _edge(src: str, dst: str, **kwargs) -> EdgeRecord:
    return EdgeRecord(
        src=src,
        dst=dst,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
    )


def test_every_node_becomes_a_graph_node_with_its_evidence():
    nodes = [_node("a"), _node("b")]
    result = assemble_graph(nodes, [])

    assert set(result.graph.nodes) == {"a", "b"}
    assert result.graph.nodes["a"]["evidence"] == [nodes[0]]
    assert result.graph.nodes["b"]["evidence"] == [nodes[1]]
    assert result.dropped_edges == []


def test_duplicate_identity_merges_evidence_instead_of_overwriting():
    first = _node("a", line=1)
    second = _node("a", line=2)
    result = assemble_graph([first, second], [])

    assert list(result.graph.nodes) == ["a"]
    assert result.graph.nodes["a"]["evidence"] == [first, second]


def test_edge_between_two_real_nodes_is_kept():
    nodes = [_node("a"), _node("b")]
    edge = _edge("a", "b")
    result = assemble_graph(nodes, [edge])

    assert result.graph.has_edge("a", "b")
    assert result.graph.get_edge_data("a", "b")[0]["evidence"] is edge
    assert result.dropped_edges == []


def test_edge_to_unextracted_identity_is_dropped_not_auto_created():
    nodes = [_node("a")]
    dangling = _edge("a", "boto3")
    result = assemble_graph(nodes, [dangling])

    assert set(result.graph.nodes) == {"a"}
    assert not result.graph.has_edge("a", "boto3")
    assert result.dropped_edges == [dangling]


def test_edge_with_unextracted_src_is_also_dropped():
    nodes = [_node("b")]
    dangling = _edge("unscanned_module", "b")
    result = assemble_graph(nodes, [dangling])

    assert result.dropped_edges == [dangling]


def test_real_tier2_extraction_never_leaves_a_dangling_edge_in_the_graph():
    """Integration check against the real tier2 python extractor: whatever
    it produces, every edge that survives into the graph must have both
    endpoints as real evidence-backed nodes, and every dropped edge must be
    missing at least one endpoint."""
    nodes, edges = parse_python_ast(FIXTURE)
    result = assemble_graph(nodes, edges)

    node_identities = set(result.graph.nodes)
    kept = [(u, v) for u, v, _ in result.graph.edges(keys=True)]

    for u, v in kept:
        assert u in node_identities
        assert v in node_identities

    for dropped in result.dropped_edges:
        assert dropped.src not in node_identities or dropped.dst not in node_identities

    assert len(kept) + len(result.dropped_edges) == len(edges)
