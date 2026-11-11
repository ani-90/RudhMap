# Step B: The tools

**Branch:** `stepB-tools` · **Date:** 2026-11-12 · **Verdict: PASS**

## 1. Goal

RudhMap controls exactly two things in a model's context window: **the results its tools return**
and **its tool definitions**, which are re-sent on every model call. Everything else is fixed or not
ours: Claude Code's system prompt, the built-in tools, CLAUDE.md, the question, and the model's own
output.

Step B builds four tools whose results are:
- **complete enough** that the model needs no follow-up call;
- **compact enough** not to bloat the context;

and whose definitions are small and clear. Step C will measure the effect with real Claude runs;
step B is measured without an LLM.

Pass criteria, written and committed before the work (`docs/plan.md`, commit `ef45cb4`):

| Check | Target | Result |
|---|---|---|
| Unit tests incl. exact-output fixtures + existing suite | all green | **278 passed** |
| Step 1 engine eval | unchanged (>= 99.3% / 100%) | **99.3% / 100%**, 0 extra edges |
| Output size within budget, every cut stated | 100% of a 200+ call sweep | **1,161 / 1,161** |
| `find_symbol` top-3 accuracy (30 hand-labelled queries) | >= 90% | **29/30 (97%)** |
| Coverage: the facts' symbols appear within <= 2 planned calls | >= 12 of 15 | **12/15** |
| MCP tool definitions, tokens added per model call | <= 800 | **649** (measured in Claude Code) |
| Determinism: same call twice, and from a fresh index | identical | **1,161 / 1,161 identical**, both ways |
| Latency on rich (144 files): cold / warm / after editing a file | <= 5 s / 300 ms / 1.5 s | **2.1 s / 42 ms / 1.16 s** |

## 2. Changes

### The tools (`src/rudhmap/tools/`)

These are MCP tools (the default `rudhmap-mcp` surface) and CLI commands (`rudhmap find|show|trace|map`)
with identical output.

| Tool | Returns | Budget |
|---|---|---|
| `find_symbol(query)` | One line per match: kind, `file:line`, signature, route, doc. For an identifier that names no function/class (e.g. `SECRET_KEY`), the lines where it appears, each with its enclosing function | 400 tokens |
| `show(symbol, detail)` | Header with `file:start-end`, signature, decorators, HTTP route, parent class, doc, overrides / overridden-by; numbered source (`full`); **calls**: each callee with its signature, doc and location, tiny (<= 3-line) bodies inline, plus what it calls in turn when it is a callback, a module value builder, a thin wrapper (<= 12 lines) or a private same-file helper; **called by**; unresolved calls. Files: an outline with signatures. Ambiguous names return candidate ids | 2,000 tokens |
| `trace(symbol, to, direction)` | Shortest call paths (up to 3) between two symbols, or the call tree below / callers above a symbol. Each hop shows its call line and the target's location. Classes passed as values are left out; indirection hops don't use up depth | 800 tokens |
| `repo_map(path)` | Folders and files with their most-connected functions/classes and HTTP routes (router prefixes applied), shrunk level by level to fit the budget | 1,500 tokens |

The index (`RepoIndex`):
- keeps one in-memory graph per repo;
- checks for changed source files (size + mtime) at most every 0.5 s, and rebuilds if any changed;
- warms up in the background when the MCP server starts.

The old `scan`/`slice`/`get_context`/`generate_diagram` tools moved to `rudhmap-mcp --legacy`.

### Engine changes required by the tools

