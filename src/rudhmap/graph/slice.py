"""Slicing: turn the whole-repo graph into a small, relevant subgraph for a
plain-English query. See rudhmap spec Part II, Stage 3.

Four steps, each deterministic:
  1. Seed   -- BM25 over per-node text built from evidence (identity, kind,
               subtype, attrs). No embeddings, no vector DB, no API call.
  2. Expand -- bounded weighted traversal from the seed, both directions.
               Infra nodes (any tier-0 evidence) are admitted regardless of
               accumulated cost, since they're the point of an architecture
               diagram -- but they don't act as a free teleport for their own
               neighbors, or a shared infra node would silently pull in every
               unrelated service that references it (the documented
               monorepo-bleed failure mode).
  3. Cap    -- hard node limit (default 60). Seeds and infra nodes are
               protected; the rest is dropped farthest-cost-first, tie-broken
               by identity, so the drop order is reproducible.
  4. Ambiguity -- if the top BM25 candidates fall into more than one
               disconnected part of the graph with comparably strong scores,
               return candidates instead of silently picking one.

The returned subgraph is `assembly.graph.subgraph(kept_ids).copy()` --
NetworkX's induced-subgraph-then-copy, which is lossless: every kept node/edge
keeps its original `evidence` attribute untouched. Nothing here ever adds a
node the stage-2 graph didn't already have (spec invariant 5).
"""
from __future__ import annotations

import heapq
import re
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
from rank_bm25 import BM25Okapi

from rudhmap.graph.assemble import AssemblyResult

MAX_HOP_BUDGET = 3.0
_STRONG_RELATIONS = {"routes_to", "depends_on", "build_context_contains"}
_AMBIGUITY_TOP_N = 10
_AMBIGUITY_SCORE_RATIO = 0.5

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class SliceCandidate:
    label: str
    seed_ids: list[str]
    score: float


@dataclass
class SliceResult:
    graph: nx.MultiDiGraph | None
    seed_ids: list[str] = field(default_factory=list)
    dropped_for_cap: list[str] = field(default_factory=list)
    ambiguous: bool = False
    candidates: list[SliceCandidate] = field(default_factory=list)
    query: str = ""


def _node_text_blob(identity: str, evidence: list) -> str:
    """Deliberately excludes directory ancestry. A node's `identity` is
    often `{absolute file path}:{qualname}` -- if the full identity were
    indexed verbatim, every node in a repo checked out under a path like
    `.../Knowledge-News-App/...` would spuriously share the token "news"
    with every query mentioning it, since that word came from wherever the
    repo happens to be cloned on disk, not from any code the node actually
    represents. Worse, it would make search results depend on the absolute
    checkout path, which has nothing to do with the commit being scanned.
    Only the file's own basename (still real signal -- `qdrant.py` is
    meaningful) and the identity's qualname suffix (the part after the file
    prefix) are indexed; parent directories are dropped."""
    parts = []
    for ev in evidence:
        parts.append(Path(ev.file).name)
        qualname = identity[len(ev.file) :].lstrip(":") if identity.startswith(ev.file) else identity
        parts.append(qualname)
        parts.append(ev.kind)
        if ev.subtype:
            parts.append(ev.subtype)
        for key in sorted(ev.attrs):
            val = ev.attrs[key]
            if isinstance(val, (str, int, float)):
                parts.append(f"{key}:{val}")
    return " ".join(parts)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _build_corpus(graph: nx.MultiDiGraph) -> tuple[list[str], list[list[str]]]:
    node_ids = sorted(graph.nodes)
    blobs = [
        _tokenize(_node_text_blob(node_id, graph.nodes[node_id]["evidence"]))
        for node_id in node_ids
    ]
    return node_ids, blobs


def _bm25_scores(node_ids: list[str], blobs: list[list[str]], query: str) -> list[tuple[str, float]]:
    if not node_ids:
        return []
    bm25 = BM25Okapi(blobs)
    scores = bm25.get_scores(_tokenize(query))
    scored = list(zip(node_ids, scores))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored


def _relevant_ranked(
    node_ids: list[str], blobs: list[list[str]], query: str
) -> list[tuple[str, float]]:
    """BM25-ranked nodes, restricted to ones that actually share at least one
    token with the query. BM25's score is only meaningful as a *ranking*
    signal here, not as a relevance threshold: rank_bm25's IDF formula
    degenerates to exactly 0 (or goes negative) whenever a query term
    appears in roughly half or more of a small corpus, which is a routine
    occurrence for a node graph, not evidence the term didn't match. So
    "did this node match at all" is decided by literal token overlap, and
    BM25 score is used only to order the nodes that already passed that
    test."""
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []
    scored = _bm25_scores(node_ids, blobs, query)
    blob_by_id = dict(zip(node_ids, blobs))
    return [
        (node_id, score)
        for node_id, score in scored
        if query_tokens & set(blob_by_id[node_id])
    ]


def _is_infra(graph: nx.MultiDiGraph, node_id: str) -> bool:
    return any(ev.tier == 0 for ev in graph.nodes[node_id]["evidence"])


def _edge_weight(graph: nx.MultiDiGraph, u: str, v: str, key) -> float:
    edge_record = graph[u][v][key]["evidence"]
    relation = edge_record.attrs.get("relation")
    if relation in _STRONG_RELATIONS:
        return 0.5
    return 1.0


