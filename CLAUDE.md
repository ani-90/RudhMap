# RudhMap — project instructions

MCP server that reads a repo and produces an evidence-cited (`file:line`-traceable) architecture graph. Full spec: see memory `project_rudhmap_spec.md`. 13-phase build order, phases 1-7 have zero LLM calls — don't add LLM code until phase 8.

## Current status (update this section whenever a phase completes or work resumes)

**Last updated:** 2026-10-25

**Context packs for LLMs (2026-10-25)** (244 tests passing) — a new direction alongside the diagram, not a phase of the original build order. See `eval/cases.md` Case 6:
- Goal: make RudhMap useful as a token-saving context source for coding agents, not only a diagram generator. The graph is the core asset; diagram and context pack are two renderers of it.
- `src/rudhmap/context.py` (`build_context_pack`), MCP tool `get_context(repo_path, query, token_budget=6000, max_nodes=60)`, CLI `rudhmap context <repo> "<q>" [--budget N]`. Pack = deduped call-graph lines + source bodies cut to exact line ranges (ranked seeds-first then hop distance, greedy fit to the budget, hard-checked after rendering) + `file:start-end` refs for what didn't fit. Classes show only their header when their methods have their own snippets. Tokens estimated as chars/4.
- `pipeline.build_view(..., merge_ambiguous=True)` seeds on the top 3 ambiguous candidates instead of stopping (context only; diagram/slice unchanged).
- Tier-2 nodes now carry `end_line`; extractors bumped to `python@3`/`typescript@3`. `end_line` is excluded from slicer BM25 text (`_UNINDEXED_ATTRS`).
- `eval/context_bench.py` + `eval/context_questions_knowledge_news_app.txt`: median whole-file/pack ratio 4.0× at budget 2000, 2.2× at 4000. That baseline (read every touched file whole) turned out to be far too generous — see next point.
- **Real agent test (`eval/agent_bench.py`, Case 7): no token saving.** Claude Code headless (Sonnet), 4 questions on `Knowledge-News-App`, with vs. without `get_context`: 131k vs 129k tokens, $0.27 vs $0.18, 8 vs 13 turns, answers equally correct. Repeated on RudhMap itself: 190k vs 172k tokens, $0.36 vs $0.25, 9 vs 15 turns (the extraction-cache question seeded on `graph_to_ir` and never included `cache.py`). README "Results so far" has the combined table. The baseline agent only reads 2-3 files, the repo's CLAUDE.md already maps it, and packs carry irrelevant code. **Do not claim token savings** until a test (large repo without CLAUDE.md, budget 2000, better seeding) shows one.

**Cross-file attribute-call resolution + two cache bugs fixed (2026-10-20)** (232 tests passing) — see `eval/cases.md` Case 5:
- Python `from app.db import crud; crud.create_user()` (and `import a.b as x; x.f()`, `import a.b; a.b.f()`, class attributes like `User.create()`) now resolves. Extractor records `resolved_dotted_path` (built from what the local name is bound to — new `bound` field in the import table); `resolve._resolve_dotted_attribute_path` tries every (module file, qualname) split and connects only if exactly one names both a scanned file and an existing node. TS namespace imports (`import * as crud`) and attribute calls on named imports resolve the same way via `resolved_name`. Default imports stay unresolved. `Knowledge-News-App`: 47 → 81 edges, all verified; 7 cited lines spot-checked correct.
- Cache bug 1: key was (extractor, content hash) only, so two files with identical bytes shared an entry and the second file's nodes vanished. Key now includes the file path.
- Cache bug 2: no extractor version in the key, so changing extractor output kept serving stale cache. Names are now `python@2`, `typescript@2`, `tier1@1` — **bump the version whenever an extractor's output changes.** Cache file renamed `extraction_cache.v2.json` (old `extraction_cache.json` files are orphaned, safe to delete).
- Python module suffix matching now requires a path boundary (`writer` no longer matches `rewriter.py`) and accepts `pkg/__init__.py`.

**Phase 7 complete (2026-10-20): layout + draw.io renderer:**
- `src/rudhmap/render/layout.py`: pure-Python simplified Sugiyama (no Graphviz/ELK — an external engine would put byte-identical output at the mercy of its version). DFS cycle breaking (back edges reversed for layering only), longest-path layering (callers above callees, heap-based Kahn), dummy nodes for long edges (become draw.io waypoints), 8 alternating barycenter sweeps, per-layer centering; components shelf-packed into rows (max 2400px), edge-less nodes in a sqrt grid. Every tie broken by node id.
- `src/rudhmap/render/drawio.py`: uncompressed `.drawio`; each node/edge is an `<object>` with `evidence`, `kind`/`relation`, `rudhmap_id`, and a hover tooltip (groundwork for phase 9 `trace_edge`). Parallel same-relation edges merge into one arrow listing all call sites. The renderer sorts its own input, so output is byte-identical regardless of caller order (tested with shuffled input). Colors by kind; non-call relations dashed + labelled.
- `src/rudhmap/diagram.py` (build → slice → verify → render → write) shared by CLI `rudhmap diagram <repo> [-q Q] [-o out.drawio]` and MCP tool `generate_diagram`. Default output `rudhmap.drawio` / `rudhmap-<slug>.drawio` in the repo root; refuses non-`.drawio` output paths; writes nothing when the query is ambiguous/no-match.
- `pipeline.build_view` is now the single build/slice/verify path for CLI `slice`/`diagram` and all MCP tools. `paths.Relativizer` is shared.
- Ambiguity is now actionable: an exact repo-relative node id as the query slices on that node directly (`slice_graph(..., seed_ids=...)`). Before this, ambiguous results were a dead end.
- Real-repo check (`eval/cases.md` Case 4): `Knowledge-News-App` diagram is readable; RudhMap's own graph is a hub tangle — expected, phase 8's job. Also surfaced the cross-file resolution gap fixed above (Case 5).

