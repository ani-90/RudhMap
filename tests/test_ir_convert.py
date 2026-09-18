from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.graph.assemble import assemble_graph
from rudhmap.graph.slice import SliceResult, slice_graph
from rudhmap.ir.convert import graph_to_ir


def _node(identity: str, **kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=identity,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        subtype=kwargs.pop("subtype", None),
        attrs=kwargs.pop("attrs", {}),
    )


def _edge(src: str, dst: str, **kwargs) -> EdgeRecord:
    return EdgeRecord(
        src=src,
        dst=dst,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        attrs=kwargs.pop("attrs", {}),
    )


def test_graph_to_ir_sorts_nodes_and_edges_deterministically():
    nodes = [_node("z"), _node("a"), _node("m")]
    edges = [_edge("z", "a", line=5), _edge("a", "m", line=1)]
    result = assemble_graph(nodes, edges)

    ir = graph_to_ir(result.graph)

    assert [n.id for n in ir.nodes] == ["a", "m", "z"]
    assert [(e.src, e.dst) for e in ir.edges] == [("a", "m"), ("z", "a")]


def test_graph_to_ir_preserves_all_evidence_no_loss():
    first = _node("a", tier=1, line=1)
    second = _node("a", tier=2, line=9)
    result = assemble_graph([first, second], [])

    ir = graph_to_ir(result.graph)

    assert len(ir.nodes) == 1
    assert ir.nodes[0].evidence == [first, second]


def test_graph_to_ir_accepts_slice_result_graph():
    nodes = [_node("a"), _node("b")]
    edges = [_edge("a", "b")]
    assembly = assemble_graph(nodes, edges)

    slice_result: SliceResult = slice_graph(assembly, "a", max_nodes=60)
    assert slice_result.graph is not None

    ir = graph_to_ir(slice_result.graph)
    assert {n.id for n in ir.nodes} == {"a", "b"}
