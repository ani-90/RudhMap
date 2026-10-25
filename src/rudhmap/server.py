"""The MCP server surface: exposes the tier 0-2 pipeline as MCP tools over
stdio, so any MCP client (Claude Code, VS Code, ...) can ask for a repo's
verified graph, a query-scoped slice of it, or a draw.io diagram of either.
No LLM calls happen here -- the tools return exactly what the pipeline
(`rudhmap.pipeline.build_view`) produces, reshaped into JSON.

Every path and node id in a tool result is made relative to the scanned
repo root (`rudhmap.paths.Relativizer`) before it leaves the server, so the
same commit gives the same result regardless of where it's checked out or
which OS scanned it (spec invariant 4).

Nothing in this module may write to stdout: under the stdio transport,
stdout *is* the protocol stream. The pipeline is always run non-verbose.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from rudhmap.context import DEFAULT_TOKEN_BUDGET, build_context_pack
from rudhmap.diagram import generate_diagram
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.ir.schema import IRGraph
from rudhmap.ir.verify import VerificationResult
from rudhmap.paths import Relativizer
from rudhmap.pipeline import VerifiedView, build_view
from rudhmap.render.drawio import edge_relation

mcp = MCPServer(
    name="rudhmap",
    instructions=(
        "RudhMap builds an evidence-cited architecture graph of a local code repository. "
        "Every node and edge it returns cites the file:line that proves it, and anything "
        "whose citation doesn't resolve on disk has already been dropped. Use `get_context` "
        "first when you need to understand code to answer a question: it returns the call "
        "graph and the source of the relevant functions within a token budget, far cheaper "
        "than reading whole files. Use `slice` for the raw subgraph of one part of a codebase, `scan` for the whole graph, and "
        "`generate_diagram` to write either one as a .drawio file the user can open."
    ),
)

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
_WRITES_DIAGRAM = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)


def _resolve_repo(repo_path: str) -> Path:
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        raise ToolError(f"repo_path is not a directory: {repo_path}")
    return root.resolve()


def _check_slice_args(query: str, max_nodes: int) -> None:
    if not query.strip():
        raise ToolError("query must be non-empty")
    if max_nodes < 1:
        raise ToolError(f"max_nodes must be >= 1, got {max_nodes}")


def _evidence_json(record: EvidenceRecord | EdgeRecord, rel: Relativizer) -> dict[str, Any]:
    return {
        "file": rel(record.file),
        "line": record.line,
        "tier": record.tier,
        "confidence": record.confidence,
    }


def _ir_json(ir: IRGraph, rel: Relativizer) -> dict[str, Any]:
    nodes = [
        {
            "id": rel(node.id),
            "kind": node.evidence[0].kind,
            "evidence": [_evidence_json(e, rel) for e in node.evidence],
        }
        for node in ir.nodes
    ]
    edges = [
        {
            "src": rel(edge.src),
            "dst": rel(edge.dst),
            "relation": edge_relation(edge.evidence),
            "evidence": _evidence_json(edge.evidence, rel),
        }
        for edge in ir.edges
    ]
    return {"nodes": nodes, "edges": edges}


def _verification_json(verification: VerificationResult, rel: Relativizer) -> dict[str, Any]:
    return {
        **_ir_json(verification.ir, rel),
        "dropped_by_verifier": {
            "nodes": len(verification.dropped_nodes),
            "edges": len(verification.dropped_edges),
        },
    }


def _not_ok_json(view: VerifiedView, query: str, rel: Relativizer) -> dict[str, Any]:
    if view.status == "ambiguous":
        return {
            "status": "ambiguous",
            "query": query,
            "candidates": [
                {"label": rel(c.label), "score": round(c.score, 6), "seed_ids": [rel(s) for s in c.seed_ids]}
                for c in view.candidates
            ],
        }
    return {"status": "no_match", "query": query}


def scan_repo(repo_path: str) -> dict[str, Any]:
    root = _resolve_repo(repo_path)
    rel = Relativizer(root)
    view = build_view(root)
    return {
        "repo": root.name,
        **_verification_json(view.verification, rel),
        "unresolved_edges": view.unresolved_edges,
    }


def slice_repo(repo_path: str, query: str, max_nodes: int = 60) -> dict[str, Any]:
    _check_slice_args(query, max_nodes)
    root = _resolve_repo(repo_path)
    rel = Relativizer(root)
    view = build_view(root, query, max_nodes)
    if view.status != "ok":
        return _not_ok_json(view, query, rel)
    return {
        "status": "ok",
        "query": query,
        "seed_ids": [rel(s) for s in view.seed_ids],
        **_verification_json(view.verification, rel),
        "dropped_for_cap": view.dropped_for_cap,
    }


def diagram_repo(
    repo_path: str, query: str | None = None, max_nodes: int = 60, output_path: str | None = None
) -> dict[str, Any]:
    if query is not None:
        _check_slice_args(query, max_nodes)
    root = _resolve_repo(repo_path)
    rel = Relativizer(root)
    out = Path(output_path).expanduser().resolve() if output_path else None
    if out is not None and out.suffix != ".drawio":
        raise ToolError(f"output_path must end in .drawio, got {output_path}")

    result = generate_diagram(root, query, max_nodes, out)
    if result.view.status != "ok":
        return _not_ok_json(result.view, query or "", rel)

    ir = result.view.verification.ir
    return {
        "status": "ok",
        "output_path": str(result.output_path),
        "nodes": len(ir.nodes),
        "edges": len(ir.edges),
        "dropped_by_verifier": {
            "nodes": len(result.view.verification.dropped_nodes),
            "edges": len(result.view.verification.dropped_edges),
        },
    }


def context_repo(
    repo_path: str, query: str, token_budget: int = DEFAULT_TOKEN_BUDGET, max_nodes: int = 60
) -> dict[str, Any]:
    _check_slice_args(query, max_nodes)
    if token_budget < 200:
        raise ToolError(f"token_budget must be >= 200, got {token_budget}")
    root = _resolve_repo(repo_path)
    pack = build_context_pack(root, query, token_budget, max_nodes)
    if pack.status != "ok":
        return {"status": "no_match", "query": query}
    return {
        "status": "ok",
        "query": query,
        "context": pack.text,
        "approx_tokens": pack.pack_tokens,
        "snippets": len(pack.snippets),
        "references_not_shown": len(pack.references),
        "approx_tokens_reading_touched_files_whole": pack.baseline_tokens,
    }


@mcp.tool(annotations=_READ_ONLY)
async def scan(repo_path: str) -> dict[str, Any]:
    """Build the full verified architecture graph of a local repository.

    Runs deterministic extraction (Terraform, docker-compose, Dockerfile, Kubernetes,
    regex rules for SDK/database clients, and Python/TypeScript AST parsing), assembles
    and resolves the graph, then drops anything whose file:line citation doesn't
    resolve on disk. Returns nodes and edges, each with its evidence. Paths are
    relative to the repo root. For a large repo prefer `slice`.

    Args:
        repo_path: Absolute path to the repository root on this machine.
    """
    return await anyio.to_thread.run_sync(scan_repo, repo_path)


@mcp.tool(name="slice", annotations=_READ_ONLY)
async def slice_tool(repo_path: str, query: str, max_nodes: int = 60) -> dict[str, Any]:
    """Return the part of a repository's architecture graph relevant to a question.

    Finds the components best matching `query` (plain English, e.g. "how are uploads
    stored") and expands to their nearby dependencies, capped at `max_nodes`. Returns
    `status`: "ok" with a verified subgraph, "ambiguous" with candidate subsystems, or
    "no_match". To resolve an ambiguous result, call again with one candidate's
    `label` (a node id such as "app/api/user.py:create_user") as the query: an exact
    node id slices on that node directly instead of searching.

    Args:
        repo_path: Absolute path to the repository root on this machine.
        query: Plain-English description of the process or component.
        max_nodes: Upper bound on nodes in the returned subgraph.
    """
    return await anyio.to_thread.run_sync(slice_repo, repo_path, query, max_nodes)


@mcp.tool(name="generate_diagram", annotations=_WRITES_DIAGRAM)
async def generate_diagram_tool(
    repo_path: str, query: str | None = None, max_nodes: int = 60, output_path: str | None = None
) -> dict[str, Any]:
    """Write a draw.io diagram of a repository's verified architecture graph.

    Without `query`, diagrams the whole repo; with `query`, diagrams the same scoped
    subgraph `slice` would return (if the query is ambiguous or matches nothing, no file
    is written and the candidates are returned instead). Every box and arrow in the
    file carries the file:line it was extracted from, shown on hover in draw.io.
    The file opens in draw.io desktop, app.diagrams.net, or the VS Code Draw.io extension.

    Args:
        repo_path: Absolute path to the repository root on this machine.
        query: Optional plain-English description of the part of the system to diagram,
            or an exact node id (e.g. a candidate label from an ambiguous result).
        max_nodes: Upper bound on nodes when `query` is given.
        output_path: Where to write the .drawio file. Defaults to `rudhmap.drawio`
            (or `rudhmap-<query>.drawio`) in the repository root.
    """
    return await anyio.to_thread.run_sync(diagram_repo, repo_path, query, max_nodes, output_path)


@mcp.tool(name="get_context", annotations=_READ_ONLY)
async def get_context_tool(
    repo_path: str, query: str, token_budget: int = DEFAULT_TOKEN_BUDGET, max_nodes: int = 60
) -> dict[str, Any]:
    """Gather the code context needed to answer a question about a repository, cheaply.

    Returns `context`: a markdown pack with the call graph around the code most relevant
    to `query` (each edge cited by file:line) and the source of the closest functions and
    classes, cut to their exact line ranges and ranked to fit `token_budget`. Definitions
    that didn't fit are listed with their file:start-end range, so read only those lines
    if you need them, rather than whole files. If the query matches several unconnected
    areas, all of the top ones are included. Static analysis only: dynamic dispatch and
    languages other than Python/TypeScript may be missing, so fall back to search if the
    pack doesn't cover the question.

    Args:
        repo_path: Absolute path to the repository root on this machine.
        query: The question or the thing to find, in plain English or as identifiers
            (e.g. "how does user signup reach the database", "create_user").
        token_budget: Approximate upper bound on the pack's size in tokens.
        max_nodes: Upper bound on graph nodes considered.
    """
    return await anyio.to_thread.run_sync(context_repo, repo_path, query, token_budget, max_nodes)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
