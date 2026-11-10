# Step 1: Engine correctness

**Branch:** `step1-engine-fixes` · **Date:** 2026-11-10 · **Verdict: PASS**

## 1. Goal

Every tool in later steps answers from the code graph, so the graph has to be
complete and clean first. Pass criteria, written before the work (`docs/plan.md`):

| Criterion | Target |
|---|---|
| Recall on hand-labelled ground truth, excluding `hard` cases | ≥ 95% |
| Precision on ground truth | ≥ 98% |
| Nodes picked up from tool folders (`.claude/` worktrees) | 0 |
| Two builds of the same tree | identical |
| Test suite | all green |

## 2. Changes

| Area | Change | Files |
|---|---|---|
| File discovery | File list comes from `git ls-files` (tracked + untracked-not-ignored) when the target is a git work tree, so `.gitignore` is respected and nested worktrees/repos are never listed; `os.walk` fallback otherwise. `.claude` added to the shared skip list. One git call per build, shared by all extractors. | `extract/__init__.py`, `pipeline.py` |
| Module nodes | Each non-empty Python/TS file gets a `module` node, so top-level code (`settings = Settings()`) has a caller. | `tier2_ast/python.py`, `tier2_ast/typescript.py` |
| Scoping | Bare names resolve innermost scope first, through enclosing functions, then the module. Class bodies are skipped (Python/JS semantics). `self.x()` uses the innermost enclosing class. | `graph/resolve.py` |
| Stated types (Python) | The extractor records the type of a name when the file states it: `x = Foo()`, `x: Foo` / `Optional[Foo]` / `Foo \| None` parameters and annotations, `self.x = Foo()` (stored on the class). A new resolver pass connects `x.m()`, `self.x.m()`, inherited `self.m()` by looking the method up on the class, then its bases. | `tier2_ast/python.py`, `graph/resolve.py` (`resolve_typed_calls`) |
| Inheritance (Python) | `class A(B)` emits an `inherits` edge, resolved like any other name. | same |
| References (Python) | A definition passed as a value is a `references` edge: callbacks (`add_task(_run_bg)`), `Depends(get_db)` in parameter defaults (attributed to the function), `db.query(User)`, keyword args, decorator arguments (`response_model=X`, attributed to the decorated function). Names bound locally (params, assignments, loop targets) are skipped; unresolved references are discarded, not counted as dropped. | `tier2_ast/python.py`, `pipeline.py` |
| Dockerfile | The Dockerfile extractor existed and was tested but was never called by the pipeline. Wired in. | `pipeline.py` |
| Speed | Resolver indexes scanned files by name instead of scanning every file per lookup. | `graph/resolve.py` |
| Context pack | Token budget is now a hard limit on dense slices (see RCA 8). | `context.py` |
| Cache | Extractor versions bumped: `python@5`, `typescript@4`. | |

## 3. Evaluation suite

```
python eval/engine_eval.py --label <name>      # writes eval/results/engine/<name>.json
pytest
```

- **Ground truth:** `eval/ground_truth/knowledge_news_app_calls.yaml`. Every connection between
  Knowledge-News-App's own definitions at commit `20d352e`, labelled by reading all 1,749 lines of
  Python by hand, not derived from RudhMap output. 145 call sites in four kinds (call, reference,
  param_reference, inherits); one site is marked `hard` (the target depends on a runtime dict value).
  Scored at call-site level: each cited line counts. The repo is exported fresh from git for every
  run, so local junk files and caches can't affect results.
- **Unresolved-call audit:** calls the engine dropped whose last name matches a definition in the
  repo, bucketed by cause. Runs on the test repo and on RudhMap's own `src/`, which has no ground truth.
- **Discovery:** scan RudhMap's repo root, which contains a stale Claude Code worktree under
  `.claude/worktrees/`, and count nodes from tool folders.
