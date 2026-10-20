"""Deterministic layered layout for an IR graph. Pure Python, no Graphviz/ELK:
an external layout engine would add a binary or JS dependency and put
byte-identical output (spec invariant 4) at the mercy of its version.

A simplified Sugiyama pipeline, run per weakly-connected component:

  1. Cycle breaking -- DFS in sorted-id order; back edges are reversed for
     layering only (they're still drawn in their real direction).
     Self-loops are ignored for layering.
  2. Layering -- longest path from sources, so callers sit above callees.
  3. Dummy nodes -- an edge spanning k layers gets k-1 invisible dummies, so
     crossing reduction sees it and the renderer can route it through them.
  4. Ordering -- alternating down/up barycenter sweeps; ties keep the
     previous order, and the initial order is sorted ids.
  5. Coordinates -- fixed layer pitch; each layer centered in the component.

Components are then shelf-packed left-to-right into rows, largest first;
nodes with no edges at all are collected into one grid block at the end so
they don't stretch a single row across the page.

Every tie anywhere is broken by node id, so the same IR always yields the
same coordinates.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass, field

from rudhmap.ir.schema import IRGraph

NODE_HEIGHT = 48
MIN_NODE_WIDTH = 120
MAX_NODE_WIDTH = 320
CHAR_WIDTH = 7
NODE_PADDING = 24
DUMMY_WIDTH = 16
H_GAP = 40
LAYER_GAP = 80
COMPONENT_GAP = 120
MAX_ROW_WIDTH = 2400
SWEEPS = 8


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2


@dataclass
class Layout:
    boxes: dict[str, Box] = field(default_factory=dict)
    # (src, dst) -> waypoints through dummy nodes, for edges spanning >1 layer
    waypoints: dict[tuple[str, str], list[tuple[int, int]]] = field(default_factory=dict)
    width: int = 0
    height: int = 0


def node_width(label_lines: list[str]) -> int:
    longest = max((len(line) for line in label_lines), default=0)
    return max(MIN_NODE_WIDTH, min(MAX_NODE_WIDTH, longest * CHAR_WIDTH + NODE_PADDING))


def _components(nodes: list[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    seen: set[str] = set()
    components = []
    for start in nodes:
        if start in seen:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            node = stack.pop()
            members.append(node)
            for nxt in sorted(adjacency[node]):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(sorted(members))
    return components


def _acyclic_edges(members: list[str], succ: dict[str, set[str]]) -> set[tuple[str, str]]:
    """Return the component's edges with DFS back edges reversed."""
    state: dict[str, int] = {}  # 1 = on stack, 2 = done
    result: set[tuple[str, str]] = set()
    for root in members:
        if root in state:
            continue
        state[root] = 1
        stack = [(root, iter(sorted(succ[root])))]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
                continue
            if state.get(child) == 1:
                result.add((child, node))
            else:
                result.add((node, child))
                if child not in state:
                    state[child] = 1
                    stack.append((child, iter(sorted(succ[child]))))
    return result


def _longest_path_layers(members: list[str], dag: set[tuple[str, str]]) -> dict[str, int]:
    preds: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {m: 0 for m in members}
    succs: dict[str, list[str]] = defaultdict(list)
    for u, v in dag:
        preds[v].append(u)
        succs[u].append(v)
        in_degree[v] += 1

    layer: dict[str, int] = {}
    ready = [m for m in members if in_degree[m] == 0]
    heapq.heapify(ready)
    remaining = dict(in_degree)
    while ready:
        node = heapq.heappop(ready)
        layer[node] = max((layer[p] + 1 for p in preds[node]), default=0)
        for nxt in succs[node]:
            remaining[nxt] -= 1
            if remaining[nxt] == 0:
                heapq.heappush(ready, nxt)
    return layer


def _crossing_sweeps(
    layers: list[list[str]], up: dict[str, list[str]], down: dict[str, list[str]]
) -> list[list[str]]:
    for sweep in range(SWEEPS):
        downward = sweep % 2 == 0
        indices = range(1, len(layers)) if downward else range(len(layers) - 2, -1, -1)
        for i in indices:
            ref = layers[i - 1] if downward else layers[i + 1]
            ref_pos = {n: p for p, n in enumerate(ref)}
            neighbors = up if downward else down
            keyed = []
            for pos, node in enumerate(layers[i]):
                linked = [ref_pos[n] for n in neighbors[node] if n in ref_pos]
                bary = sum(linked) / len(linked) if linked else float(pos)
                keyed.append((bary, pos, node))
            layers[i] = [node for _, _, node in sorted(keyed)]
    return layers


@dataclass
class _Block:
    boxes: dict[str, Box]
    waypoints: dict[tuple[str, str], list[tuple[int, int]]]
    width: int
    height: int


