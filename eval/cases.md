# Eval cases

Test cases for the slicer (and later stages) discovered through real use, ahead of
the formal eval harness (phase 12). Each entry here is a candidate for that
harness's ground-truth suite once it exists — recorded now so the finding isn't
lost between now and then.

---

## Case 1: test file exclusion

**Discovered:** 2026-08-29, dogfooding `slice` against the RudhMap repo itself.

**Query:** `slice("BM25 seeding for the slicer")`

**Expected:** returns source code nodes only — `slice.py`'s BM25/slicer functions
(`slice_graph`, `_bm25_scores`, `_relevant_ranked`, `_expand`, `_apply_cap`,
`_detect_ambiguity`), `assemble.py`'s `assemble_graph`, and the immediately
relevant pipeline stages that call into them.

**Failure mode observed (before fix):** the 60-node cap was dominated by test
files. `assemble_graph` is called by ~20 different `test_*.py` functions across
the suite; expansion is bidirectional (callers and callees both traversed), so
seeding near a widely-shared utility pulled in every test file that happens to
call it, at low hop-cost, crowding out the budget with test scaffolding instead
of the actual mechanism asked about. Confirmed reproducible — not a fixture
artifact — same pattern also hit `"resolve_cross_file_calls"` and `"hop budget
expansion"` in the same run.

**Root cause:** the extraction pipeline treats every `.py`/`.ts` file
identically — there is no distinction anywhere between production code and test
code, so a repo's own tests ride along as ordinary graph nodes with ordinary
call edges into the code they test.

**Pass condition (post-fix):** zero `test_*.py` nodes in any `slice_graph()`
result, for this query and in general.

**Status:** FIXED, 2026-08-29. Chose extraction-time exclusion (Option 1):
`tests`, `test`, `__tests__`, `spec`, `specs` added to `COMMON_SKIP_DIRS`
(`src/rudhmap/extract/__init__.py`) — same shared-constant mechanism as the
`.venv`/`node_modules` skip fix, so it applies to every extractor across every
tier automatically, not just the slicer. Directory-name matching only,
deliberately not filename-pattern matching (`foo.test.ts` alongside source is
still scanned) — consistent with every other entry in that set.

**Verified after fix:**
- `scan` on this repo: 354 → 98 nodes (test suite fully excluded from
  extraction, not just hidden from one query).
- `slice("BM25 seeding for the slicer")`: 11 nodes, 0 dropped for cap, every
  node is in `slice.py` (the actual implementation) or its one real caller
  (`cli.py:slice_cmd`) — zero `test_*.py` nodes. Pass condition met exactly.
- The other two queries that hit the cap in the same dogfooding run
  (`"resolve_cross_file_calls"`, `"hop budget expansion"`) also verified
  clean: 18 nodes/0 dropped, and correctly "no match" respectively.
- Determinism reconfirmed (two runs, byte-identical diff).
- Full test suite (177 tests) unaffected — no existing test passes the repo
  root into an extractor; all use narrow `tests/fixtures/...` paths, which
  are unaffected since `iter_files()` only prunes subdirectories discovered
  *during* the walk, never the walk's own starting directory or its
  ancestors.

---

## Case 2: self-loops in the raw graph

**Discovered:** 2026-08-29, visually inspecting a rendered image of this repo's
own 98-node self-scan graph — two nodes showed an edge back to themselves.

**Investigated:** queried `assembly.graph` directly for self-loop edges
(`u == v` across `graph.edges(keys=True)`). Found **4 self-loop edges across 3
distinct nodes**:
- `tier2_ast/python.py:_flatten_callee` (1 self-loop)
- `tier2_ast/typescript.py:_flatten_callee` (1 self-loop)
- `tier0_iac/terraform.py:_iter_refs` (2 self-loops — it recurses from two
  different call sites, lines 85 and 88)

**Verdict: not a bug.** All three are genuinely, literally recursive functions
in this codebase's own source:
- `_flatten_callee` (both python.py:54 and typescript.py:68): `chain =
  _flatten_callee(obj, source) if obj is not None else []` — walks an
  attribute/member-expression chain recursively.
- `_iter_refs` (terraform.py:85, 88): `yield from _iter_refs(v)` — recurses
  into nested dict/list values while walking a parsed Terraform config.

**Conclusion:** the graph is behaving exactly as designed. Tier 2's call-edge
extraction cites the real `file:line` of the recursive call site; when that
call site's callee happens to resolve to the same function, the correct,
evidence-faithful output is a self-loop edge, not a suppressed or rewritten
one. Documented as an expected-behavior known limit, not fixed as a bug — see
[`README.md`](../README.md#known-limits).

---

## Case 3: 5-query graded eval, average 1.8/3 — hub dilution and BM25 length bias

**Discovered:** 2026-08-29, grading 5 slice queries against this repo
(`graph assembly`, `cache invalidation`, `tier2 AST extraction`, `CLI entry
point`, `schema validation`) on a 1-3 rubric. Average **1.8**, below the 2.5
bar set for moving to phase 8. Full grading detail is in that session's
transcript; summary below.

**Two failure modes found, neither a slicer-logic bug:**

1. **Hub dilution from structurally disconnected members** (`cache
   invalidation`, `schema validation` — grade 1 each). `ExtractionCache`'s
   methods have no edge connecting them to the class node, so a query
   matching "cache" (only via the `cache.py` basename — "invalidation" itself
   matches nothing, the cache has no such concept) splits into 3 falsely
   "distinct" candidates instead of one cohesive result. Separately,
   `EdgeRecord`/`EvidenceRecord` are constructed by nearly every extractor in
   the repo, so `schema validation` (an unbuilt phase-6 concept — "validation"
   matches nothing yet) sprawled to 52 of 60 nodes, essentially the whole
   pipeline, once test-exclusion (Case 1) stopped masking it with a different
   hub.
2. **BM25 document-length bias** (`CLI entry point` — grade 2, real seed
   choice was wrong). Seeded on `_AssemblyStats`, a sparse dataclass, instead
   of `cli.py:main`, the actual entry point — a short document's search text
   is proportionally more dominated by a shared token (`cli` via basename),
   so BM25 scores it relatively higher than a richer, more relevant document
   carrying the same match diluted among more tokens.

**Decision:** not fixed at the slicer level. Both failure modes are hub/graph
*shape* problems — exactly what phase 8 (abstraction) exists to solve by
grouping a hub's many callers into one labeled component, not something a
BM25/k-hop slicer can reasonably solve by itself without semantic
understanding. Proceeding to phase 6 (verifier) per the existing build order
rather than phase 8 directly. Revisit this case once phase 8 exists, to
confirm abstraction actually resolves it.

**`tier2 AST extraction` scored a clean 3** — correctly flagged ambiguous
between the two symmetric python/typescript extractors, exactly right.
`graph assembly` scored 2 — seed reasonable but diluted by sibling IaC-parser
calls in the same orchestrator function.