| Change | Why it was needed | Version |
|---|---|---|
| Signature, first docstring line and decorators on every Python def/class | `show`/`find_symbol` show one-line summaries | python@6 |
| `x = build()` at module level + `x.method()` in a function → a `built_by` link to `build` | `refresh_feed → … → run_pipeline` stopped at `pipeline.ainvoke()` (`pipeline = _build_graph()`), so trace couldn't reach the agents/aggregator | python@7 |
| Relative imports (`from ._models import Request`) resolve; `from . import x` bound to `.x`, not `..x` | Libraries (httpx, rich) use them almost everywhere and were nearly unconnected | python@8 |
| Return annotations type assignments: `x = f()` / `x = self.f()` with `-> Foo` | `transport = self._transport_for_url(url)` then `transport.handle_request()`, so `BaseTransport.handle_request` showed "no callers" | python@8 |
| TS: arrow-function / function-expression consts are definitions | `const AddItem = () => {…}`: most of the React frontend was invisible | typescript@5 |
| TS: JSX `<Component />` is a connection; `fn.bind()` counts as a use of `fn` | Component trees and handlers | typescript@5 |
| TS: tsconfig path aliases (`@/x`), default imports/exports and barrel re-exports (`export * from`) resolve | Nearly every frontend import uses one of these | typescript@5 |
| Extraction cache moved out of the repo (`%LOCALAPPDATA%\rudhmap\cache`, `~/.cache/rudhmap`, or `RUDHMAP_CACHE_DIR`); stale entries pruned | A `.rudhmap_cache/` in the repo is clutter, and it was visible to benchmark agents' Grep/Glob | cache v3 |

Effect on the template repo: **681 frontend connections**. Before this step the frontend had almost
none, because aliases and default imports never resolved.

## 3. Evaluation suite

```
python eval/tools_eval.py --label <name>       # writes eval/results/tools/<name>.json
python eval/engine_eval.py --label <name>      # step 1 regression check
pytest
```

- **Inputs:**
  - **Repos:** the benchmark's clean git exports of the 3 tuning repos, plus `rich` for size and
    latency. None of `rich`'s held-out questions are used.
  - **Hand-written data** (`eval/ground_truth/step_b_tools.yaml`, committed `dba5d27` before the first
    run): 30 `find_symbol` queries with accepted answers, and a coverage plan. The plan lists, for each
    tuning question, the 1-2 calls a model would make first and the strings the answer key needs.
- **Size sweep:** for each repo, a deterministic sample of 50 symbols. Each sample symbol gets
  `show` full and outline, `trace` down and up, and `find_symbol` on its name; on top of that come
  pairwise `trace`, 10 file outlines and 6 `repo_map` calls. 1,161 calls in all.
- **Overhead:** measured in Claude Code itself with a trivial `claude -p` run: 6,431 prompt tokens per
  call without RudhMap, 7,080 with it.
- **Unit tests** (`tests/test_tools.py`, `tests/test_ts_frontend.py`, updated resolver and cache tests),
  including negative cases:
  - HTML tags are not components;
  - bare packages stay unresolved;
  - a missing relative module stays dropped;
  - ambiguous names return candidates.

  A mutation check confirmed the depth rule for indirection hops is covered by a test.

## 4. Results

Raw: `eval/results/tools/stepB-v1.json` → `stepB-v2.json` → `stepB-v3.json` (final).

| | v1 | v2 | v3 (final) |
|---|---|---|---|
| Calls over budget | 3 (trace 803-818 / 800) | 2 (find 477, 401 / 400) | **0** |
| `find_symbol` top-3 | 29/30 | 29/30 | **29/30** |
| Coverage | 10/15 | 12/15 | **12/15** |
| Determinism | identical | identical | identical |
| rich cold / warm / edit | 2.46 s / 51 ms / 1.01 s | 2.86 s / 62 ms / 0.93 s | **2.1 s / 42 ms / 1.16 s** |

Max output per tool (v3; budget in brackets):

| Repo | find_symbol (400) | show (2,000) | trace (800) | repo_map (1,500) |
|---|---|---|---|---|
| Knowledge-News-App | 365 | 750 | 401 | 582 |
| fastapi-template | 396 | 1,135 | 781 | 1,332 |
| httpx | 385 | 1,890 | 434 | 882 |
| rich | 400 | 1,986 | 786 | 1,418 |

The median outputs are small: `show` 72-160 tokens, `trace` 26-43 tokens. Most symbols are small,
and the budgets only matter for big ones.

