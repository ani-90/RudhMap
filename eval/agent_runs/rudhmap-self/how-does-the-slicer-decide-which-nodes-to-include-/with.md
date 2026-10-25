# with get_context: how does the slicer decide which nodes to include for a query

`slice_graph` (`src/rudhmap/graph/slice.py:261-297`) picks the nodes in four steps.

1. **Seeding.**
   - If the caller passes `seed_ids`, search is skipped. Those nodes become the seeds, and any that aren't in the graph are dropped (`slice.py:268-272`).
   - Otherwise `_build_corpus` (`slice.py:99-105`) builds a text blob per node, and `_relevant_ranked` (`slice.py:118-139`) ranks the nodes against the query. `CLAUDE.md` describes this as BM25 plus a token-overlap relevance filter.
   - If nothing is relevant, the result is empty (`slice.py:277-281`).

2. **Ambiguity check.** `_detect_ambiguity` (`slice.py:154-208`) runs before any expansion. If it finds several competing clusters, it returns candidates and no graph (`slice.py:283-285`). `CLAUDE.md` says it clusters the top matches by weakly-connected component and applies a score-ratio dominance check. Otherwise the single top-ranked node becomes the seed (`slice.py:287`).

3. **Expansion.** `_expand` (`slice.py:211-238`) walks outward from the seeds (`slice.py:288`). `CLAUDE.md` describes this as a weighted, bounded Dijkstra with a hop budget of 3. Infra/tier-0 nodes are admitted regardless of cost but don't pull in their own neighbours.

4. **Cap.** `_apply_cap` (`slice.py:241-258`) trims the visited set to `max_nodes` (default 60) and protects the seeds (`slice.py:289`). `CLAUDE.md` adds that infra nodes are also protected and that the drop order is deterministic. The kept nodes become an induced subgraph (`slice.py:291`).

I didn't read the bodies of `_relevant_ranked`, `_expand` or `_apply_cap`. The details in steps 1–4 that aren't tied to a `slice.py` line come from `CLAUDE.md`, not the code.

`build_view` (`src/rudhmap/pipeline.py:114-148`) calls this. If the query exactly matches a node id, it passes that node as the seed. With `merge_ambiguous=True`, it seeds on the top candidates together instead of stopping (`pipeline.py:132-137`).
