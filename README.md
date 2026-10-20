# RudhMap

An MCP server that generates verified data flow diagrams from source code — every component and arrow traceable to a line of code, laid out deterministically.

RudhMap reads a repo and produces an evidence-cited architecture graph: no node or edge is asserted unless it resolves to a real `file:line`.  **this README documents only what is actually implemented so far.**

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
- `scan` / `slice` / `diagram` CLI commands
- An MCP server (`rudhmap-mcp`, stdio) exposing `scan`, `slice`, and `generate_diagram`

Not yet implemented: the abstraction LLM pass (diagrams are still one box per function/class/service), SVG/mermaid output, the `trace_edge` MCP tool, tier 3 (LLM extraction), and the eval harness. None of these exist in the code yet — don't infer them from the spec.

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

### CLI (`src/rudhmap/cli.py`)

```
rudhmap scan <repo_path>
rudhmap slice <repo_path> "<question>" [--max-nodes 60]
rudhmap diagram <repo_path> [-q "<question>"] [--max-nodes 60] [-o out.drawio]
```

(`python -m rudhmap ...` works too.) `scan` runs all tiers, prints every extracted node/edge with its `file:line`, assembles, resolves and verifies the graph, and prints a summary. `slice` prints the scoped subgraph for a question. `diagram` writes a `.drawio` file of the whole repo, or of a slice with `-q`; the default output is `rudhmap.drawio` (or `rudhmap-<query>.drawio`) in the repo root.

If a question is ambiguous, `slice`/`diagram` list candidate node ids; re-run with one of those ids as the query (e.g. `-q "app/api/user.py:create_user"`) to slice on it directly.

### MCP server (`src/rudhmap/server.py`)

```
rudhmap-mcp            # stdio transport
```

Exposes three tools over stdio, built on the official `mcp` Python SDK (2.x):

| Tool | Arguments | Returns |
|---|---|---|
| `scan` | `repo_path` | The full verified graph: nodes (`id`, `kind`, evidence list) and edges (`src`, `dst`, `relation`, evidence), plus verifier drop counts |
| `slice` | `repo_path`, `query`, `max_nodes=60` | `status: "ok"` with a verified subgraph, `"ambiguous"` with candidate subsystems, or `"no_match"` |
| `generate_diagram` | `repo_path`, `query=None`, `max_nodes=60`, `output_path=None` | Writes a `.drawio` file (whole repo, or a slice) and returns its path and counts; writes nothing if the query is ambiguous/unmatched |

`scan` and `slice` are read-only. `generate_diagram` only ever writes a `.drawio` file (it refuses any other extension). In any tool, an exact node id as the query (e.g. a candidate `label` from an ambiguous result) slices on that node directly.

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
├── cli.py                     # scan / slice / diagram CLI entrypoint
├── server.py                  # MCP server (stdio): scan / slice / generate_diagram
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
```

## Testing

```
pip install -e ".[dev]"
pytest
```

232 tests currently pass, covering every extractor (base + edge-case fixtures), the tier 1 rule engine, the cache, graph assembly, all three identity-resolution passes, the slicer, the IR verifier, layout and draw.io rendering (including byte-identical output under shuffled input), the `diagram` CLI command, and the MCP server (driven through a real in-process MCP client).

## Known limits

- **Recursive functions produce self-loop edges in the raw graph.** Tier 2's call-edge extraction is exact: if a function genuinely calls itself (e.g. `tier2_ast/python.py:_flatten_callee`, `tier2_ast/typescript.py:_flatten_callee`, `tier0_iac/terraform.py:_iter_refs` — all real recursive helpers in this codebase itself), the graph gets a real self-loop edge citing the real `file:line` of the recursive call. This is expected, evidence-correct behavior, not a bug — confirmed by dogfooding `scan` against this repo (see [`eval/cases.md`](eval/cases.md)).

## Requirements

Python ≥3.10. Dependencies: `python-hcl2`, `pyyaml`, `tree-sitter` (+ `tree-sitter-python`, `tree-sitter-typescript`), `networkx`, `rank-bm25`, `mcp` (2.x), `anyio`.