Coverage per question (v3): what the planned calls return, against what a model reading files
would otherwise need.

| Q | Planned calls | Output tokens | Covered |
|---|---|---|---|
| kna-1 | show + trace `refresh_feed` | 1,061 | ✅ incl. run_all_agents_node, aggregator_node |
| kna-2 | show `BaseAgent.run` + show `aggregator_node` | 2,079 | ✅ incl. `embed` → `return []` inline |
| kna-3 | find `scheduler` + show `start_scheduler` | 308 | ✅ "called by: nothing in this repo" |
| kna-4 | show `search_similar` + show `aggregator_node` | 1,577 | ✅ |
| kna-5 | show quiz routes | 1,348 | ✅ |
| tpl-1 | show `login_access_token` + `authenticate` | 817 | ✅ |
| tpl-2 | show `get_user_by_email` | 291 | ✅ all 8 callers in one call |
| tpl-3 | show `DeleteItem` + `delete_item` | 1,390 | ✅ frontend component and backend route |
| tpl-4 | show `isLoggedIn` + `handleApiError` | 288 | ❌ `get_current_user` (backend) |
| tpl-5 | show `Settings` + `_enforce_non_default_secrets` | 361 | ❌ SECRET_KEY usage sites |
| httpx-1 | show `_send_handling_redirects` + `_build_redirect_request` | 1,379 | ✅ |
| httpx-2 | show `BaseTransport.handle_request` | 491 | ✅ 3 implementations + the call site in one call |
| httpx-3 | show `build_request` + `HTTPTransport.handle_request` | 1,488 | ✅ |
| httpx-4 | show `DigestAuth.auth_flow` + `_send_handling_auth` | 1,300 | ✅ |
| httpx-5 | show `Response.text` + `Response.encoding` | 658 | ❌ `_get_content_decoder` |

## 5. RCA

**1. Most of the React frontend was invisible to the graph (found while building, not by a metric).**
- **Root cause:** components and hooks are `const X = () => {…}`, which the TS extractor didn't treat as
  definitions. Imports also go through `@/` path aliases (treated as external packages), default imports
  (never resolved) and barrel files (`@/client` → `export * from "./sdk.gen"`, not followed). So almost
  every frontend link was dropped.
- **Fix:** all four handled, tested with must-not cases.
- **Limit:** aliases come from the nearest `tsconfig.json` (`prefix/*` patterns only). A tsconfig change
  doesn't invalidate cached extraction for unchanged files.

**2. `trace refresh_feed` couldn't reach the pipeline (kna-1 coverage miss in v1).**
- **Symptom:** the path stopped at `run_pipeline`.
- **Root cause, in two parts:**
  - `pipeline.ainvoke()` calls a method on a module-level value (`pipeline = _build_graph()`), and nothing
    linked the two. Fixed with the `built_by` link, which the engine eval doesn't score since it has no
    answer key for that kind.
  - With that fixed, the agents/aggregator sat at depth 4, behind two indirection hops (background task
    passed as a value, module value). Fixed: indirection hops don't consume trace depth.

