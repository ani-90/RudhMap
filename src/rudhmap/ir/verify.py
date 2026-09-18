"""The verifier: mechanically enforces spec invariant 3 (every node/edge
carries evidence a program resolves; unresolvable evidence is dropped and
counted). Three checks, each feeding the next:

  1. Schema shape  -- required fields present and in-range.
  2. Referential integrity -- every edge's src/dst names a node that
     survived check 1. Self-loops (src == dst) are explicitly valid --
     genuine recursion (`_flatten_callee`, `_iter_refs`, see README "Known
     limits") produces real, correctly-cited self-loop edges, so there is
     no `src != dst` check anywhere here.
  3. Evidence resolution -- the citation's file must exist on disk and its
     line (if any) must fall within that file's actual line count. A node
     survives with just its bad evidence entries stripped if at least one
     entry still resolves (multi-tier corroboration); an edge has only one
     evidence record, so it is dropped outright if that one fails.

This only proves a citation is *possible* (the file/line exists), not that
its content matches the claim -- that's a stronger check than anything
here attempts. Files are re-read from disk on every call rather than
through `ExtractionCache`: verification must reflect the repo's current
on-disk state (e.g. a file deleted since extraction must fail), and the
cache exists to skip re-parsing, not to answer "does this still exist".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rudhmap.ir.schema import IREdge, IRGraph, IRNode

_VALID_TIERS = {0, 1, 2, 3}


@dataclass
class VerificationResult:
    ir: IRGraph
    dropped_nodes: list[tuple[IRNode, str]] = field(default_factory=list)
    dropped_edges: list[tuple[IREdge, str]] = field(default_factory=list)


def _schema_error(record: Any) -> str | None:
    if not record.file:
        return "file must be non-empty"
    if record.line is not None and record.line <= 0:
        return f"line must be a positive int or None, got {record.line}"
    if not (0.0 <= record.confidence <= 1.0):
        return f"confidence out of range [0.0, 1.0], got {record.confidence}"
    if record.tier not in _VALID_TIERS:
        return f"invalid tier {record.tier}"
    return None


def _resolve_path(file: str, repo_root: Path) -> Path:
    """Extractors already emit `file` as a full path rooted at whatever
    `repo_path` was passed at extraction time (relative-to-cwd or absolute,
    however that was given) -- joining `repo_root` onto it again would
    double the prefix. Try the path verbatim first; only fall back to
    joining `repo_root` for a bare repo-relative filename (the shape a
    hand-built IR, e.g. in tests, is free to use)."""
    direct = Path(file)
    if direct.is_absolute() or direct.exists():
        return direct
    return repo_root / direct


def _line_count(path: Path) -> int:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def _evidence_resolves(record: Any, repo_root: Path) -> str | None:
    path = _resolve_path(record.file, repo_root)
    if not path.is_file():
        return f"file not found: {record.file}"
    if record.line is not None:
        count = _line_count(path)
        if not (1 <= record.line <= count):
            return f"line {record.line} out of range (file has {count} lines): {record.file}"
    return None


def verify_ir(ir: IRGraph, repo_root: str | Path) -> VerificationResult:
    repo_root = Path(repo_root)
    dropped_nodes: list[tuple[IRNode, str]] = []
    dropped_edges: list[tuple[IREdge, str]] = []

    surviving_nodes: list[IRNode] = []
    node_ids: set[str] = set()
    for node in ir.nodes:
        if not node.id:
            dropped_nodes.append((node, "schema: node id must be non-empty"))
            continue

        good_evidence = []
        last_reason = "evidence: no resolvable evidence entries"
        for evidence in node.evidence:
            reason = _schema_error(evidence)
            if reason is None:
                reason = _evidence_resolves(evidence, repo_root)
                if reason is not None:
                    reason = f"evidence: {reason}"
            else:
                reason = f"schema: {reason}"
            if reason is None:
                good_evidence.append(evidence)
            else:
                last_reason = reason

        if not good_evidence:
            dropped_nodes.append((node, last_reason))
            continue

        surviving_nodes.append(IRNode(id=node.id, evidence=good_evidence))
        node_ids.add(node.id)

    surviving_edges: list[IREdge] = []
    for edge in ir.edges:
        if not edge.src or not edge.dst:
            dropped_edges.append((edge, "schema: src/dst must be non-empty"))
            continue
        if edge.src not in node_ids or edge.dst not in node_ids:
            dropped_edges.append((edge, "referential integrity: dangling node reference"))
            continue

        reason = _schema_error(edge.evidence)
        if reason is not None:
            dropped_edges.append((edge, f"schema: {reason}"))
            continue

        reason = _evidence_resolves(edge.evidence, repo_root)
        if reason is not None:
            dropped_edges.append((edge, f"evidence: {reason}"))
            continue

        surviving_edges.append(edge)

    clean_ir = IRGraph(nodes=surviving_nodes, edges=surviving_edges)
    return VerificationResult(ir=clean_ir, dropped_nodes=dropped_nodes, dropped_edges=dropped_edges)
