"""The MCP server surface: exposes the tier 0-2 pipeline as MCP tools over
stdio, so any MCP client (Claude Code, VS Code, ...) can ask for a repo's
verified graph or a query-scoped slice of it. No LLM calls happen here --
the tools return exactly what `build_assembly` -> `slice_graph` ->
`verify_ir` produce, reshaped into JSON.

Every path and node id in a tool result is made relative to the scanned
repo root (forward slashes) before it leaves the server, so the same commit
gives the same result regardless of where it's checked out or which OS
scanned it (spec invariant 4) -- the same class of leak the slicer's
basename-only indexing fixed.

Nothing in this module may write to stdout: under the stdio transport,
stdout *is* the protocol stream. `build_assembly` is always called with
`verbose=False` for that reason.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.graph.slice import slice_graph
from rudhmap.ir.convert import graph_to_ir
from rudhmap.ir.schema import IRGraph
from rudhmap.ir.verify import VerificationResult, verify_ir
from rudhmap.pipeline import build_assembly

mcp = MCPServer(
    name="rudhmap",
    instructions=(
        "RudhMap builds an evidence-cited architecture graph of a local code repository. "
        "Every node and edge it returns cites the file:line that proves it, and anything "
        "whose citation doesn't resolve on disk has already been dropped. Use `slice` to "
        "answer a question about one part of a codebase; use `scan` for the whole graph."
    ),
)

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)


class _Relativizer:
    def __init__(self, root: Path):
        self._prefix = str(root) + os.sep

    def __call__(self, value: str) -> str:
        if value.startswith(self._prefix):
            value = value[len(self._prefix) :]
        return value.replace("\\", "/")


def _resolve_repo(repo_path: str) -> Path:
    root = Path(repo_path).expanduser()
    if not root.is_dir():
        raise ToolError(f"repo_path is not a directory: {repo_path}")
    return root.resolve()


def _evidence_json(record: EvidenceRecord | EdgeRecord, rel: _Relativizer) -> dict[str, Any]:
    return {
        "file": rel(record.file),
        "line": record.line,
        "tier": record.tier,
        "confidence": record.confidence,
    }


def _relation(edge: EdgeRecord) -> str:
    """Tier 0 and resolver edges name their relation explicitly; tier 2 edges
    don't, and are either imports (`kind: "import"`) or calls."""
    if "relation" in edge.attrs:
        return edge.attrs["relation"]
    return "imports" if edge.attrs.get("kind") == "import" else "calls"


def _ir_json(ir: IRGraph, rel: _Relativizer) -> dict[str, Any]:
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
            "relation": _relation(edge.evidence),
            "evidence": _evidence_json(edge.evidence, rel),
        }
        for edge in ir.edges
    ]
    return {"nodes": nodes, "edges": edges}


def _verification_json(verification: VerificationResult, rel: _Relativizer) -> dict[str, Any]:
    return {
        **_ir_json(verification.ir, rel),
        "dropped_by_verifier": {
            "nodes": len(verification.dropped_nodes),
            "edges": len(verification.dropped_edges),
        },
    }


def scan_repo(repo_path: str) -> dict[str, Any]:
    root = _resolve_repo(repo_path)
    rel = _Relativizer(root)
    stats = build_assembly(str(root), verbose=False)
    verification = verify_ir(graph_to_ir(stats.result.graph), root)
    return {
        "repo": root.name,
        **_verification_json(verification, rel),
        "unresolved_edges": len(stats.result.dropped_edges),
    }


def slice_repo(repo_path: str, query: str, max_nodes: int = 60) -> dict[str, Any]:
    if not query.strip():
        raise ToolError("query must be non-empty")
    if max_nodes < 1:
        raise ToolError(f"max_nodes must be >= 1, got {max_nodes}")

    root = _resolve_repo(repo_path)
    rel = _Relativizer(root)
    assembly = build_assembly(str(root), verbose=False).result
    result = slice_graph(assembly, query, max_nodes=max_nodes)

    if result.ambiguous:
        return {
            "status": "ambiguous",
            "query": query,
            "candidates": [
                {"label": rel(c.label), "score": round(c.score, 6), "seed_ids": [rel(s) for s in c.seed_ids]}
                for c in result.candidates
            ],
        }
    if result.graph is None:
        return {"status": "no_match", "query": query}

    verification = verify_ir(graph_to_ir(result.graph), root)
    return {
        "status": "ok",
        "query": query,
        "seed_ids": [rel(s) for s in result.seed_ids],
        **_verification_json(verification, rel),
        "dropped_for_cap": len(result.dropped_for_cap),
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
    `status`: "ok" with a verified subgraph, "ambiguous" with candidate subsystems to
    re-ask about more specifically, or "no_match".

    Args:
        repo_path: Absolute path to the repository root on this machine.
        query: Plain-English description of the process or component.
        max_nodes: Upper bound on nodes in the returned subgraph.
    """
    return await anyio.to_thread.run_sync(slice_repo, repo_path, query, max_nodes)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