**3. Libraries were barely connected (found on httpx).** Relative imports were skipped by design ("not
handled here"), and `from . import x` recorded the wrong path (`..x`). Both are fixed; the old test that
asserted "left unresolved" was replaced by a positive test and a negative one.

**4. "No callers" for an interface method (httpx).** `BaseTransport.handle_request` is called on a value
returned by a method annotated `-> BaseTransport`, and return annotations weren't used for types. Fixed
for `x = f()` and `x = self.f()`, at most 3 functions deep. `show` now also lists overrides, which gives
httpx-2 its facts in a single call.

**5. kna-2 coverage miss in v1: `generate_queries`.** It sits in `BaseAgent._fetch_all`, a 35-line private
helper. Callees of callees were listed only for helpers of 12 lines or fewer. **Fix:** private (`_name`)
same-file helpers always get their calls listed, since they are part of the shown function's logic.

**6. Budget overruns in v1 and v2.**
- `trace`'s "+N more branches cut" footer wasn't counted in the budget, so it ran 3-18 tokens over.
- The new usage list in `find_symbol` wasn't trimmed, so it reached 477 tokens.

Both fixed: space is reserved for the footer, and usage lines are trimmed with a stated "+N more".

**7. The one `find_symbol` miss: "authenticate user password".**
- **Symptom:** `crud.authenticate` ranks 4th, behind `update_password_me` and friends. Those match two
  query words, while `authenticate` matches one.
- **Fix attempted:** a boost for a single-word name that equals a query word moved it from unranked to
  4th, still outside the top 3.
- **Status:** left as is rather than tuned further against the eval set.

**8. Remaining coverage misses: 3 of 15, all reported and none tuned around.**
- **tpl-4:** frontend → backend needs cross-layer links (API call → route), which are cut from v1, as
  expected since step A.
- **tpl-5:** "where is SECRET_KEY used" is about an attribute, not a function. The *planned* calls
  (`show Settings`) can't reach it. `find_symbol SECRET_KEY` does answer it in one call (all 6 usage sites
  with their enclosing functions), but that call was added after v1, so tpl-5 still counts as a miss
  rather than changing the plan.
- **httpx-5:** decompression happens in `iter_bytes`/`read`, reached from `.text` only through the
  `content` property. Property access isn't a call in the graph.

**9. Tool-definition overhead was 1,134 tokens per model call at first (target 800).**
- **Measured:** in Claude Code, not estimated. The JSON estimate was 827, so estimating would have hidden
  this.
- **Fix:**
  - shorter descriptions and instructions;
  - no `repo` parameter (the server uses its working directory, or `RUDHMAP_REPO`);
  - no `kind`/`depth` parameters;
  - plain `str` defaults instead of Optional, which produces a smaller schema.

  Now 649 tokens.

**10. RudhMap's cache was polluting the benchmark repos.** The smoke run and the overhead probe started
the server inside the KNA benchmark export, which wrote `.rudhmap_cache/` there. In step C both arms
would have seen it in Grep/Glob.
- **Step A:** unaffected; its runs happened earlier.
- **Fix:** the cache moved out of the repo, and the stray caches in the exports were deleted. The caches
  I had created in the cloned httpx and template repos were removed. Knowledge-News-App's own October
  `.rudhmap_cache/` and `.archilens_cache/` were left alone; they are unused now and safe to delete.

## 6. Observation for step C (not a step B criterion)

A single smoke run (kna-1, Haiku, with RudhMap) confirmed the tools work over stdio: the first move was
`show refresh_feed`.
- **But in that same first call** it also ran Grep and Read out of habit, and later re-read `feed.py`.
  The run took 3 model calls and 26.5k tokens, vs 2 calls and ~17.7k for plain Haiku.
- **What this means:** the tools only save calls if the model trusts them. Step C has to look at
  descriptions, instructions and whether the model stops after a sufficient `show`.

The run was a functional check and isn't counted anywhere.

## 7. Limits of this evaluation

- **Coverage is a proxy:** "the strings are in the output", not "the model answers correctly". The
  planned calls are my guess at what a model does first. Step C measures the real thing.
- **The answer keys and the coverage plan were both written by me,** the tools' author. The plan was
  committed before the first run and not changed afterwards.
- **Several fixes were made after seeing v1 results.** These were the depth rule, helper expansion,
  usage search and the find boost. Each is a general rule, not a per-question patch, but the held-out
  set in step C is the real check against overfitting.
- **Budgets use chars/4.** Real tokenizers differ by about ±20%.

## 8. Decision

All step B criteria are met. **Step B passes.**

Into step C:
- **Runs:** re-run the plain baseline (Haiku, Sonnet) alongside the RudhMap arm with the same harness,
  which now records model calls.
- **Watch:** whether the model trusts a `show` result or still greps.
- **Expected losses:** tpl-4 (cross-layer), and probably httpx-5.
- **Held-out set:** stays untouched until the final step C run.
