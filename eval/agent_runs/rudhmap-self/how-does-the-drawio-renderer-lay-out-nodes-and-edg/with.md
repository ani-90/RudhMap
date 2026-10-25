# with get_context: how does the drawio renderer lay out nodes and edges

Layout is a pure-Python, simplified Sugiyama layered layout in `render/layout.py`. `render_drawio` sizes each box from its label, then calls `layout_ir` (`drawio.py:75-89`).

**Per-component pipeline** (`_layout_component`, `layout.py:171-230`):
1. **Components:** `layout_ir` splits the graph into weakly-connected components, ignoring self-loops (`layout.py:250-270`). Components with more than one node are laid out as layered blocks. Single-node components are collected separately.
2. **Cycle breaking:** a DFS reverses back edges, but only for layering (`_acyclic_edges`, `layout.py:95-118`).
3. **Layering:** longest-path layering with a heap-based Kahn traversal puts callers above callees (`_longest_path_layers`, `layout.py:121-141`).
4. **Long edges:** an edge spanning more than one layer gets dummy nodes (`layout.py:187-199`). Their centers become draw.io waypoints. A reversed back edge gets its waypoints reversed back (`layout.py:218-224`).
5. **Crossing reduction:** `SWEEPS` alternating down/up barycenter sweeps reorder each layer (`_crossing_sweeps`, `layout.py:144-160`).
6. **Coordinates:** y is `layer × (NODE_HEIGHT + LAYER_GAP)`. Each row is centered within the block width (`layout.py:208-216`).

**Placing components** (`layout.py:261-292`):
- Components are sorted largest first.
- Edge-less nodes go into a roughly square grid (`_layout_isolated`, `layout.py:233-247`).
- The blocks are shelf-packed into rows, wrapping at `MAX_ROW_WIDTH`, with `COMPONENT_GAP` between them.

**Edges in the output:** parallel edges with the same source, destination and relation are merged into one arrow (`drawio.py:~92-94`). The layout waypoints are attached to those arrows. I didn't see the edge-emission code, which sits in `drawio.py:155-209` past where the context cut off.

Determinism comes from sorting the input and breaking every tie by node id.
