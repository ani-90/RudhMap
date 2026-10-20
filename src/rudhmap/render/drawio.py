"""Render a verified IR as an uncompressed draw.io (mxGraph) file.

Every node and edge is an `<object>` carrying its evidence as attributes
(`evidence`, `kind`, `relation`, ...) plus a hover tooltip, so the
`file:line` behind any box or arrow is visible inside draw.io itself -- the
groundwork for phase 9's `trace_edge`.

Output is byte-deterministic: the renderer sorts nodes and edges itself
(rather than trusting its caller's order), cell ids follow that sorted
order, coordinates come from the deterministic layout, and there's no
timestamp, `modified`, or random diagram id anywhere in the file.

Parallel IR edges with the same (src, dst, relation) -- e.g. a function
calling the same helper on three lines -- become one arrow whose evidence
lists every call site, rather than three overlapping arrows.
"""
from __future__ import annotations

import html
import posixpath
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Callable

from rudhmap.extract.schema import EdgeRecord
from rudhmap.ir.schema import IRGraph, IRNode
from rudhmap.render.layout import layout_ir, node_width

MARGIN = 40
TITLE_HEIGHT = 50

_BASE_NODE_STYLE = "rounded=1;whiteSpace=wrap;html=1;fontSize=12;arcSize=12;"
_KIND_STYLES = {
    "function": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "method": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "class": "fillColor=#e1d5e7;strokeColor=#9673a6;",
    "service": "fillColor=#d5e8d4;strokeColor=#82b366;",
    "job": "fillColor=#d5e8d4;strokeColor=#82b366;dashed=1;",
    "datastore": "fillColor=#ffe6cc;strokeColor=#d79b00;",
    "queue": "fillColor=#fff2cc;strokeColor=#d6b656;",
    "gateway": "fillColor=#f8cecc;strokeColor=#b85450;",
    "route": "fillColor=#f8cecc;strokeColor=#b85450;dashed=1;",
    "config": "fillColor=#f5f5f5;strokeColor=#999999;dashed=1;",
}
_DEFAULT_KIND_STYLE = "fillColor=#f5f5f5;strokeColor=#666666;"
_EDGE_STYLE = "endArrow=block;endFill=1;html=1;rounded=1;strokeColor=#555555;fontSize=10;"
_NON_CALL_EDGE_STYLE = _EDGE_STYLE + "dashed=1;"


def edge_relation(edge: EdgeRecord) -> str:
    """Tier 0 and resolver edges name their relation explicitly; tier 2 edges
    don't, and are either imports (`kind: "import"`) or calls."""
    if "relation" in edge.attrs:
        return edge.attrs["relation"]
    return "imports" if edge.attrs.get("kind") == "import" else "calls"


def _cite(file: str, line: int | None, rel: Callable[[str], str]) -> str:
    return f"{rel(file)}:{line}" if line is not None else rel(file)


def _node_label_parts(node_id: str, kind: str) -> tuple[str, str]:
    """`app/store.py:save_upload` -> ("save_upload", "store.py");
    `compose:api` -> ("api", "compose"); no colon -> (id, kind)."""
    if ":" in node_id:
        head, name = node_id.rsplit(":", 1)
        return name, posixpath.basename(head)
    return node_id, kind


def _kind(node: IRNode) -> str:
    return node.evidence[0].kind if node.evidence else "unknown"