**Minimal MCP server built early (2026-10-20), ahead of phase 7 — a first slice of phase 10, not phase 10 itself:**
- `src/rudhmap/server.py`: stdio MCP server on the official `mcp` SDK **2.x** (`from mcp.server.mcpserver import MCPServer` — `FastMCP` was renamed in 2.x; `mcp.server.fastmcp` no longer exists). Two read-only tools, `scan(repo_path)` and `slice(repo_path, query, max_nodes=60)`, returning JSON of the *verified* IR (post-`verify_ir`) with evidence per node/edge. Pipeline runs in a worker thread (`anyio.to_thread`) so the event loop isn't blocked. Bad input raises `ToolError` (returned as `is_error`, not a crash).
- All ids/paths in tool output are made relative to the repo root with forward slashes, so output is identical across checkout locations/OSes (tested). Tier 2 edges have no `relation` attr — the server labels them `imports` (`attrs.kind == "import"`) or `calls`.
- Nothing may print to stdout in this process (stdio *is* the protocol stream) — `build_assembly(verbose=False)` only.
- `src/rudhmap/pipeline.py`: `build_assembly`/`AssemblyStats` moved out of `cli.py` unchanged so CLI and server share one pipeline.
- Entry points in `pyproject.toml`: `rudhmap` (CLI) and `rudhmap-mcp` (server). Deps added: `mcp>=2.3,<3`, `anyio>=4.9`.
- Verified over a real stdio subprocess against `Knowledge-News-App`: 102 nodes/47 edges (matches CLI), 0 dropped by verifier, ~1s warm. Slice queries there mostly come back `ambiguous`/`no_match` — that's the known Case 3 slicer weakness, deferred to phase 8, not a server bug.
- Still missing for real phase 10: `trace_edge` (phase 9), sampling for zero-API-key installs. (`generate_diagram` landed with phase 7.)
- Setup gotcha: after the archilens→rudhmap rename the venv still had only the old package installed, so every test failed to import `rudhmap`. Fix: `pip install -e ".[dev]"`.

Phases 0-6 complete and merged to `main`:
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
  - Perf: every extractor used `Path.rglob(...)` then filtered skip-dirs *after* enumeration, so it still fully walked `.venv` (40K files) before discarding results. Fixed with a shared `iter_files()` helper (`src/rudhmap/extract/__init__.py`) using `os.walk()` with in-place `dirnames` pruning. Benchmarked 2026-10-20 (commit `206aa04^` vs `206aa04`, same machine, ~43K-file repo with 40,387 files in `.venv`, identical 102-node/47-edge output): cold scan 76.0s → 3.4s (~22×), warm-cache scan 41.1s/40.4s → 3.25s/3.29s (~12×). An earlier claim of "3+ min, had to be killed" / "~2.4s" was an unfinished run and an unreproduced figure — don't cite those.
  - Slicer ambiguity: a clearly dominant match got flagged ambiguous by weak unrelated matches — restored a score-ratio dominance check (guarded for the degenerate small-corpus case).
  - Slicer relevance leak: the BM25 search text included each node's full absolute file path, so a repo checked out under e.g. `.../Knowledge-News-App/...` made every single node spuriously match any query containing "news" — non-deterministic across checkout locations too. Fixed by indexing only the file's basename + qualname, never parent directories. Found by querying the slicer with plain-English questions a human who'd never read the repo would actually ask, not just code-shaped queries.
  - Test-file exclusion (found dogfooding the slicer against this repo itself, see `eval/cases.md`): a widely-shared utility called from ~20 test functions made slice queries near it hit the 60-node cap dominated by test scaffolding instead of the real production-code neighborhood. Added `tests`/`test`/`__tests__`/`spec`/`specs` to `COMMON_SKIP_DIRS` (directory-name matching only, same mechanism as the venv fix) — test suites are never extracted at all now, in `scan` or `slice`. This repo's own self-scan went from 354 to 98 nodes.
  - Self-loops in the raw graph (`_flatten_callee` x2, `_iter_refs`): investigated, confirmed genuinely recursive source, not a bug — documented in `README.md`'s new "Known limits" section and `eval/cases.md` Case 2.

**Phase 5 slicer graded, 5 queries, average 1.8/3** (below the 2.5 bar for proceeding straight to phase 8) — see `eval/cases.md` Case 3. Two failure modes, both hub/graph-shape problems rather than slicer-logic bugs: (1) hub dilution — `ExtractionCache`'s methods disconnected from its class node, `EdgeRecord`/`EvidenceRecord` constructed almost everywhere; (2) BM25 document-length bias favoring a sparse dataclass over the real entry point (`main`). **Decision: not fixed at the slicer level** — phase 8 (abstraction/grouping) is the right place to solve this, not more BM25/k-hop tuning. Proceeding to phase 6 next per the existing build order (not phase 8 directly). Revisit Case 3 once phase 8 exists.

**Next up:** Phase 8 — abstraction LLM pass (grouping per-function boxes into named components).

Not started: abstraction LLM pass, the rest of the MCP surface (`trace_edge`, sampling), tier 3 LLM extraction, eval harness.

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
