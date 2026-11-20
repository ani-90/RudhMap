# RudhMap

RudhMap builds a map of a codebase (every function and class, and which ones call which) directly from the source, with no LLM, and lets AI coding assistants like Claude Code and Cursor query it through an MCP server or a CLI. Every fact it returns cites the `file:line` that proves it.

## Status (November 2026)

| | |
|---|---|
| **Engine** | Python and TypeScript/React. **99.3% recall, 100% precision** against 145 hand-labelled call sites ([report](eval/reports/step1-engine.md)) |
| **Tools** | `find_symbol`, `show`, `trace`, `repo_map`, as MCP tools and CLI commands. In-memory index, ~40 ms per query, refreshed when files change ([report](eval/reports/stepB-tools.md)) |
| **Benchmark** | 405 headless Claude Code sessions plus a 120-session held-out run. **RudhMap did not reduce token use in realistic setups**, and an accuracy gain on the tuning questions did not hold on held-out questions ([report](eval/reports/stepC-benchmark.md), [write-up](blog/README.md)) |
| **Next** | Redesign around removing agent rounds (context attached before the first model call). Not started |

RudhMap is a research project, not a released product. The write-up of what the benchmark found, and why, is in [`blog/README.md`](blog/README.md). The full story, step by step, is in [`docs/journey.md`](docs/journey.md).

## What the tools return

| Tool / command | Returns |
|---|---|
| `find_symbol` / `rudhmap find "<words>"` | Functions, classes, files and HTTP routes matching a name or keywords, each with `file:line` and signature. For an identifier that isn't a symbol (e.g. `SECRET_KEY`), every line it appears on with its enclosing function. When one match clearly wins, its full source |
| `show` / `rudhmap show <symbol>` | A function, class or file: source with line numbers; what it calls (signature, first doc line, tiny bodies inline, followed through callbacks and module values); who calls it; constants it uses; overrides; stubs flagged; what couldn't be resolved. Several symbols at once: `"a, b"` |
| `trace` / `rudhmap trace <from> [<to>] [--up]` | The call path between two symbols, or the call tree below or the callers above one |
| `repo_map` / `rudhmap map [<folder>]` | Files with their main functions, classes and HTTP routes, within a token budget |

Each output has a token budget (`find_symbol` 400, `show` 2,000, `trace` 800, `repo_map` 1,500), and anything cut says so.

## Install and use

Requires Python 3.10+.

```bash
git clone https://github.com/ani-90/RudhMap && cd RudhMap
pip install -e ".[dev]"

# CLI, from inside any repo
rudhmap find "refresh feed"
rudhmap show refresh_feed
rudhmap trace refresh_feed bulk_insert_articles
rudhmap map app/api
```

Add the MCP server to Claude Code from the repo you want to work in:

```bash
claude mcp add rudhmap -- rudhmap-mcp
```

The server indexes its working directory in the background on startup (set `RUDHMAP_REPO` to point it elsewhere). It adds about 740 tokens of tool descriptions to every model call.

The extraction cache lives outside your repo, in `%LOCALAPPDATA%\rudhmap\cache` on Windows or `~/.cache/rudhmap` elsewhere. `RUDHMAP_CACHE_DIR` overrides it.

## How it works

1. **File discovery** follows `git ls-files` (so `.gitignore` is respected) and skips vendor, virtualenv, test and tool folders.
2. **Extraction** uses tree-sitter for Python and TypeScript/TSX. It records definitions with signatures and docstrings, calls, functions passed as values, base classes and JSX component use. Terraform, docker-compose, Dockerfile and Kubernetes files are parsed too.
3. **Resolution** connects a call to its definition only when the code proves it:
   - **scope:** scope-chain lookup for nested functions;
   - **imports:** across files, including relative imports, tsconfig path aliases, default exports and barrel re-exports;
   - **types:** stated types (`x = Foo()`, `x: Foo`, `-> Foo` return annotations), inherited methods, and module-level values built by a function.
4. **Index:** the graph is kept in memory and rebuilt when a source file changes. Per-file parse results are cached by content hash.

No LLM is used anywhere in the engine or the tools.

## Benchmark

The benchmark asks real questions about 3 repositories, plus a held-out set on a 4th, `Textualize/rich`. Each runs in fresh headless Claude Code sessions in four setups:
- **plain:** Read, Grep and Glob only;
- **natural:** plain plus RudhMap's tools;
- **nudged:** natural plus a one-line instruction;
- **only:** RudhMap's tools alone.

Answers are graded against hand-written keys by a blind 3-vote Sonnet grader, validated against hand grading (17/18 agreement). Pass criteria were committed before the first run ([`eval/THRESHOLDS.md`](eval/THRESHOLDS.md)).

Final tuning round, Claude Haiku, 15 questions × 3 runs:

| Setup | Correct | Median tokens / question | vs plain |
|---|---|---|---|
| Plain | 12/15 | 31.4k | — |
| Natural | 13/15 | 35.4k | 113% |
| Nudged | 13/15 | 41.7k | 133% |
| RudhMap only | 10/15 | 29.9k | 95% |

On the 8 held-out questions, plain Haiku answered 6/8 correctly and every RudhMap setup fewer (natural 5/8). Token use was again not lower in realistic setups.

The main finding is that in an agent loop, cost is roughly *rounds × fixed context*: Claude Code re-sends ~6.4k tokens on every model call. Richer tool answers didn't reduce the number of rounds (about 3.7 per question in every setup), so they couldn't reduce the total.

Run it yourself:

```bash
python eval/bench/run_bench.py run   --label mine --arms none,rudhmap --models haiku --reps 3
python eval/bench/run_bench.py grade --label mine
python eval/bench/run_bench.py runs  --label mine     # one row per run + summary
python eval/engine_eval.py --label mine               # engine accuracy vs hand-labelled call sites
python eval/tools_eval.py  --label mine               # tool output size, search accuracy, coverage, latency
```

The benchmark expects the evaluated repos cloned next to this one, at the commits pinned in `eval/bench/questions.yaml`, and uses your Claude Code login.

## Known limits

- **Static analysis only.** Dynamic dispatch (a function picked from a dict or received as a parameter), `getattr` and string type hints (`x: "Foo"`) aren't resolved, and callers reached that way are missing from `show` and `trace`. The held-out benchmark showed models trust an incomplete caller list, so treat "called by" as a lower bound.
- **Code files only for the tools.** Shell scripts, Markdown, `.env` and similar files are invisible to RudhMap.
- **No type tracking for TypeScript;** Python only.
- **Recursive functions show as self-loops,** which is correct: they really call themselves.

## Legacy: evidence-cited diagrams

RudhMap started as a draw.io diagram generator. Those commands still work, but are frozen:
- **CLI:** `rudhmap scan`, `rudhmap slice`, `rudhmap diagram`, `rudhmap context`.
- **MCP:** the old tools are available with `rudhmap-mcp --legacy`.

The diagram-era history is in `CLAUDE.md` and `eval/cases.md`.

## Repository layout

| Path | Contents |
|---|---|
| `src/rudhmap/extract/` | Extractors: tree-sitter Python/TypeScript, IaC, regex rules |
| `src/rudhmap/graph/` | Graph assembly and resolution |
| `src/rudhmap/tools/` | The index (`index.py`) and tool outputs (`views.py`) |
| `src/rudhmap/server.py`, `cli.py` | MCP server and CLI |
| `eval/` | Benchmark harness, ground truth, question sets, results and step reports |
| `docs/` | Plan, journey overview, pre-registered next experiments |
| `blog/` | Write-up of the benchmark findings |
| `tests/` | ~280 tests (`pytest`) |
