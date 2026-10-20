from __future__ import annotations

import argparse

from rudhmap.graph.slice import slice_graph
from rudhmap.ir.convert import graph_to_ir
from rudhmap.ir.verify import verify_ir
from rudhmap.pipeline import build_assembly


def scan(repo_path: str) -> None:
    stats = build_assembly(repo_path, verbose=True)
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
    assembly = build_assembly(repo_path, verbose=False).result
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
