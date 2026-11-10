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

### Step 1: Engine correctness
Make the graph complete and clean, because every tool's answers come from it.
- File discovery respects `.gitignore` and skips tool folders (`.claude/`), so nested worktrees aren't scanned.
- Call resolution: nested functions, top-level (module) code as a caller, calls on variables whose type is visible (`x = Foo()`, `x: Foo`, `self.x = Foo()`), inherited methods.
- New connection kinds: functions/classes passed as values (callbacks, background tasks, `Depends(get_db)`) and inheritance.
- **Eval:** `eval/engine_eval.py` against a hand-labelled ground truth of every connection in Knowledge-News-App (136 call sites), plus the unresolved-call audit on RudhMap's own `src/`, discovery, determinism and speed.
- **Pass:** recall ≥ 95% on ground truth excluding `hard` cases, precision ≥ 98%, 0 nodes from tool folders, identical output across runs, all tests green.

### Step 2: Engine serving
Make it fast and fresh inside a long-running MCP server.
- Keep the graph in memory between calls; re-parse only changed files (cheap stat check, then hash).
- Background indexing at server start; single-file requests answered immediately without waiting.
- Cache moves out of the user's repo into a user cache folder.
- **Eval:** latency per call (cold, warm, after editing a file), correctness after edits (an edit is reflected in the next answer), memory use, on the test repo and a larger repo.

### Step 3: Benchmark harness and baselines
Measure the problem before building the solution.
- Question set (~15) over 2 repos (Knowledge-News-App + one mid-size open-source repo without CLAUDE.md), with hand-written answer keys (facts a correct answer must contain). Question types where reading dominates: trace a request, impact of a change, where a value is used, explain a function in context.
- `agent_bench.py` upgrade: per-turn logging (tool, result size), hide CLAUDE.md, repeats, arms (none / Serena / RudhMap), models (Sonnet, Haiku), blind grading against the answer key, tokens per correct answer.
- Pass/fail thresholds committed to `eval/THRESHOLDS.md` before any RudhMap run.
- **Eval:** baseline report for none and Serena arms, with RCA of where baseline agents spend tokens and get answers wrong. That RCA shapes Step 4.

### Step 4: The tools
Four outputs, each as an MCP tool and a CLI command, compact text, token-budgeted:
- `repo_map`: files and main symbols with one-line signatures, most-connected first.
- `find_symbol`: fuzzy name search (snake/camel aware) for when the model doesn't know names.
- `show`: one symbol at `signature` / `skeleton` / `full` detail, plus callers/callees as one-liners, module constants it uses, and what couldn't be resolved.
- `trace`: call chain(s) between two symbols with call-site lines.
- **Eval:** golden outputs on fixtures, token size per tool vs reading the same files, `find_symbol` retrieval accuracy on a labelled query set, `trace` correctness against ground truth, determinism.

### Step 5: Full comparison and decision
- Matrix: Sonnet and Haiku × no tool / Serena / RudhMap × questions × 3 repeats.
- **Stop** unless Haiku + RudhMap beats plain Haiku on correct answers at equal or fewer tokens. **Headline** if Haiku + RudhMap matches plain Sonnet.
- Report includes every question RudhMap lost, with RCA.

### Step 6 (only if Step 5 passes): small local model
Minimal tool-calling harness for a local model (OpenAI-compatible server), same tools vs plain read/grep.

### Step 7 (only if Step 5 passes): cross-layer links and release
API routes ↔ frontend calls, env vars ↔ compose/Terraform, packaging (`uvx rudhmap-mcp`), README around the benchmark table, PyPI.
