# without get_context: how does the slicer decide which nodes to include for a query

The slicer (`src/rudhmap/graph/slice.py`) works in four steps, all in `slice_graph` (`slice.py:261`).

1. **Seed selection.** If the caller passes `seed_ids`, those nodes are the seeds and search is skipped (`slice.py:272-275`). Otherwise it builds a BM25 corpus from each node's text (`slice.py:277`) and ranks the nodes against the query (`slice.py:278`).
   - The index text uses the file's basename and qualname, not parent directories (`_node_text_blob`, `slice.py:66`).
   - `end_line` is excluded from the text (`slice.py:46`).
   - If nothing is relevant, it returns an empty result (`slice.py:280-281`).

2. **Ambiguity check.** `_detect_ambiguity` (`slice.py:154`) looks at the top 10 matches (`_AMBIGUITY_TOP_N`, `slice.py:40`). It clusters them by weakly connected component and applies a score-ratio dominance check (`_AMBIGUITY_SCORE_RATIO = 0.5`, `slice.py:41`). If the match is ambiguous, it returns candidates and no graph (`slice.py:283-285`). Otherwise the single top match becomes the seed (`slice.py:287`).

3. **Expansion.** `_expand` (`slice.py:211`) is a bounded Dijkstra walk from the seeds. It follows edges in both directions (`slice.py:222-225`) and accumulates edge weights from `_edge_weight` (`slice.py:146`). A non-infra neighbor is dropped if its cost exceeds `MAX_HOP_BUDGET = 3.0` (`slice.py:230`). Infra nodes are admitted regardless, with their cost clamped to the budget (`slice.py:232-233`).

4. **Cap.** If more than `max_nodes` (default 60) were reached, `_apply_cap` (`slice.py:241`) sorts by seeds first, then infra, then lowest cost, then node id as a deterministic tiebreak (`slice.py:247-255`). It keeps the first `max_nodes` and records the rest as `dropped_for_cap`. The result is the induced subgraph of the kept nodes (`slice.py:291`).
