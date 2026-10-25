"""Context packs: the slice for a question, turned into the smallest text an
LLM needs to answer it -- a call-graph skeleton plus the source of the most
relevant definitions, cut to their exact line ranges and fit to a token
budget. Shared by the CLI's `context` command and the MCP `get_context` tool.

The point is token spend. Without this, an agent answering "how does signup
reach the database?" greps, then reads whole files. A pack gives it the edges
between the functions involved (cheap) and only the bodies of the closest
ones (expensive, so ranked and budgeted); everything that didn't fit is still
listed by `file:start-end` so the agent can read exactly that range on demand.

Ranking is deterministic: seeds first, then by hop distance from a seed in
the slice, then by id. Token counts are an estimate (`estimate_tokens`, ~4
characters per token) -- close enough to budget with and to compare a pack
against reading the same files whole, not a billing-accurate count.

No LLM calls happen here.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from rudhmap.ir.schema import IRGraph, IRNode
from rudhmap.paths import Relativizer
from rudhmap.pipeline import VerifiedView, build_view
from rudhmap.render.drawio import edge_relation

DEFAULT_TOKEN_BUDGET = 6000
# A single huge function shouldn't eat the whole budget; past this it's cut
# and the omitted remainder is cited by line range.
MAX_SNIPPET_LINES = 80

_FENCE_LANG = {".py": "python", ".ts": "ts", ".tsx": "tsx", ".js": "js", ".jsx": "jsx"}


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


@dataclass
class Snippet:
    node_id: str
    kind: str
    file: str
    start: int
    end: int
    hops: int
    text: str
    truncated_at: int | None = None  # last line shown, when cut by MAX_SNIPPET_LINES


@dataclass
class Reference:
    """A slice node shown only as a citation: either it has no source range
    (infra, tier-1 matches) or its body didn't fit the budget."""

    node_id: str
    kind: str
    file: str
    start: int | None
    end: int | None
    hops: int


@dataclass
class ContextPack:
    status: str  # "ok" | "no_match"
    query: str
    token_budget: int
    text: str = ""
    seed_ids: list[str] = field(default_factory=list)
    merged_candidates: list[str] = field(default_factory=list)
    snippets: list[Snippet] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    edges: int = 0
    pack_tokens: int = 0
    # What reading every file the slice touches, whole, would cost.
    baseline_tokens: int = 0
    baseline_files: int = 0
    baseline_breakdown: list[tuple[str, int]] = field(default_factory=list)  # (relative file, tokens)


def _hops_from_seeds(ir: IRGraph, seeds: list[str]) -> dict[str, int]:
    adjacency: dict[str, set[str]] = {node.id: set() for node in ir.nodes}
    for edge in ir.edges:
        adjacency[edge.src].add(edge.dst)
        adjacency[edge.dst].add(edge.src)
    hops = {seed: 0 for seed in seeds if seed in adjacency}
    queue = deque(sorted(hops))
    while queue:
        node_id = queue.popleft()
        for neighbor in sorted(adjacency[node_id]):
            if neighbor not in hops:
                hops[neighbor] = hops[node_id] + 1
                queue.append(neighbor)
    return hops


def _source_range(node: IRNode, nested_starts: list[int]) -> tuple[int, int] | None:
    """The node's own lines, from tier-2 evidence. A class is cut to its
    header (up to its first nested definition) -- its methods are nodes of
    their own and get their own snippets if they rank high enough."""
    for ev in node.evidence:
        end = ev.attrs.get("end_line")
        if ev.tier == 2 and ev.line is not None and isinstance(end, int):
            if ev.kind == "class":
                inner = [s for s in nested_starts if ev.line < s <= end]
                if inner:
                    end = min(inner) - 1
            return ev.line, end
    return None


class _FileCache:
    def __init__(self) -> None:
        self._lines: dict[str, list[str]] = {}

    def lines(self, path: str) -> list[str]:
        if path not in self._lines:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            self._lines[path] = text.splitlines()
        return self._lines[path]


def _render(pack: ContextPack, edge_lines: list[str]) -> str:
    out = [f"# RudhMap context for: {pack.query}"]
    out.append(f"Seeds: {', '.join(pack.seed_ids)}")
    if pack.merged_candidates:
        out.append(
            "The query matched several unconnected areas; all of these were included: "
            + ", ".join(pack.merged_candidates)
        )
    out.append("Every line below is cited from the repo; ids are `file:qualname`.")
    if edge_lines:
        out.append("")
        out.append("## Call graph (caller -> callee [relation @ file:line])")
        out.extend(edge_lines)
    if pack.snippets:
        out.append("")
        out.append("## Source (most relevant first)")
        for s in pack.snippets:
            shown_end = s.truncated_at or s.end
            out.append(f"### {s.node_id} ({s.kind}, {s.file}:{s.start}-{shown_end})")
            lang = _FENCE_LANG.get(Path(s.file).suffix, "")
            out.append(f"```{lang}")
            out.append(s.text)
            out.append("```")
            if s.truncated_at is not None:
                out.append(f"(cut at line {s.truncated_at}; rest is {s.file}:{s.truncated_at + 1}-{s.end})")
    if pack.references:
        out.append("")
        out.append("## Also involved, not shown (read the cited range if needed)")
        for r in pack.references:
            where = r.file if r.start is None else (
                f"{r.file}:{r.start}" if r.end in (None, r.start) else f"{r.file}:{r.start}-{r.end}"
            )
            out.append(f"- {r.node_id} ({r.kind}) {where}")
    return "\n".join(out) + "\n"


