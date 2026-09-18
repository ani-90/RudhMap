# RudhMap — project instructions

MCP server that reads a repo and produces an evidence-cited (`file:line`-traceable) architecture graph. Full spec: see memory `project_rudhmap_spec.md`. 13-phase build order, phases 1-7 have zero LLM calls — don't add LLM code until phase 8.

## Current status (update this section whenever a phase completes or work resumes)

**Last updated:** 2026-09-05

Phases 0-6 complete and merged to `main` (189 tests passing):
- Phase 6: IR schema + verifier (`src/rudhmap/ir/`) — `schema.py` (`IRNode`/`IREdge`/`IRGraph`, a thin NetworkX-free wrapper reusing `EvidenceRecord`/`EdgeRecord` unchanged), `convert.py` (`graph_to_ir`, deterministic sort of an assembled/sliced `nx.MultiDiGraph` into the flat IR), `verify.py` (`verify_ir` — schema shape checks, referential integrity of edges against surviving node ids, and mechanical evidence resolution: does the cited file exist on disk and does the line fall within its real line count; unresolvable evidence is dropped and counted, mirroring `assemble_graph`'s existing dangling-edge pattern). Self-loops explicitly pass (genuine recursion, see "Known limits"). No pydantic/jsonschema added — plain dataclasses, consistent with the rest of the repo. Files are re-read from disk per verification run, not cached, since verification must reflect current on-disk state. Wired into `scan`/`slice` CLI output as a "verified IR" summary line rather than a new subcommand (nothing to decouple it from yet). Self-scan of this repo: 108 nodes/140 edges, 0 dropped by the verifier. Note: `EvidenceRecord`/`EdgeRecord` only carry a `file`/`line` *claim* — the verifier proves a citation is *possible* (file exists, line in range), not that its content matches the claim; an in-range but imprecise line number (e.g. off by one) is not caught by this check and would need an extractor-level content-matching test instead.

Phases 0-5 complete and merged to `main`:
- Phase 0: scaffold
- Phase 1: Tier 0 IaC extractors (Terraform, docker-compose, Dockerfile, k8s)
- Phase 2: Tier 1 YAML regex rule engine
- Phase 3: Tier 2 tree-sitter AST extractors (Python, TypeScript)
- Phase 4: graph assembly (NetworkX) + identity resolution + SHA-256 extraction cache
- Phase 5: slicer (`src/rudhmap/graph/slice.py`) — BM25 seed (token-overlap relevance + BM25 ranking, robust to rank_bm25's degenerate zero/negative IDF on small corpora) + weighted bounded-Dijkstra k-hop expand (`MAX_HOP_BUDGET=3`, infra/tier-0 nodes admitted regardless of cost but don't teleport their neighbors) + 60-node cap (seeds/infra protected, deterministic drop order) + ambiguity detection via weakly-connected-components clustering of top BM25 matches, with a score-ratio dominance check (only when scores are meaningfully positive) so a clear winner isn't falsely flagged ambiguous by weak unrelated matches. New `slice` CLI subcommand. Added `rank-bm25` dependency.
- Also fixed, all found by testing against a real external repo (`Knowledge-News-App`, a Flutter + FastAPI app), not just fixtures:
  - Missing `src/rudhmap/__main__.py` so `python -m rudhmap ...` (the exact form README documents) actually works.
  - Perf: every extractor used `Path.rglob(...)` then filtered skip-dirs *after* enumeration, so it still fully walked `.venv` (40K files) before discarding results — 3+ min scan, had to be killed. Fixed with a shared `iter_files()` helper (`src/rudhmap/extract/__init__.py`) using `os.walk()` with in-place `dirnames` pruning. Same repo now scans in ~2.4s.
  - Slicer ambiguity: a clearly dominant match got flagged ambiguous by weak unrelated matches — restored a score-ratio dominance check (guarded for the degenerate small-corpus case).
  - Slicer relevance leak: the BM25 search text included each node's full absolute file path, so a repo checked out under e.g. `.../Knowledge-News-App/...` made every single node spuriously match any query containing "news" — non-deterministic across checkout locations too. Fixed by indexing only the file's basename + qualname, never parent directories. Found by querying the slicer with plain-English questions a human who'd never read the repo would actually ask, not just code-shaped queries.
  - Test-file exclusion (found dogfooding the slicer against this repo itself, see `eval/cases.md`): a widely-shared utility called from ~20 test functions made slice queries near it hit the 60-node cap dominated by test scaffolding instead of the real production-code neighborhood. Added `tests`/`test`/`__tests__`/`spec`/`specs` to `COMMON_SKIP_DIRS` (directory-name matching only, same mechanism as the venv fix) — test suites are never extracted at all now, in `scan` or `slice`. This repo's own self-scan went from 354 to 98 nodes.
  - Self-loops in the raw graph (`_flatten_callee` x2, `_iter_refs`): investigated, confirmed genuinely recursive source, not a bug — documented in `README.md`'s new "Known limits" section and `eval/cases.md` Case 2.

**Phase 5 slicer graded, 5 queries, average 1.8/3** (below the 2.5 bar for proceeding straight to phase 8) — see `eval/cases.md` Case 3. Two failure modes, both hub/graph-shape problems rather than slicer-logic bugs: (1) hub dilution — `ExtractionCache`'s methods disconnected from its class node, `EdgeRecord`/`EvidenceRecord` constructed almost everywhere; (2) BM25 document-length bias favoring a sparse dataclass over the real entry point (`main`). **Decision: not fixed at the slicer level** — phase 8 (abstraction/grouping) is the right place to solve this, not more BM25/k-hop tuning. Proceeding to phase 6 next per the existing build order (not phase 8 directly). Revisit Case 3 once phase 8 exists.

**Next up:** Phase 7 — layout + draw.io renderer.

Not started: layout/draw.io rendering, abstraction LLM pass, MCP server surface, tier 3 LLM extraction, eval harness.

## V1 public release target: through Phase 10

Decided 2026-08-28. Phase 10 (full MCP surface) is the release bar, not earlier:
- Phases 0-6 only produce graphs/slices — no usable output, no MCP server. Not a product.
- Phase 7 (layout + draw.io renderer) gives a real output file, but it's raw structural nodes — unreadable as an architecture diagram.
- Phase 8 (abstraction LLM pass) is the first point where output looks like an actual architecture diagram (grouped/named components, not one box per function).
- Phase 9 (`trace_edge`) makes the evidence-cited claim actually checkable by a user — click an arrow, see why it's there.
- Phase 10 (full MCP surface: `scan`, `generate_diagram`, `trace_edge`, sampling for zero-API-key installs) is the actual product boundary — before this it's a CLI script, after this it's an installable MCP server.

**Explicitly deferred to v1.1+:**
- Phase 11 (tier 3 LLM extraction) — v1 ships with tier0-2 coverage (Python/TS/IaC); other languages just extract less, not blocking.
- Phase 12 (eval harness) — needed before making public hallucination-rate claims in marketing, but not a runtime dependency; do this right after v1 ships.
- Phase 13 (CI gating, `diff_against_commit`, freeform mode) — genuine v2 features.

So: **4 more phases after the current one (7→8→9→10)** stand between here and a public v1.

## Working agreement

- At the start of a session, read this status section and just proceed — don't ask the user where the project stands.
- After any commit that finishes or advances a phase, update the "Current status" section above (and the date) in the same turn.
- Also update the published "RudhMap, explained" interview-FAQ artifact whenever a phase completes: https://claude.ai/code/artifact/85d1a127-451e-4688-ab14-f9f8f5c0946b — update the pipeline strip, status pills, footer phase count, and add/revise Q&A sections covering the newly completed work.