- **Determinism:** cold and warm builds must give identical edge/node fingerprints.
- **Speed:** cold (no cache) and warm builds of the test repo.
- **Unit tests:** 15 new tests (`tests/test_engine_resolution.py`, `tests/test_context_budget.py`),
  including negative cases (edges that must *not* be drawn). Mutation checks: disabling the
  local-binding guard and the class-body scoping rule each made exactly one new test fail.

## 4. Results

Raw output: `eval/results/engine/before.json`, `after-v1.json` (intermediate, before RCA 6 and 7),
`after.json`.

### Ground truth (Knowledge-News-App @ 20d352e, 145 sites)

| Kind | Sites | Before | After |
|---|---|---|---|
| call | 93 | 81 (87.1%) | 92 (98.9%; 100% excl. hard) |
| reference | 28 | 0 | 28 (100%) |
| param_reference | 11 | 0 | 11 (100%) |
| inherits | 13 | 0 | 13 (100%) |
| **All** | **145** | **81 (55.9%)** | **144 (99.3%)** |
| Precision | | 100% | 100% |

"Before" was first scored against the original 136-site labelling (81/136 = 59.6%). The 9 sites
added in RCA 7 are references, a kind the old engine couldn't produce, so before = 81/145 on the
amended set.

### Other checks

| Check | Before | After |
|---|---|---|
| Unconnected calls naming a repo definition: test repo | 16 | 5 (all external or dynamic) |
| Same, RudhMap `src/` | 48 | 4 (all external or dynamic) |
| Nodes from tool folders when scanning RudhMap's root | 175 (half the graph) | 0 |
| Cross-file resolution on RudhMap's root scan | 0 resolved (see RCA 1) | 91 resolved |
| Determinism | identical | identical |
| Build time, test repo, cold / warm | 1.12s / 0.27s | 0.44s / 0.25s |
| Test repo graph | 102 nodes / 81 edges | 134 nodes / 144 edges |
| RudhMap `src/` graph | 169 nodes / 244 edges | 224 nodes / 377 edges |
| Tests | 244 passed | 259 passed |

Node counts grow mainly from the new per-file module nodes (32 in the test repo).

## 5. RCA

**1. Scanning the repo root doubled the graph and switched off cross-file resolution.**
Symptom: 361 nodes at the root vs 169 for `src/`; 0 cross-file resolutions.
Root cause: Claude Code keeps worktrees under `.claude/worktrees/`, full copies of the repo. The skip
list had no `.claude`, and discovery ignored `.gitignore`. Every module then existed twice, so every
Python import matched two files and the resolver, which only connects a unique match, connected none.
Fix: git-based discovery plus `.claude` in the skip list. Now 0 stray nodes and 91 cross-file resolutions.

**2. Calls to nested helper functions were never connected (36 of 48 misses in RudhMap `src/`).**
Root cause: a bare call was only looked up at module level (`file:name`), never in enclosing
functions (`file:outer.name`). Fix: scope-chain lookup, skipping class bodies.

**3. Top-level code had no caller (10 of 16 test-repo misses).**
Root cause: calls outside any function have the file itself as their source, and no node had that id,
so assembly dropped them. Fix: a `module` node per non-empty file. Empty files get none, because a
`line: 1` citation in an empty file would fail verification.

**4. Calls on variables were never connected (`request.resolved_domains()`, `files.lines()`, `cache.get_or_compute()`).**
Root cause: the extractor recorded no types, so `x.m()` had nothing to resolve `x` against. Fix: types
the file itself states (constructor assignment, annotations, `self.x = Foo()`). A type must resolve to
a class node; `x = make_thing()` proves nothing and is ignored. An untyped rebinding clears the known type.

**5. Functions passed as values, `Depends(...)` and inheritance were never extracted (43 of 145 sites, 0 found).**
Root cause: only call expressions were emitted. Fix: `references` and `inherits` edges. Locally bound
names are excluded so a variable that shares a definition's name isn't linked (tested).

