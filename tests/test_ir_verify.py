from pathlib import Path

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.ir.schema import IREdge, IRGraph, IRNode
from rudhmap.ir.verify import verify_ir

FIXTURE = Path(__file__).parent / "fixtures" / "ir_verify"
SAMPLE = FIXTURE / "sample.py"
SAMPLE_LINE_COUNT = 10


def _evidence(**kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=kwargs.pop("identity", "a"),
        file=kwargs.pop("file", str(SAMPLE)),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        subtype=kwargs.pop("subtype", None),
        attrs=kwargs.pop("attrs", {}),
    )


def _edge_evidence(src="a", dst="b", **kwargs) -> EdgeRecord:
    return EdgeRecord(
        src=src,
        dst=dst,
        file=kwargs.pop("file", str(SAMPLE)),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        attrs=kwargs.pop("attrs", {}),
    )


def test_verify_passes_clean_ir_with_real_file_and_line():
    node = IRNode(id="a", evidence=[_evidence(identity="a", line=1)])
    ir = IRGraph(nodes=[node], edges=[])

    result = verify_ir(ir, FIXTURE)

    assert result.dropped_nodes == []
    assert [n.id for n in result.ir.nodes] == ["a"]


def test_verify_drops_node_with_nonexistent_file():
    node = IRNode(id="a", evidence=[_evidence(file=str(FIXTURE / "missing.py"))])
    ir = IRGraph(nodes=[node], edges=[])

    result = verify_ir(ir, FIXTURE)

    assert result.ir.nodes == []
    assert len(result.dropped_nodes) == 1
    dropped_node, reason = result.dropped_nodes[0]
    assert dropped_node.id == "a"
    assert "file not found" in reason


def test_verify_drops_node_with_out_of_range_line():
    node = IRNode(id="a", evidence=[_evidence(line=SAMPLE_LINE_COUNT + 5)])
    ir = IRGraph(nodes=[node], edges=[])

    result = verify_ir(ir, FIXTURE)

    assert result.ir.nodes == []
    assert "out of range" in result.dropped_nodes[0][1]


def test_verify_keeps_node_with_partial_evidence_when_one_entry_resolves():
    good = _evidence(identity="a", tier=1, line=1)
    bad = _evidence(identity="a", tier=2, line=999)
    node = IRNode(id="a", evidence=[good, bad])
    ir = IRGraph(nodes=[node], edges=[])

    result = verify_ir(ir, FIXTURE)

    assert len(result.ir.nodes) == 1
    assert result.ir.nodes[0].evidence == [good]
    assert result.dropped_nodes == []


def test_verify_drops_edge_whose_evidence_is_unresolvable():
    node_a = IRNode(id="a", evidence=[_evidence(identity="a")])
    node_b = IRNode(id="b", evidence=[_evidence(identity="b")])
    edge = IREdge(src="a", dst="b", evidence=_edge_evidence(line=999))
    ir = IRGraph(nodes=[node_a, node_b], edges=[edge])

    result = verify_ir(ir, FIXTURE)

    assert result.ir.edges == []
    assert {n.id for n in result.ir.nodes} == {"a", "b"}
    assert "out of range" in result.dropped_edges[0][1]


def test_verify_drops_edge_referencing_missing_node_defensively():
    node_a = IRNode(id="a", evidence=[_evidence(identity="a")])
    edge = IREdge(src="a", dst="ghost", evidence=_edge_evidence(src="a", dst="ghost"))
    ir = IRGraph(nodes=[node_a], edges=[edge])

    result = verify_ir(ir, FIXTURE)

    assert result.ir.edges == []
    assert "dangling" in result.dropped_edges[0][1]


def test_verify_self_loop_with_valid_evidence_survives():
    node_a = IRNode(id="a", evidence=[_evidence(identity="a")])
    edge = IREdge(src="a", dst="a", evidence=_edge_evidence(src="a", dst="a"))
    ir = IRGraph(nodes=[node_a], edges=[edge])

    result = verify_ir(ir, FIXTURE)

    assert len(result.ir.edges) == 1
    assert result.ir.edges[0].src == result.ir.edges[0].dst == "a"
    assert result.dropped_edges == []


def test_verify_rejects_bad_confidence_and_tier():
    bad_confidence = IRNode(id="a", evidence=[_evidence(identity="a", confidence=1.5)])
    bad_tier = IRNode(id="b", evidence=[_evidence(identity="b", tier=9)])
    ir = IRGraph(nodes=[bad_confidence, bad_tier], edges=[])

    result = verify_ir(ir, FIXTURE)

    assert result.ir.nodes == []
    assert len(result.dropped_nodes) == 2
    reasons = [reason for _, reason in result.dropped_nodes]
    assert any("confidence" in r for r in reasons)
    assert any("tier" in r for r in reasons)
