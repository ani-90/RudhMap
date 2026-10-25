# RudhMap

RudhMap is an MCP server that gives AI coding assistants a map of a codebase where every connection is backed by the exact file and line that proves it, so they stop guessing.
**this README documents only what is actually implemented so far.**

## Status

This repo currently implements **structural extraction, graph assembly, slicing, verification, draw.io rendering, and an MCP server exposing them (no LLM involved anywhere yet)**. Concretely:

- Tier 0: IaC/config extractors (Terraform, docker-compose, Dockerfile, Kubernetes manifests)
- Tier 1: YAML-declared regex rule engine over application source
- Tier 2: tree-sitter AST extractors for Python and TypeScript
- Content-addressed extraction cache (SHA-256 keyed, tier 1/2 only)
- Graph assembly from extracted evidence into a NetworkX graph
- Identity resolution: same-scope call resolution, cross-file import resolution, and compose build-context containment
- Slicer: query-scoped subgraph for a plain-English question (BM25 seed + bounded weighted k-hop expansion, ambiguity detection)
- IR + verifier: drops any node/edge whose `file:line` citation doesn't resolve on disk
- Deterministic layered layout + draw.io renderer: every box and arrow carries its `file:line` evidence (shown on hover)
- Context packs (experimental): a token-budgeted call graph plus the cited source of the most relevant functions, meant to give an LLM coding agent what it needs to answer a question about a repo without hunting through files
- Two benchmark scripts: pack size vs. whole files, and real Claude Code runs with vs. without the `get_context` tool
- `scan` / `slice` / `diagram` / `context` CLI commands
- An MCP server (`rudhmap-mcp`, stdio) exposing `scan`, `slice`, `generate_diagram`, and `get_context`

Not yet implemented: the abstraction LLM pass (diagrams are still one box per function/class/service), SVG/mermaid output, the `trace_edge` MCP tool, tier 3 (LLM extraction), and a full eval harness. None of these exist in the code yet — don't infer them from the spec.

### Results so far (context packs)

Measured with real Claude Code runs (Sonnet, read-only tools), each question answered once without RudhMap and once with `get_context`. Token counts and cost are Claude Code's own usage report. Details and all 16 answers: [`eval/cases.md`](eval/cases.md) Case 7, `eval/agent_runs/`.

| Repo | Questions | Turns (without → with) | Tokens (without → with) | Cost (without → with) |
|---|---|---|---|---|
| `Knowledge-News-App` (FastAPI) | 4 | 13 → 8 | 129,118 → 131,132 | $0.178 → $0.274 |
| RudhMap itself | 4 | 15 → 9 | 172,310 → 190,413 | $0.251 → $0.355 |
| **Total** | **8** | **28 → 17** | **301,428 → 321,545** | **$0.429 → $0.629** |

All 16 answers were correct. **The tool cuts the agent's turns but does not yet save tokens or cost.** The cause is relevance: the slicer often seeds on the wrong functions (e.g. `graph_to_ir` for a question about the extraction cache), so packs carry irrelevant code and the agent still reads files itself. Where the pack did contain the right code (the draw.io layout question), it used 21% fewer tokens. Better seeding and smaller default packs are the current focus; until a benchmark shows otherwise, don't claim token savings.

## Pipeline (as built)

```
tier 0 (IaC)  ─┐                                                             ┌─▶ scan  ─┐
tier 1 (regex) ─┼─▶ extraction cache ─▶ graph assembly ─▶ identity resolution ─┤          ├─▶ IR + verifier ─▶ CLI output / MCP tool result
tier 2 (AST)  ─┘                                                             └─▶ slice ─┘
```

### Tier 0 — IaC/config extractors (`src/rudhmap/extract/tier0_iac/`)

Parse infrastructure-as-code files directly (no regex, no LLM) into evidence nodes/edges:

| File | Extracts |
|---|---|
| `terraform.py` | Terraform resources/modules from `.tf` files (via `python-hcl2`) |
| `compose.py` | Services, images, build contexts, and dependencies from `docker-compose.yml` |
| `dockerfile.py` | Base images and build stages from `Dockerfile` |
| `k8s.py` | Kubernetes manifests (Deployments, Services, etc.) from YAML |

