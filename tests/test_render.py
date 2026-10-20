import random
import xml.etree.ElementTree as ET

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.ir.schema import IREdge, IRGraph, IRNode
from rudhmap.render.drawio import render_drawio
from rudhmap.render.layout import layout_ir


def _node(node_id: str, kind: str = "function", file: str = "app/mod.py", line: int = 1) -> IRNode:
    return IRNode(
        id=node_id,
        evidence=[EvidenceRecord(kind=kind, identity=node_id, file=file, line=line, tier=2, confidence=1.0)],
    )


def _edge(src: str, dst: str, line: int = 1, file: str = "app/mod.py", **attrs) -> IREdge:
    return IREdge(src=src, dst=dst, evidence=EdgeRecord(src=src, dst=dst, file=file, line=line, tier=2, confidence=1.0, attrs=attrs))


def _graph(node_ids, edge_pairs) -> IRGraph:
    return IRGraph(nodes=[_node(n) for n in node_ids], edges=[_edge(u, v) for u, v in edge_pairs])


def _widths(ir: IRGraph) -> dict[str, int]:
    return {n.id: 120 for n in ir.nodes}


def _overlaps(a, b) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


# --- layout ---------------------------------------------------------------


def test_callers_are_laid_out_above_callees():
    ir = _graph(["a", "b", "c"], [("a", "b"), ("b", "c")])

    boxes = layout_ir(ir, _widths(ir)).boxes

    assert boxes["a"].y < boxes["b"].y < boxes["c"].y


def test_cycles_and_self_loops_lay_out_without_error():
    ir = _graph(["a", "b", "c"], [("a", "b"), ("b", "a"), ("b", "c"), ("c", "c")])

    boxes = layout_ir(ir, _widths(ir)).boxes

    assert set(boxes) == {"a", "b", "c"}
    assert len({b.y for b in boxes.values()}) > 1


def test_no_two_boxes_overlap_on_a_messy_graph():
    rng = random.Random(7)
    ids = [f"n{i:02d}" for i in range(40)]
    pairs = {(rng.choice(ids), rng.choice(ids)) for _ in range(70)}
    ir = _graph(ids, sorted(pairs))

    boxes = list(layout_ir(ir, _widths(ir)).boxes.values())

    assert len(boxes) == 40
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not _overlaps(a, b)


def test_edge_spanning_layers_gets_waypoints():
    ir = _graph(["a", "b", "c"], [("a", "b"), ("b", "c"), ("a", "c")])

    layout = layout_ir(ir, _widths(ir))

    assert len(layout.waypoints[("a", "c")]) == 1
    assert ("a", "b") not in layout.waypoints


def test_isolated_nodes_go_in_a_grid_not_one_long_row():
    ir = _graph([f"solo{i:02d}" for i in range(16)], [])

    boxes = layout_ir(ir, _widths(ir)).boxes

    assert len({b.y for b in boxes.values()}) == 4
    assert len({b.x for b in boxes.values()}) == 4


def test_empty_graph_has_empty_layout():
    layout = layout_ir(IRGraph(), {})

    assert layout.boxes == {} and layout.width == 0 and layout.height == 0


# --- draw.io rendering ----------------------------------------------------


def test_output_is_byte_identical_regardless_of_input_order():
    rng = random.Random(3)
    ids = [f"app/m{i}.py:f{i}" for i in range(25)]
    pairs = sorted({(rng.choice(ids), rng.choice(ids)) for _ in range(40)})
    ir = _graph(ids, pairs)

    shuffled_nodes, shuffled_edges = list(ir.nodes), list(ir.edges)
    rng.shuffle(shuffled_nodes)
    rng.shuffle(shuffled_edges)
    shuffled = IRGraph(nodes=shuffled_nodes, edges=shuffled_edges)

    assert render_drawio(ir, title="t") == render_drawio(shuffled, title="t")
    assert render_drawio(ir, title="t") == render_drawio(ir, title="t")


def test_every_node_and_edge_appears_once_with_evidence():
    ir = _graph(["app/a.py:a", "app/b.py:b", "app/c.py:c"], [("app/a.py:a", "app/b.py:b"), ("app/b.py:b", "app/c.py:c")])

    root = ET.fromstring(render_drawio(ir, title="t"))
    objects = root.findall(".//object")
    nodes = [o for o in objects if o.find("mxCell").get("vertex") == "1"]
    edges = [o for o in objects if o.find("mxCell").get("edge") == "1"]

    assert sorted(o.get("rudhmap_id") for o in nodes) == ["app/a.py:a", "app/b.py:b", "app/c.py:c"]
    assert all(o.get("evidence") == "app/mod.py:1" for o in nodes)
    assert len(edges) == 2
    ids = {o.get("id") for o in objects}
    for e in edges:
        assert e.find("mxCell").get("source") in ids
        assert e.find("mxCell").get("target") in ids


def test_parallel_call_edges_merge_into_one_arrow_listing_every_site():
    ir = IRGraph(
        nodes=[_node("a"), _node("b")],
        edges=[_edge("a", "b", line=5), _edge("a", "b", line=9)],
    )

    root = ET.fromstring(render_drawio(ir, title="t"))
    edges = [o for o in root.findall(".//object") if o.find("mxCell").get("edge") == "1"]

    assert len(edges) == 1
    assert edges[0].get("evidence") == "app/mod.py:5; app/mod.py:9"
    assert "(2 sites)" in edges[0].get("tooltip")


def test_non_call_relations_are_labelled_and_imports_detected():
    ir = IRGraph(
        nodes=[_node("compose:api", kind="service"), _node("compose:db", kind="datastore"), _node("x"), _node("y")],
        edges=[_edge("compose:api", "compose:db", relation="depends_on"), _edge("x", "y", kind="import")],
    )

    root = ET.fromstring(render_drawio(ir, title="t"))
    labels = {o.get("relation"): o.get("label") for o in root.findall(".//object") if o.get("relation")}

    assert labels == {"depends_on": "depends_on", "imports": "imports"}


def test_paths_are_relativized_in_ids_labels_and_evidence():
    root_dir = "/abs/checkout/repo/"
    node_id = root_dir + "app/store.py:save_upload"
    ir = IRGraph(nodes=[_node(node_id, file=root_dir + "app/store.py", line=3)], edges=[])

    def rel(value: str) -> str:
        return value.removeprefix(root_dir)

    xml = render_drawio(ir, title="t", rel=rel)

    assert "/abs/checkout" not in xml
    obj = ET.fromstring(xml).find(".//object")
    assert obj.get("rudhmap_id") == "app/store.py:save_upload"
    assert obj.get("evidence") == "app/store.py:3"
    assert "<b>save_upload</b>" in obj.get("label")
    assert "store.py" in obj.get("label")


def test_special_characters_are_escaped_safely():
    ir = IRGraph(nodes=[_node('app/x.py:<lambda>&"q"')], edges=[])

    xml = render_drawio(ir, title='A & <B> "C"')
    root = ET.fromstring(xml)

    label = root.find(".//object").get("label")
    assert "&lt;lambda&gt;&amp;&quot;q&quot;" in label
    assert root.find("diagram").get("name") == 'A & <B> "C"'
