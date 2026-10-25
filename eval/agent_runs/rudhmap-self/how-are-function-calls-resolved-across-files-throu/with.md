# with get_context: how are function calls resolved across files through imports

Cross-file resolution is a second pass over call edges that couldn't be linked when the graph was first assembled.

1. **Dropped edges.** `assemble_graph` drops any edge whose source or destination node doesn't exist (`src/rudhmap/graph/assemble.py:46-48`). An import-based call is dropped here because the extractor only knows the name, not the target node's id.

2. **Ordering.** `build_assembly` runs `resolve_same_scope_calls`, then `resolve_cross_file_calls` (`src/rudhmap/pipeline.py:76-80`), then build-context containment.

3. **Re-linking.** `resolve_cross_file_calls` (`src/rudhmap/graph/resolve.py:190-207`) walks `dropped_edges`. For each one it computes a candidate id with `_cross_file_candidate_identity`. It adds the edge only if both the candidate and the source node exist. Otherwise the edge stays dropped.

4. **Candidate identity** (`resolve.py:164-187`). Only tier-2 edges are considered.
   - **Python, attribute or dotted calls.** If the edge has `resolved_dotted_path`, `_resolve_dotted_attribute_path` (`resolve.py:144-161`) tries every split into (module, qualname). It accepts a split only if the module suffix matches exactly one scanned file and that file has a node with that qualname. It resolves only when exactly one split qualifies, so ambiguous and external paths stay dropped.
   - **Python, plain imports.** `resolved_module` and `resolved_name` go through `_resolve_dotted_module_suffix` (`resolve.py:137-141`), which requires a unique suffix match. Leading-dot relative imports return `None`.
   - **TypeScript.** Only relative specifiers are resolved. They are joined to the importing file's directory and tried with each TS extension and `index` files (`resolve.py:113-125`). Bare specifiers are treated as external packages and skipped.

5. **Result.** The id is `"{target_file}:{name}"`, and the original edge's evidence is kept (`resolve.py:187, 201`).

I didn't read how the extractors fill `resolved_dotted_path`. That comes from `CLAUDE.md`'s notes.
