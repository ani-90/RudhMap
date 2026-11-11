# RudhMap plan

## Goal

A tool an LLM uses to gather context about a repo while spending **fewer tokens
and fewer round trips per correct answer** than it does with its usual tools
(grep, read whole files), so that even small models answer repo questions well.

RudhMap parses the repo once (locally, no LLM, no tokens), keeps a graph of every
function/class and how they connect, and hands the LLM exactly the part it
needs: a repo map, a condensed view of a function, the connections between
functions, or exact source lines. Line numbers are kept only as cheap pointers
(`feed.py:47` instead of the code), not as a selling point.

Usable two ways: an MCP server (Claude Code, Cursor, ...) and a CLI (developers,
shell-based agents, scripts). Both share one engine and one cache.

The diagram/draw.io code stays in the repo but is frozen and off the roadmap.

## How every step is run

Each step ends with a report in `eval/reports/step<N>-<name>.md` containing:

1. **Goal**: what the step must achieve, with pass criteria written *before* the work.
2. **Changes**: what was built or changed.
3. **Evaluation suite**: what was measured and the exact command to reproduce it.
4. **Results**: before → after numbers, with raw output kept in `eval/results/`.
5. **RCA**: every failure, miss or surprise: symptom, root cause, fix or reason it is deferred.
6. **Decision**: pass/fail against the criteria, and what changes for the next step.

Ground truth is always written by hand before measuring, never derived from RudhMap's own output.

## Steps

Re-planned 2026-11-11 for the fastest honest route to a v1: measure, build the
four tools, iterate on them against the benchmark, release. Step 1 is done;
the old steps 2-7 are folded into A-D below or cut from v1.

### Step 1: Engine correctness (PASSED 2026-11-10)
Report: `eval/reports/step1-engine.md`. Recall 99.3%, precision 100% on a
hand-labelled ground truth of Knowledge-News-App.

### Step A: Questions and baseline
Measure the problem before building the solution.
- 15 questions over 3 repos (Knowledge-News-App, fastapi/full-stack-fastapi-template
  incl. its TS frontend, encode/httpx), pinned commits, hand-written answer keys
  (3-5 facts each, critical/supporting, with file:line), written before RudhMap
  is run on these repos.
- Each run: fresh export from git into a temp dir, CLAUDE.md/AGENTS.md removed,
  fresh headless Claude Code session, Read/Grep/Glob only, no MCP, no memory, no
  user settings. Per-call logging (tool, input, result size).
- Arms: Haiku and Sonnet without RudhMap, 3 repeats each.
- Blind grading by a separate Sonnet grader against the key; 20% hand-checked.
- Step C thresholds committed to `eval/THRESHOLDS.md` before any RudhMap run.
- **Pass:** all runs complete, grader agreement with hand checks >= 90%,
  variance reported, RCA of every wrong answer and of where tokens go.

### Step B: The tools
Goal (narrowed 2026-11-12): RudhMap controls exactly two things in the model's
context: **its tool results** and **its tool definitions**. Everything else
(Claude Code's system prompt, built-in tools, CLAUDE.md, the question, the
model's own output) is fixed or not ours. Step B makes tool results complete
enough that the model needs no follow-up call and compact enough not to bloat,
and keeps the tool definitions small and clear.

Four MCP tools (and CLI commands with identical output), repo defaults to the
server's working directory:
- `find_symbol(query)`: fuzzy name/keyword search -> one line per match (kind, file:line, signature).
- `show(symbol, detail)`: one function/class/file at `signature` / `outline` / `full`;
  callees with signature + first doc line, tiny (<=3-line) callee bodies inline, one extra
  hop through callbacks/background tasks; callers; unresolved calls stated.
- `trace(from, to?)`: call chain(s) with call-site lines, or the reachable tree to depth 3.
- `repo_map(path?)`: folders/files with their main symbols and routes, within a budget.

Engine work: Python signature/docstring/decorator attrs; TS arrow-function components as
nodes, JSX usage and signatures as edges/attrs; graph kept in memory by the MCP server with a
changed-file check per call; old scan/slice/get_context/diagram tools removed from the MCP
surface (kept in the CLI).

**Pass criteria** (no LLM; measured on the 4 bench repos, tuning questions only):

| Check | Pass |
|---|---|
| Unit tests incl. exact-output fixtures and the existing suite | all green |
| Step 1 engine eval (`engine_eval.py`) | recall/precision unchanged (>= 99.3% / 100%) |
| Output size: show <= 2,000 tokens, repo_map <= 1,500, find_symbol <= 400, trace <= 800 (chars/4), every cut stated | 100% of calls on a 200-call sweep |
| `find_symbol` top-3 accuracy on a hand-labelled query set (~30, tuning repos) | >= 90% |
| Coverage: for each tuning question, the facts' symbols appear in at most 2 RudhMap calls from the obvious entry symbol | >= 12 of 15 |
| MCP tool definitions size (tokens added per model call) | <= 800 |
| Determinism: same call twice, and cold vs warm | identical output |
| Latency on rich: first call (cold cache) / warm call / after editing one file | <= 5 s / <= 300 ms / <= 1.5 s |

### Step C: Benchmark and iterate
- Haiku (and Sonnet) + RudhMap on the step A questions, same harness.
- RCA every lost or expensive question (map wrong, tool missing, output too big,
  tool ignored), fix, rerun. At most 3 rounds.
- **Pass:** see `eval/THRESHOLDS.md`. **Stop and rethink** if 3 rounds don't pass.

### Step D: Release
`uvx rudhmap-mcp` / `pip install rudhmap`, README built around the benchmark table
and its limits, setup snippets for Claude Code / Cursor / Claude Desktop, PyPI.
Clean-machine install tested against a repo not used in tuning.

### Cut from v1
Diagrams, `get_context`, step 1b ground truth on more repos, local small model,
cross-layer links (API routes <-> frontend calls, env vars <-> compose).

### Enhancements backlog (revisit after v1)
- **Persist the resolved graph, not just per-file parse results.** Today a server
  restart re-runs resolution over cached parse results (~0.5 s on rich, ~2.1 s with
  an empty cache). Saving the connected graph keyed by the file snapshot would make
  restart near-instant; only worth it if larger repos make the rebuild noticeable.
- **Incremental rebuild after an edit.** Re-parse and re-resolve only the changed
  files and their dependents instead of the whole graph (~1 s on rich today).
- **Property access as a connection** (`self.content` where `content` is a
  `@property`), which would close the httpx-5 coverage miss.
- **Cross-layer links** (frontend API call -> backend route), already cut from v1;
  closes tpl-4.
