"""The shared tier 0-2 extraction + assembly + identity-resolution pipeline.
Both the CLI and the MCP server build their graphs through `build_assembly`,
so the two surfaces can never disagree about what a repo's graph is.
"""
from __future__ import annotations

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
class AssemblyStats:
    result: AssemblyResult
    total_nodes: int
    total_edges: int
    resolved_same_scope: int
    resolved_cross_file: int
    resolved_containment: int


def build_assembly(repo_path: str, *, verbose: bool) -> AssemblyStats:
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

    return AssemblyStats(
        result=result,
        total_nodes=len(all_nodes),
        total_edges=len(all_edges),
        resolved_same_scope=resolved_same_scope,
        resolved_cross_file=resolved_cross_file,
        resolved_containment=resolved_containment,
    )