def _layout_component(
    members: list[str],
    edges: set[tuple[str, str]],
    widths: dict[str, int],
) -> _Block:
    succ: dict[str, set[str]] = {m: set() for m in members}
    for u, v in edges:
        succ[u].add(v)

    dag = _acyclic_edges(members, succ)
    layer_of = _longest_path_layers(members, dag)

    up: dict[str, list[str]] = defaultdict(list)
    down: dict[str, list[str]] = defaultdict(list)
    chains: dict[tuple[str, str], list[str]] = {}
    node_layer = dict(layer_of)
    for u, v in sorted(dag):
        span = layer_of[v] - layer_of[u]
        chain = [u]
        for k in range(1, span):
            dummy = f"\0dummy:{u}->{v}:{k}"
            node_layer[dummy] = layer_of[u] + k
            chain.append(dummy)
        chain.append(v)
        for a, b in zip(chain, chain[1:]):
            down[a].append(b)
            up[b].append(a)
        if span > 1:
            chains[(u, v)] = chain[1:-1]

    depth = max(node_layer.values()) + 1
    layers: list[list[str]] = [[] for _ in range(depth)]
    for node in sorted(node_layer):
        layers[node_layer[node]].append(node)
    layers = _crossing_sweeps(layers, up, down)

    def width_of(n: str) -> int:
        return DUMMY_WIDTH if n.startswith("\0dummy:") else widths[n]

    row_widths = [sum(width_of(n) for n in row) + H_GAP * (len(row) - 1) for row in layers]
    block_width = max(row_widths)
    positions: dict[str, Box] = {}
    for depth_index, row in enumerate(layers):
        x = (block_width - row_widths[depth_index]) // 2
        y = depth_index * (NODE_HEIGHT + LAYER_GAP)
        for node in row:
            positions[node] = Box(x, y, width_of(node), NODE_HEIGHT)
            x += width_of(node) + H_GAP

    waypoints: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for (u, v), dummies in chains.items():
        points = [(positions[d].cx, positions[d].cy) for d in dummies]
        if (u, v) in edges:
            waypoints[(u, v)] = points
        else:  # reversed back edge: drawn v -> u in its real direction
            waypoints[(v, u)] = list(reversed(points))

    boxes = {n: b for n, b in positions.items() if not n.startswith("\0dummy:")}
    block_height = depth * NODE_HEIGHT + (depth - 1) * LAYER_GAP
    return _Block(boxes, waypoints, block_width, block_height)


def _layout_isolated(members: list[str], widths: dict[str, int]) -> _Block:
    columns = max(1, math.ceil(math.sqrt(len(members))))
    col_width = max(widths[m] for m in members)
    boxes = {}
    for i, node in enumerate(members):
        row, col = divmod(i, columns)
        boxes[node] = Box(col * (col_width + H_GAP), row * (NODE_HEIGHT + H_GAP), widths[node], NODE_HEIGHT)
    rows = math.ceil(len(members) / columns)
    used_cols = min(columns, len(members))
    return _Block(
        boxes,
        {},
        used_cols * col_width + (used_cols - 1) * H_GAP,
        rows * NODE_HEIGHT + (rows - 1) * H_GAP,
    )


def layout_ir(ir: IRGraph, widths: dict[str, int]) -> Layout:
    """Lay out `ir`. `widths` gives each node's box width (the renderer
    decides labels, so it decides widths)."""
    nodes = sorted(n.id for n in ir.nodes)
    edges = {(e.src, e.dst) for e in ir.edges if e.src != e.dst}
    adjacency: dict[str, set[str]] = {n: set() for n in nodes}
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)

    connected, isolated = [], []
    for members in _components(nodes, adjacency):
        (connected if len(members) > 1 else isolated).append(members)
    connected.sort(key=lambda m: (-len(m), m[0]))

    component_of = {n: i for i, m in enumerate(connected) for n in m}
    component_edges: list[set[tuple[str, str]]] = [set() for _ in connected]
    for u, v in edges:
        component_edges[component_of[u]].add((u, v))

    blocks = [_layout_component(m, component_edges[i], widths) for i, m in enumerate(connected)]
    if isolated:
        blocks.append(_layout_isolated(sorted(n for m in isolated for n in m), widths))

    layout = Layout()
    if not blocks:
        return layout

    row_limit = max(MAX_ROW_WIDTH, max(b.width for b in blocks))
    x = y = row_height = 0
    for block in blocks:
        if x > 0 and x + block.width > row_limit:
            x, y = 0, y + row_height + COMPONENT_GAP
            row_height = 0
        for node, box in block.boxes.items():
            layout.boxes[node] = Box(box.x + x, box.y + y, box.w, box.h)
        for key, points in block.waypoints.items():
            layout.waypoints[key] = [(px + x, py + y) for px, py in points]
        layout.width = max(layout.width, x + block.width)
        row_height = max(row_height, block.height)
        x += block.width + COMPONENT_GAP
    layout.height = y + row_height
    return layout