All tier 0 extractors skip vendor/build/VCS directories (`.git`, `node_modules`, `vendor`, `venv`, `.venv`, `__pycache__`, `dist`, `build`) via a shared `COMMON_SKIP_DIRS` set, so a third-party package's bundled compose file (e.g. inside `.venv`) is never mistaken for the scanned repo's own infrastructure.

### Tier 1 — YAML regex rule engine (`src/rudhmap/extract/tier1_rules/`)

Declarative regex rules (`rules/aws.yaml`, `rules/databases.yaml`) matched against application source (Python, JS/TS, Go, Java) to detect SDK/client-construction patterns (e.g. "this file constructs an S3 client"). Produces evidence nodes only — a regex has no notion of scope, so it can say a pattern matched somewhere in a file but not which function it belongs to; building real call edges is tier 2's job.

### Tier 2 — tree-sitter AST extractors (`src/rudhmap/extract/tier2_ast/`)

Real AST parsing for Python and TypeScript. Extracts functions/classes/methods as nodes and call/import edges as edges, including:
- `self.foo` / `this.foo` method calls
- bare (module-level) calls
- import bindings (including aliased imports, `from x import y as z`)

### Extraction cache (`src/rudhmap/cache.py`)

`ExtractionCache` keys extraction results by `(extractor_name@version, file_path, sha256(file_bytes))` and persists to `.rudhmap_cache/extraction_cache.v2.json` in the target repo. Hashing content (never mtime) means a touched-but-unchanged file still hits cache and a changed file is a guaranteed miss (spec invariant 4: same commit → byte-identical output). The path is in the key because cached records cite their own file; the extractor version is in the key so changing an extractor never serves its old output. Currently opted in for tier 1 and tier 2 only (tier 0 IaC parsing is cheap enough not to need it).

### Graph assembly (`src/rudhmap/graph/assemble.py`)

Turns the flat lists of `EvidenceRecord`/`EdgeRecord` from all tiers into one `networkx.MultiDiGraph`. Pure and lossless: every extracted node becomes a graph node exactly as extracted, and an edge whose endpoint has no matching node is dropped (counted, not silently discarded) rather than auto-creating an evidence-less placeholder node.

### Identity resolution (`src/rudhmap/graph/resolve.py`)

Recovers a subset of dropped edges once real graph identities are available, using only information already present in extracted evidence — never a guess:

1. **Same-scope calls** — `self.foo`/`this.foo` and bare module-level calls resolved against the caller's own file/class.
2. **Cross-file calls** — calls through an import binding, resolved via TS/JS relative-path resolution (with extension/index fallback) or Python dotted-import suffix matching against actually-scanned files (left unresolved if ambiguous). This covers bare calls (`put_object()` after `from writer import put_object`) and attribute calls through an imported module or class (`crud.create_user()` after `from app.db import crud`; `User.create()`; TS `import * as crud`): every split of the dotted path into (file, qualname) is tried, and the edge is connected only if exactly one split names both a scanned file and an extracted node.
3. **Compose build-context containment** — links a compose service node to every tier 1/2 code node whose file falls under that service's `build:` context directory, using the compose file's own `file:line` as evidence.

### Slicer (`src/rudhmap/graph/slice.py`)

