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
Four outputs, each an MCP tool and a CLI command, compact text, token-budgeted:
- `repo_map`: main modules and symbols with one-line signatures, most-connected first.
- `find_symbol`: fuzzy name/keyword search returning names + locations, not code.
- `show`: one symbol at `signature` / `skeleton` / `full` detail, plus callers/callees
  as one-liners, module constants it uses, and what couldn't be resolved.
- `trace`: call chain(s) from a symbol or between two symbols, with call-site lines.
- Graph kept in memory by the MCP server; changed files re-parsed on each call.
- TS: JSX component use (`<Foo />`) and hooks as connections.
- **Eval:** golden outputs on fixtures, output size limits on all 3 repos,
  `find_symbol` retrieval accuracy on a labelled query set, determinism.

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