def _detect_ambiguity(
    graph: nx.MultiDiGraph, relevant_ranked: list[tuple[str, float]]
) -> list[SliceCandidate] | None:
    """Group the top relevant candidates by which weakly-connected component
    of the graph they fall in. If they span >=2 components with comparably
    strong scores, the query is ambiguous between distinct subsystems rather
    than pointing at one clear target -- return candidates instead of
    guessing which one was meant.

    The score-ratio dominance check only applies when the top cluster's
    score is meaningfully positive. On a real, healthily-sized corpus BM25
    scores are ordinary positive numbers and the ratio is a real "is the top
    match a clear winner" signal. But rank_bm25's IDF formula legitimately
    produces a score of exactly 0, or negative, on a small/degenerate corpus
    (see _relevant_ranked's docstring) -- there, magnitude comparison isn't
    meaningful, so any node sharing the top cluster's token-overlap rank
    within the top N is treated as a live competing interpretation rather
    than silently dismissed by a ratio comparison that has no real signal
    to compare."""
    top_candidates = relevant_ranked[:_AMBIGUITY_TOP_N]
    if len(top_candidates) < 2:
        return None

    undirected = graph.to_undirected(as_view=True)
    component_of: dict[str, int] = {}
    for i, component in enumerate(nx.connected_components(undirected)):
        for node_id in component:
            component_of[node_id] = i

    clusters: dict[int, list[tuple[str, float]]] = {}
    for node_id, score in top_candidates:
        comp = component_of[node_id]
        clusters.setdefault(comp, []).append((node_id, score))

    if len(clusters) < 2:
        return None

    cluster_best_scores = sorted((max(s for _, s in items) for items in clusters.values()), reverse=True)
    top_score, second_score = cluster_best_scores[0], cluster_best_scores[1]
    if top_score > 0 and second_score < _AMBIGUITY_SCORE_RATIO * top_score:
        return None

    candidates = []
    for items in clusters.values():
        items_sorted = sorted(items, key=lambda kv: kv[0])
        best_label, best_score = max(items, key=lambda kv: (kv[1], kv[0]))
        candidates.append(
            SliceCandidate(
                label=best_label,
                seed_ids=[node_id for node_id, _ in items_sorted],
                score=best_score,
            )
        )
    candidates.sort(key=lambda c: (-c.score, c.label))
    return candidates


def _expand(graph: nx.MultiDiGraph, seeds: list[str]) -> dict[str, float]:
    visited: dict[str, float] = {seed: 0.0 for seed in seeds}
    frontier: list[tuple[float, str]] = [(0.0, seed) for seed in seeds]
    heapq.heapify(frontier)

    while frontier:
        cost, node_id = heapq.heappop(frontier)
        if cost > visited.get(node_id, float("inf")):
            continue

        neighbors = []
        for _, v, key in graph.out_edges(node_id, keys=True):
            neighbors.append((v, _edge_weight(graph, node_id, v, key)))
        for u, _, key in graph.in_edges(node_id, keys=True):
            neighbors.append((u, _edge_weight(graph, u, node_id, key)))

        for neighbor, weight in neighbors:
            new_cost = cost + weight
            neighbor_is_infra = _is_infra(graph, neighbor)
            if not neighbor_is_infra and new_cost > MAX_HOP_BUDGET:
                continue  # not admitted -- neither kept nor expanded from
            if neighbor_is_infra:
                new_cost = min(new_cost, MAX_HOP_BUDGET)
            if new_cost < visited.get(neighbor, float("inf")):
                visited[neighbor] = new_cost
                heapq.heappush(frontier, (new_cost, neighbor))

    return visited


def _apply_cap(
    graph: nx.MultiDiGraph, visited: dict[str, float], seeds: set[str], max_nodes: int
) -> tuple[set[str], list[str]]:
    if len(visited) <= max_nodes:
        return set(visited), []

    ranked = sorted(
        visited.items(),
        key=lambda kv: (
            kv[0] not in seeds,
            not _is_infra(graph, kv[0]),
            kv[1],
            kv[0],
        ),
    )
    kept = {node_id for node_id, _ in ranked[:max_nodes]}
    dropped = sorted(node_id for node_id, _ in ranked[max_nodes:])
    return kept, dropped


def slice_graph(assembly: AssemblyResult, query: str, max_nodes: int = 60) -> SliceResult:
    graph = assembly.graph
    node_ids, blobs = _build_corpus(graph)
    relevant_ranked = _relevant_ranked(node_ids, blobs, query)

    if not relevant_ranked:
        return SliceResult(graph=None, query=query)

    candidates = _detect_ambiguity(graph, relevant_ranked)
    if candidates is not None:
        return SliceResult(graph=None, ambiguous=True, candidates=candidates, query=query)

    seeds = [relevant_ranked[0][0]]
    visited = _expand(graph, seeds)
    kept, dropped = _apply_cap(graph, visited, set(seeds), max_nodes)

    subgraph = graph.subgraph(kept).copy()
    return SliceResult(
        graph=subgraph,
        seed_ids=seeds,
        dropped_for_cap=dropped,
        query=query,
    )