Turns a plain-English question into a scoped subgraph: BM25 picks seed nodes (indexing only each node's file basename + qualname, never parent directories), a weighted bounded-Dijkstra expansion (max 3 hops) pulls in nearby dependencies, and a 60-node cap trims the rest deterministically. If the top matches fall into separate subsystems with no clear winner, it returns the candidates instead of guessing.

### IR + verifier (`src/rudhmap/ir/`)

`graph_to_ir` flattens a graph into a deterministically sorted node/edge list; `verify_ir` checks schema shape, referential integrity, and that every cited file exists on disk with the cited line in range. Anything that fails is dropped and counted. This proves a citation is *possible*, not that the line's content matches the claim.

### Layout + draw.io renderer (`src/rudhmap/render/`)

`layout.py` is a pure-Python simplified Sugiyama layout (no Graphviz/ELK, so output can't drift with an external tool's version): DFS cycle breaking, longest-path layering (callers above callees), dummy nodes for long edges, barycenter crossing reduction, then components shelf-packed into rows with edge-less nodes in a grid. `drawio.py` writes an uncompressed `.drawio` file where each node/edge is an `<object>` carrying `evidence`, `kind`/`relation`, and a hover tooltip. Parallel edges with the same relation merge into one arrow listing every call site. Output is byte-identical for the same graph regardless of input order: no timestamps or random ids.

Open the file in draw.io desktop, [app.diagrams.net](https://app.diagrams.net), or the VS Code Draw.io extension.

### Context packs (`src/rudhmap/context.py`)

Turns the slice for a question into the smallest text an LLM needs to answer it, instead of having it grep and read whole files. A pack has three parts:

1. **Call graph**: every edge in the slice, one line each, cited `file:line` (repeated calls between the same pair collapse to one line listing every site).
2. **Source**: the bodies of the most relevant functions/classes, cut to their exact line ranges (tier-2 extractors record `end_line`), ranked seeds first and then by hop distance, and added until `token_budget` is reached. A class shows only its header when its methods have their own snippets; any single body is cut at 80 lines.
3. **Also involved, not shown**: everything that didn't fit, as `file:start-end`, so the model can read exactly those lines if it needs them.

An ambiguous query isn't a dead end here: the top 3 candidate areas are seeded together. Token counts are an estimate (~4 characters per token).

### Benchmarks (`eval/`)

```
python eval/context_bench.py <repo> <questions.txt> [--budget N] [--show-files]
python eval/agent_bench.py <repo> "<question>" [--model sonnet] [--out DIR]
```

- `context_bench.py` compares each pack's size with reading every file the slice touches in full (median 2.2× smaller at a 4,000-token budget on `Knowledge-News-App`, Case 6). This is a size comparison only: a real agent reads far fewer files than that, so it overstates any saving.
- `agent_bench.py` is the real test: it runs Claude Code headless (`claude -p`) twice on the same question, with and without `get_context`, and prints turns, tokens and cost from Claude Code's own usage report, saving both answers. It needs the `claude` CLI and spends real usage (a few cents per question on Sonnet). When benchmarking a repo against itself, pass `--out` outside the repo so the second run can't read the first run's answer.

### CLI (`src/rudhmap/cli.py`)

```
rudhmap scan <repo_path>
rudhmap slice <repo_path> "<question>" [--max-nodes 60]
rudhmap diagram <repo_path> [-q "<question>"] [--max-nodes 60] [-o out.drawio]
rudhmap context <repo_path> "<question>" [--budget 6000] [--max-nodes 60]
```

(`python -m rudhmap ...` works too.) `scan` runs all tiers, prints every extracted node/edge with its `file:line`, assembles, resolves and verifies the graph, and prints a summary. `slice` prints the scoped subgraph for a question. `diagram` writes a `.drawio` file of the whole repo, or of a slice with `-q`; the default output is `rudhmap.drawio` (or `rudhmap-<query>.drawio`) in the repo root. `context` prints a context pack to stdout (pipe it into a prompt) and its size stats to stderr.

If a question is ambiguous, `slice`/`diagram` list candidate node ids; re-run with one of those ids as the query (e.g. `-q "app/api/user.py:create_user"`) to slice on it directly.

### MCP server (`src/rudhmap/server.py`)

```
rudhmap-mcp            # stdio transport
```

Exposes four tools over stdio, built on the official `mcp` Python SDK (2.x):

| Tool | Arguments | Returns |
|---|---|---|
| `scan` | `repo_path` | The full verified graph: nodes (`id`, `kind`, evidence list) and edges (`src`, `dst`, `relation`, evidence), plus verifier drop counts |
| `slice` | `repo_path`, `query`, `max_nodes=60` | `status: "ok"` with a verified subgraph, `"ambiguous"` with candidate subsystems, or `"no_match"` |
| `get_context` | `repo_path`, `query`, `token_budget=6000`, `max_nodes=60` | `status: "ok"` with `context` (the markdown context pack) and size stats, or `"no_match"` |
| `generate_diagram` | `repo_path`, `query=None`, `max_nodes=60`, `output_path=None` | Writes a `.drawio` file (whole repo, or a slice) and returns its path and counts; writes nothing if the query is ambiguous/unmatched |

`scan`, `slice` and `get_context` are read-only. `generate_diagram` only ever writes a `.drawio` file (it refuses any other extension). In any tool, an exact node id as the query (e.g. a candidate `label` from an ambiguous result) slices on that node directly.

All ids and paths in results are relative to the repo root with forward slashes, so the same commit gives the same result regardless of checkout location or OS. Both CLI and server build graphs through the same `rudhmap.pipeline.build_assembly`.

Register it with Claude Code:

```
claude mcp add rudhmap -- <path-to-venv>/Scripts/rudhmap-mcp     # Windows
claude mcp add rudhmap -- <path-to-venv>/bin/rudhmap-mcp         # macOS/Linux
```

Any other MCP client (e.g. VS Code) takes the same command as a stdio server.

## Repo layout

```
src/rudhmap/
├── cli.py                     # scan / slice / diagram / context CLI entrypoint
├── server.py                  # MCP server (stdio): scan / slice / generate_diagram / get_context
├── context.py                 # slice -> token-budgeted context pack for an LLM (shared by CLI + MCP)
├── pipeline.py                # shared extract -> assemble -> resolve -> (slice) -> verify
├── diagram.py                 # pipeline -> render -> write .drawio (shared by CLI + MCP)
├── paths.py                   # repo-relative ids/paths for anything leaving the process
├── cache.py                   # SHA-256 content-keyed extraction cache
├── extract/
│   ├── schema.py               # EvidenceRecord / EdgeRecord (shared across all tiers)
│   ├── tier0_iac/               # Terraform, compose, Dockerfile, k8s
│   ├── tier1_rules/              # YAML regex rules + engine
│   └── tier2_ast/                # tree-sitter Python + TypeScript
├── graph/
│   ├── assemble.py             # flat records -> NetworkX graph
│   ├── resolve.py              # identity resolution passes
│   └── slice.py                # query-scoped subgraph
├── ir/
│   ├── schema.py               # IRNode / IREdge / IRGraph
│   ├── convert.py              # NetworkX graph -> sorted IR
│   └── verify.py               # evidence verifier
└── render/
    ├── layout.py               # deterministic layered layout
    └── drawio.py               # IR + layout -> .drawio XML

eval/
├── cases.md                    # findings log: what was tested, what broke, what it showed
├── context_bench.py            # pack size vs. whole files, per question
├── agent_bench.py              # real Claude Code runs, with vs. without get_context
└── agent_runs/                 # saved answers from agent_bench.py
```

## Testing

```
pip install -e ".[dev]"
pytest
```

244 tests currently pass, covering every extractor (base + edge-case fixtures), the tier 1 rule engine, the cache, graph assembly, all three identity-resolution passes, the slicer, the IR verifier, layout and draw.io rendering (including byte-identical output under shuffled input), context packs (exact line ranges, budget enforcement, checkout-location independence), the `diagram` CLI command, and the MCP server (driven through a real in-process MCP client).

## Known limits

- **Recursive functions produce self-loop edges in the raw graph.** Tier 2's call-edge extraction is exact: if a function genuinely calls itself (e.g. `tier2_ast/python.py:_flatten_callee`, `tier2_ast/typescript.py:_flatten_callee`, `tier0_iac/terraform.py:_iter_refs` — all real recursive helpers in this codebase itself), the graph gets a real self-loop edge citing the real `file:line` of the recursive call. This is expected, evidence-correct behavior, not a bug — confirmed by dogfooding `scan` against this repo (see [`eval/cases.md`](eval/cases.md)).

- **The slicer's search is keyword-based and often picks the wrong starting functions** for plain-English questions (BM25 over names only). This limits slices, diagrams and context packs alike, and is why `get_context` doesn't yet save tokens (see "Results so far").
- **Static analysis only.** Calls on object instances (`store.put()`), dynamic dispatch and default imports aren't resolved, and only Python/TypeScript code (plus IaC files) is read.

## Requirements

Python ≥3.10. Dependencies: `python-hcl2`, `pyyaml`, `tree-sitter` (+ `tree-sitter-python`, `tree-sitter-typescript`), `networkx`, `rank-bm25`, `mcp` (2.x), `anyio`.