def render_drawio(ir: IRGraph, *, title: str, rel: Callable[[str], str] = lambda s: s) -> str:
    ir = IRGraph(
        nodes=sorted(ir.nodes, key=lambda n: n.id),
        edges=sorted(
            ir.edges, key=lambda e: (e.src, e.dst, e.evidence.file, e.evidence.line or -1, edge_relation(e.evidence))
        ),
    )
    labels: dict[str, tuple[str, str]] = {}
    widths: dict[str, int] = {}
    for node in ir.nodes:
        name, subtitle = _node_label_parts(rel(node.id), _kind(node))
        labels[node.id] = (name, subtitle)
        widths[node.id] = node_width([name, subtitle])

    layout = layout_ir(ir, widths)

    merged: dict[tuple[str, str, str], list[EdgeRecord]] = defaultdict(list)
    for edge in ir.edges:
        merged[(edge.src, edge.dst, edge_relation(edge.evidence))].append(edge.evidence)

    mxfile = ET.Element("mxfile", {"host": "rudhmap", "type": "device"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": "rudhmap", "name": title})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "0", "dy": "0", "grid": "1", "gridSize": "10", "guides": "1",
            "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "0",
            "pageScale": "1",
            "pageWidth": str(layout.width + 2 * MARGIN),
            "pageHeight": str(layout.height + 2 * MARGIN + TITLE_HEIGHT),
            "math": "0", "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    heading = (
        f"<b>{html.escape(title)}</b><br><font style=\"font-size:11px\">"
        f"{len(ir.nodes)} components, {len(merged)} connections &middot; "
        f"every box and arrow cites the file:line it was extracted from (hover to see)</font>"
    )
    title_cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": "title",
            "value": heading,
            "style": "text;html=1;align=left;verticalAlign=top;fontSize=16;",
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(
        title_cell,
        "mxGeometry",
        {"x": str(MARGIN), "y": "10", "width": str(max(600, layout.width)), "height": "40", "as": "geometry"},
    )

    cell_ids: dict[str, str] = {}
    for index, node in enumerate(ir.nodes):
        cell_id = f"n{index}"
        cell_ids[node.id] = cell_id
        kind = _kind(node)
        name, subtitle = labels[node.id]
        citations = [_cite(e.file, e.line, rel) for e in node.evidence]
        tooltip_lines = [rel(node.id), f"kind: {kind}"] + [
            f"{_cite(e.file, e.line, rel)} (tier {e.tier}, confidence {e.confidence})"
            for e in node.evidence
        ]
        obj = ET.SubElement(
            root,
            "object",
            {
                "id": cell_id,
                "label": f"<b>{html.escape(name)}</b><br><font style=\"font-size:10px\">{html.escape(subtitle)}</font>",
                "rudhmap_id": rel(node.id),
                "kind": kind,
                "evidence": "; ".join(citations),
                "tooltip": "\n".join(tooltip_lines),
            },
        )
        cell = ET.SubElement(
            obj,
            "mxCell",
            {"style": _BASE_NODE_STYLE + _KIND_STYLES.get(kind, _DEFAULT_KIND_STYLE), "vertex": "1", "parent": "1"},
        )
        box = layout.boxes[node.id]
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(box.x + MARGIN),
                "y": str(box.y + MARGIN + TITLE_HEIGHT),
                "width": str(box.w),
                "height": str(box.h),
                "as": "geometry",
            },
        )

    for index, ((src, dst, relation), records) in enumerate(merged.items()):
        citations = sorted({_cite(r.file, r.line, rel) for r in records})
        sites = f" ({len(citations)} sites)" if len(citations) > 1 else ""
        obj = ET.SubElement(
            root,
            "object",
            {
                "id": f"e{index}",
                "label": "" if relation == "calls" else relation,
                "relation": relation,
                "evidence": "; ".join(citations),
                "tooltip": "\n".join([f"{relation}{sites}"] + citations),
            },
        )
        cell = ET.SubElement(
            obj,
            "mxCell",
            {
                "style": _EDGE_STYLE if relation == "calls" else _NON_CALL_EDGE_STYLE,
                "edge": "1",
                "parent": "1",
                "source": cell_ids[src],
                "target": cell_ids[dst],
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        points = layout.waypoints.get((src, dst))
        if points:
            array = ET.SubElement(geometry, "Array", {"as": "points"})
            for px, py in points:
                ET.SubElement(array, "mxPoint", {"x": str(px + MARGIN), "y": str(py + MARGIN + TITLE_HEIGHT)})

    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode") + "\n"