def pack_from_view(
    view: VerifiedView, repo_root: Path, query: str, token_budget: int = DEFAULT_TOKEN_BUDGET
) -> ContextPack:
    if view.status != "ok":
        return ContextPack(status="no_match", query=query, token_budget=token_budget)

    rel = Relativizer(repo_root)
    ir = view.verification.ir
    files = _FileCache()
    hops = _hops_from_seeds(ir, view.seed_ids)
    unreachable = len(ir.nodes) + 1

    pack = ContextPack(
        status="ok",
        query=query,
        token_budget=token_budget,
        seed_ids=[rel(s) for s in view.seed_ids],
        edges=len(ir.edges),
    )
    if len(view.seed_ids) > 1 and view.candidates:
        pack.merged_candidates = [rel(s) for s in view.seed_ids]

    # Repeated calls between the same pair collapse to one line citing every site.
    call_sites: dict[tuple[str, str, str, str], list[int]] = {}
    for e in ir.edges:
        key = (rel(e.src), rel(e.dst), edge_relation(e.evidence), rel(e.evidence.file))
        call_sites.setdefault(key, []).append(e.evidence.line or 0)
    edge_lines = [
        f"- {src} -> {dst} [{relation} @ {file}:{','.join(str(n) for n in sorted(lines))}]"
        for (src, dst, relation, file), lines in sorted(call_sites.items())
    ]

    starts_by_file: dict[str, list[int]] = {}
    for node in ir.nodes:
        for ev in node.evidence:
            if ev.line is not None:
                starts_by_file.setdefault(ev.file, []).append(ev.line)

    ranked = sorted(ir.nodes, key=lambda n: (hops.get(n.id, unreachable), n.id))
    # Section headings for snippets and references, plus the fixed preamble.
    used = estimate_tokens(_render(pack, edge_lines)) + 30

    def add_reference(ref: Reference) -> None:
        nonlocal used
        pack.references.append(ref)
        used += estimate_tokens(f"- {ref.node_id} ({ref.kind}) {ref.file}:{ref.start}-{ref.end}")

    for node in ranked:
        ev = node.evidence[0]
        node_hops = hops.get(node.id, unreachable)
        span = _source_range(node, starts_by_file.get(ev.file, []))
        if span is None:
            add_reference(Reference(rel(node.id), ev.kind, rel(ev.file), ev.line, None, node_hops))
            continue
        start, end = span
        shown_end = min(end, start + MAX_SNIPPET_LINES - 1)
        body = "\n".join(files.lines(ev.file)[start - 1 : shown_end])
        snippet = Snippet(
            rel(node.id), ev.kind, rel(ev.file), start, end, node_hops, body,
            truncated_at=shown_end if shown_end < end else None,
        )
        # Header + fence + body + a possible "cut at" line, roughly.
        cost = estimate_tokens(body) + estimate_tokens(snippet.node_id + snippet.file) + 12
        if used + cost <= token_budget:
            pack.snippets.append(snippet)
            used += cost
        else:
            add_reference(Reference(rel(node.id), ev.kind, rel(ev.file), start, end, node_hops))

    # The running estimate above is per-part; the rendered whole is what has to
    # fit, so demote the lowest-ranked snippets until it does.
    pack.text = _render(pack, edge_lines)
    while estimate_tokens(pack.text) > token_budget and pack.snippets:
        s = pack.snippets.pop()
        pack.references.append(Reference(s.node_id, s.kind, s.file, s.start, s.end, s.hops))
        pack.references.sort(key=lambda r: (r.hops, r.node_id))
        pack.text = _render(pack, edge_lines)
    pack.pack_tokens = estimate_tokens(pack.text)

    touched = sorted({ev.file for node in ir.nodes for ev in node.evidence if Path(ev.file).is_file()})
    pack.baseline_breakdown = [(rel(f), estimate_tokens("\n".join(files.lines(f)))) for f in touched]
    pack.baseline_files = len(touched)
    pack.baseline_tokens = sum(tokens for _, tokens in pack.baseline_breakdown)
    return pack


def build_context_pack(
    repo_root: Path, query: str, token_budget: int = DEFAULT_TOKEN_BUDGET, max_nodes: int = 60
) -> ContextPack:
    view = build_view(repo_root, query, max_nodes, merge_ambiguous=True)
    return pack_from_view(view, repo_root, query, token_budget)