**6. Warm builds got 3× slower after the first version of the fix (0.27s → 0.86s).**
Root cause, from cProfile: `git ls-files` ran once per extractor (7 × ~60ms), and dotted-module lookup
scanned every file path for each of ~700 lookups. Fix: one listing per build (`shared_file_listing`)
and a file-name index in the resolver. Cold 0.44s and warm 0.25s, faster than before step 1.

**7. Nine "extra" edges were ground-truth omissions, not false positives.**
The first after-run reported 9 edges not in the ground truth, i.e. precision 93.8%. Reading each cited
line showed all 9 were real: 8 `response_model=X` decorator arguments and `StateGraph(PipelineState)`.
The labelling pass had missed them. They were added to the ground truth, with an amendment log in the
file. At the same time, decorator arguments were re-attributed from the file's top-level code to the
decorated function, because "this route returns `FeedRefreshResponse`" is more useful context. This is
the one place the ground truth changed after seeing tool output. Each addition was verified against
the source line, and the before score is reported on both versions.

**8. Side effect: context packs overflowed their budget on dense slices.**
Symptom: `rudhmap context ... "how does refresh feed work" --budget 2000` gave ~3,212 tokens (before
step 1: ~1,925), with 0 snippets and 88 edges.
Root cause, two parts:
- The budget loop could only demote source snippets, never call-graph lines or references, so a slice
  with many edges overflowed. This was a latent bug, now exposed.
- The slice itself grew from 8 to 17 files: all 11 API routes now (correctly) reference `get_db`, which
  makes it a hub that pulls every route into the slice.

Fix for the first part: the budget is a hard limit; the farthest references, then the farthest
connections, are cut, and the cut is stated. Now ~1,990/2,000 (regression test added).
**Deferred:** the second part, relevance. The pack is all call graph and no code for this question.
That is the slicer's known keyword-search and hub weakness (`eval/cases.md` Case 3). The plain-English
slicer is replaced by named-symbol tools in step 4, so it isn't tuned here.

**9. Mutation testing found dead code.** The "container annotation" guard (`List[Foo]` is not a `Foo`)
could be disabled without any test failing: the rule that an annotation must name exactly one type
already rejects `List[Foo]`. The guard was removed. Two other guards were confirmed load-bearing by
mutation (see §3).

**10. Remaining misses (not fixable with static rules; reported, not hidden).**
- Test repo, 5: `agent.run()` on a value from a dict (the one `hard` ground-truth site), and
  `uvicorn.run`, `asyncio.run`, `client.search`, `_client.search`, which are library calls whose
  method names happen to match a definition in the repo.
- RudhMap `src/`, 4: `compute()` (a function received as a parameter, called twice), `os.walk`, and
  `super().__new__`.

Step 4's tools will surface these as "N calls couldn't be resolved" instead of silently omitting them.

## 6. Limits of this evaluation

- **One small ground-truth repo** (1,749 lines, FastAPI). The rules may be tuned to its style. Step 3's
  second repo (mid-size, open source) is the out-of-sample check; precision and recall must be
  re-measured there before claiming them generally.
- **TypeScript got only module nodes and the shared scoping rule.** Type tracking, references and
  inheritance are Python-only, and none of it is measured, because neither eval repo has TypeScript.
  Step 3 should pick a repo with a TS frontend.
- **Dynamic code is out of reach by design:** dict dispatch, callables passed as parameters, `getattr`.

## 7. Decision

All pass criteria met: recall 100% excluding `hard` (99.3% overall), precision 100%, 0 tool-folder
nodes, deterministic, 259 tests green. **Step 1 passes.**

Carried into later steps:
- **Step 2:** keep the graph in memory; one git listing per build is enough for now, but incremental
  refresh is still missing.
- **Step 3:** choose the second repo with TypeScript in it, and add a ground-truth slice for it to
  `engine_eval.py`.
- **Step 4:** the `show` tool must print unresolved calls. The context pack and slicer stay as they are
  until replaced.
