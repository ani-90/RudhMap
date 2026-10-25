from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rudhmap.context import DEFAULT_TOKEN_BUDGET, build_context_pack
from rudhmap.diagram import generate_diagram
from rudhmap.graph.slice import SliceCandidate
from rudhmap.ir.convert import graph_to_ir
from rudhmap.ir.verify import verify_ir
from rudhmap.paths import Relativizer
from rudhmap.pipeline import build_assembly, build_view
from rudhmap.render.drawio import edge_relation


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


def _print_candidates(query: str, candidates: list[SliceCandidate], rel: Relativizer) -> None:
    print(f"ambiguous query {query!r} -- {len(candidates)} candidate subsystems:")
    for c in candidates:
        print(f"  [{c.score:.3f}] {rel(c.label)}  ({len(c.seed_ids)} seed nodes)")
    print("re-run with one of the ids above as the query to slice on it directly")


def slice_cmd(repo_path: str, query: str, max_nodes: int) -> None:
    root = Path(repo_path).resolve()
    rel = Relativizer(root)
    view = build_view(root, query, max_nodes)

    if view.status == "ambiguous":
        _print_candidates(query, view.candidates, rel)
        return
    if view.status == "no_match":
        print(f"no match for query {query!r}")
        return

    verification = view.verification
    print(
        f"slice for {query!r}: seed={[rel(s) for s in view.seed_ids]}, "
        f"{len(verification.ir.nodes)} nodes, {len(verification.ir.edges)} edges "
        f"({view.dropped_for_cap} dropped for cap)"
    )
    for node in verification.ir.nodes:
        print(f"  [node] {rel(node.id)}")
    for edge in verification.ir.edges:
        print(f"  [edge] {rel(edge.src)} -> {rel(edge.dst)}  relation={edge_relation(edge.evidence)}")
    print(
        f"verified IR: {len(verification.dropped_nodes)} nodes dropped, "
        f"{len(verification.dropped_edges)} edges dropped (schema/evidence)"
    )


def diagram_cmd(repo_path: str, query: str | None, max_nodes: int, output: str | None) -> int:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        print(f"not a directory: {repo_path}", file=sys.stderr)
        return 2
    out = Path(output).resolve() if output else None
    try:
        result = generate_diagram(root, query, max_nodes, out)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    view = result.view
    if view.status == "ambiguous":
        print("no diagram written.")
        _print_candidates(query, view.candidates, Relativizer(root))
        return 1
    if view.status == "no_match":
        print(f"no match for query {query!r} -- no diagram written")
        return 1

    verification = view.verification
    print(f"wrote {result.output_path}")
    print(
        f"  {len(verification.ir.nodes)} nodes, {len(verification.ir.edges)} edges "
        f"({len(verification.dropped_nodes)} nodes / {len(verification.dropped_edges)} edges dropped by verifier)"
    )
    print("  open it in draw.io desktop, https://app.diagrams.net, or the VS Code Draw.io extension")
    return 0


def context_cmd(repo_path: str, query: str, budget: int, max_nodes: int) -> int:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        print(f"not a directory: {repo_path}", file=sys.stderr)
        return 2
    pack = build_context_pack(root, query, budget, max_nodes)
    if pack.status != "ok":
        print(f"no match for query {query!r}", file=sys.stderr)
        return 1
    # The pack goes to stdout so it can be piped into a prompt; stats go to stderr.
    sys.stdout.write(pack.text)
    print(
        f"~{pack.pack_tokens} tokens (budget {budget}): {len(pack.snippets)} snippets, "
        f"{len(pack.references)} references, {pack.edges} edges | reading the "
        f"{pack.baseline_files} touched files whole: ~{pack.baseline_tokens} tokens",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="rudhmap")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Structural graph only, no LLM")
    scan_p.add_argument("repo_path")

    slice_p = sub.add_parser("slice", help="Scoped subgraph for a plain-English process name")
    slice_p.add_argument("repo_path")
    slice_p.add_argument("query")
    slice_p.add_argument("--max-nodes", type=int, default=60)

    diagram_p = sub.add_parser("diagram", help="Write a draw.io diagram of the repo, or of a slice with --query")
    diagram_p.add_argument("repo_path")
    diagram_p.add_argument("--query", "-q", help="plain-English question; diagrams only that slice")
    diagram_p.add_argument("--max-nodes", type=int, default=60)
    diagram_p.add_argument(
        "--output", "-o", help="output .drawio path (default: rudhmap[-<query>].drawio in the repo root)"
    )

    context_p = sub.add_parser("context", help="Token-budgeted context pack (call graph + cited source) for a question")
    context_p.add_argument("repo_path")
    context_p.add_argument("query")
    context_p.add_argument("--budget", type=int, default=DEFAULT_TOKEN_BUDGET, help="approximate token budget")
    context_p.add_argument("--max-nodes", type=int, default=60)

    args = parser.parse_args()
    if args.command == "scan":
        scan(args.repo_path)
    elif args.command == "slice":
        slice_cmd(args.repo_path, args.query, args.max_nodes)
    elif args.command == "diagram":
        sys.exit(diagram_cmd(args.repo_path, args.query, args.max_nodes, args.output))
    elif args.command == "context":
        sys.exit(context_cmd(args.repo_path, args.query, args.budget, args.max_nodes))


if __name__ == "__main__":
    main()
