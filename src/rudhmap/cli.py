from __future__ import annotations

import argparse
from dataclasses import dataclass

from rudhmap.cache import ExtractionCache
from rudhmap.extract.tier0_iac.compose import parse_compose
from rudhmap.extract.tier0_iac.k8s import parse_k8s
from rudhmap.extract.tier0_iac.terraform import parse_terraform
from rudhmap.extract.tier1_rules.engine import parse_tier1_rules
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.extract.tier2_ast.typescript import parse_typescript_ast
from rudhmap.graph.assemble import AssemblyResult, assemble_graph
from rudhmap.graph.resolve import (
    resolve_build_context_containment,
    resolve_cross_file_calls,
    resolve_same_scope_calls,
)
from rudhmap.graph.slice import slice_graph
from rudhmap.ir.convert import graph_to_ir
from rudhmap.ir.verify import verify_ir

EXTRACTORS = [
    ("terraform", parse_terraform),
    ("compose", parse_compose),
    ("k8s", parse_k8s),
    ("tier1", parse_tier1_rules),
    ("python", parse_python_ast),
    ("typescript", parse_typescript_ast),
]

# Tier 0 IaC extractors are cheap (few files, no tree-sitter parsing) and
# aren't wired into the cache yet -- only the two AST parsers and the
# regex-per-source-file tier 1 engine, where re-parsing on every scan is
# actually expensive, opt in.
_CACHEABLE = {"tier1", "python", "typescript"}


@dataclass
class _AssemblyStats:
    result: AssemblyResult
    total_nodes: int
    total_edges: int
    resolved_same_scope: int
    resolved_cross_file: int
    resolved_containment: int


def _build_assembly(repo_path: str, *, verbose: bool) -> _AssemblyStats:
    cache = ExtractionCache(repo_path)

    all_nodes = []
    all_edges = []
    for source_name, extractor in EXTRACTORS:
        if source_name in _CACHEABLE:
            nodes, edges = extractor(repo_path, cache=cache)
        else:
            nodes, edges = extractor(repo_path)
        if verbose:
            for n in nodes:
                print(f"[node:{source_name}] {n.kind:<10} {n.identity:<40} {n.file}:{n.line}")
            for e in edges:
                print(f"[edge:{source_name}] {e.src} -> {e.dst}  {e.file}:{e.line}")
        all_nodes.extend(nodes)
        all_edges.extend(edges)
    cache.flush()

    result = assemble_graph(all_nodes, all_edges)

    before_same_scope = len(result.dropped_edges)
    result = resolve_same_scope_calls(result)
    resolved_same_scope = before_same_scope - len(result.dropped_edges)

    before_cross_file = len(result.dropped_edges)
    result = resolve_cross_file_calls(result)
    resolved_cross_file = before_cross_file - len(result.dropped_edges)

    before_containment_edges = result.graph.number_of_edges()
    result = resolve_build_context_containment(result)
    resolved_containment = result.graph.number_of_edges() - before_containment_edges

    return _AssemblyStats(
        result=result,
        total_nodes=len(all_nodes),
        total_edges=len(all_edges),
        resolved_same_scope=resolved_same_scope,
        resolved_cross_file=resolved_cross_file,
        resolved_containment=resolved_containment,
    )


def scan(repo_path: str) -> None:
    stats = _build_assembly(repo_path, verbose=True)
    result = stats.result

    print(f"\n{stats.total_nodes} nodes, {stats.total_edges} edges (tiers 0-2, no LLM)")
    print(
        f"assembled graph: {result.graph.number_of_nodes()} nodes, "
        f"{result.graph.number_of_edges()} edges, "
        f"{len(result.dropped_edges)} edges dropped (no matching node), "
        f"{stats.resolved_same_scope} resolved via same-scope calls, "
        f"{stats.resolved_cross_file} resolved via cross-file calls, "
        f"{stats.resolved_containment} added via build-context containment"
    )

    verification = verify_ir(graph_to_ir(result.graph), repo_path)
    print(
        f"verified IR: {len(verification.ir.nodes)} nodes, {len(verification.ir.edges)} edges, "
        f"{len(verification.dropped_nodes)} nodes dropped, "
        f"{len(verification.dropped_edges)} edges dropped (schema/evidence)"
    )


def slice_cmd(repo_path: str, query: str, max_nodes: int) -> None:
    assembly = _build_assembly(repo_path, verbose=False).result
    result = slice_graph(assembly, query, max_nodes=max_nodes)

    if result.ambiguous:
        print(f"ambiguous query {query!r} -- {len(result.candidates)} candidate subsystems:")
        for c in result.candidates:
            print(f"  [{c.score:.3f}] {c.label}  ({len(c.seed_ids)} seed nodes)")
        return

    if result.graph is None:
        print(f"no match for query {query!r}")
        return

    print(
        f"slice for {query!r}: seed={result.seed_ids}, "
        f"{result.graph.number_of_nodes()} nodes, {result.graph.number_of_edges()} edges "
        f"({len(result.dropped_for_cap)} dropped for cap)"
    )
    for node_id in sorted(result.graph.nodes):
        print(f"  [node] {node_id}")
    for u, v, data in sorted(result.graph.edges(data=True), key=lambda e: (e[0], e[1])):
        relation = data["evidence"].attrs.get("relation", "")
        print(f"  [edge] {u} -> {v}  relation={relation}")

    verification = verify_ir(graph_to_ir(result.graph), repo_path)
    print(
        f"verified IR: {len(verification.ir.nodes)} nodes, {len(verification.ir.edges)} edges, "
        f"{len(verification.dropped_nodes)} nodes dropped, "
        f"{len(verification.dropped_edges)} edges dropped (schema/evidence)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="rudhmap")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Structural graph only, no LLM")
    scan_p.add_argument("repo_path")

    slice_p = sub.add_parser("slice", help="Scoped subgraph for a plain-English process name")
    slice_p.add_argument("repo_path")
    slice_p.add_argument("query")
    slice_p.add_argument("--max-nodes", type=int, default=60)

    args = parser.parse_args()
    if args.command == "scan":
        scan(args.repo_path)
    elif args.command == "slice":
        slice_cmd(args.repo_path, args.query, args.max_nodes)


if __name__ == "__main__":
    main()
