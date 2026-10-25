# without get_context: how does the drawio renderer lay out nodes and edges

Layout is a pure-Python, simplified Sugiyama in `render/layout.py`. `render/drawio.py` turns the result into XML.

**Pipeline** (`layout_ir`, `layout.py:250`)
1. The renderer sorts nodes and edges, then computes each box width from its label (`drawio.py:76-87`). That makes the output independent of input order.
2. Self-loops are dropped and the graph is split into connected components (`layout.py:254-262`). Components with more than one node are laid out as layered graphs, and the largest comes first (`:263`). Single-node components go into a sqrt-column grid (`_layout_isolated`, `:233`).
3. Per component (`_layout_component`, `:171`):
   - **Cycle breaking:** DFS back edges are reversed, for layering only (`_acyclic_edges`, `:95`).
   - **Layering:** longest-path layers, with a heap-based Kahn traversal. Callers land above callees (`:121-141`).
   - **Long edges:** an edge spanning more than one layer gets dummy nodes, one per skipped layer (`:187-199`).
   - **Crossing reduction:** 8 alternating up/down barycenter sweeps (`_crossing_sweeps`, `:144`).
   - **Coordinates:** each layer is centered within the block width, and y is `layer * (NODE_HEIGHT + LAYER_GAP)` (`:210-218`).
4. Dummy nodes become edge waypoints. Reversed edges get their waypoints flipped back to their real direction (`:220-226`).
5. Blocks are shelf-packed left to right and wrap past `MAX_ROW_WIDTH` of 2400 (`:278-291`).

**Rendering** (`drawio.py`)
- Each node is an `<object>` whose geometry is the layout box, offset by `MARGIN` and `TITLE_HEIGHT` (`:163-174`).
- Parallel edges with the same src, dst and relation are merged into one arrow that lists all call sites (`:91-93`, `:176-178`).
- Each edge's waypoints come from `layout.waypoints` (`:202-204`).
- Non-call relations are dashed and labelled (`:184`, `:194`).

Every tie is broken by node id, so the output is deterministic.
