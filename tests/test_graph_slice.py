from pathlib import Path

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.graph.assemble import assemble_graph
from rudhmap.graph.resolve import resolve_same_scope_calls
from rudhmap.graph.slice import slice_graph

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def _node(identity: str, **kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=identity,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        subtype=kwargs.pop("subtype", None),
        attrs=kwargs.pop("attrs", {}),
    )


def _edge(src: str, dst: str, **kwargs) -> EdgeRecord:
    return EdgeRecord(
        src=src,
        dst=dst,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        attrs=kwargs.pop("attrs", {}),
    )


def test_bm25_picks_the_node_whose_text_actually_matches_the_query():
    nodes = [
        _node("a", attrs={"name": "generic_handler"}),
        _node("b", attrs={"name": "generic_service"}),
        _node("telemetry_ingest", attrs={"name": "telemetry_ingest", "qualname": "telemetry_ingest"}),
    ]
    assembly = assemble_graph(nodes, [])

    result = slice_graph(assembly, "telemetry ingest", max_nodes=60)

    assert result.seed_ids == ["telemetry_ingest"]


def test_bm25_exact_score_tie_breaks_by_identity_deterministically():
    # connected (not two disjoint components) so this isolates the tie-break
    # behavior specifically, rather than tripping ambiguity detection --
    # two disconnected, equally-scoring nodes is a real ambiguous case,
    # covered separately by test_ambiguous_query_returns_candidates_instead_of_guessing.
    nodes = [
        _node("z_node", attrs={"name": "shared"}),
        _node("a_node", attrs={"name": "shared"}),
    ]
    edges = [_edge("z_node", "a_node")]
    assembly = assemble_graph(nodes, edges)

    result1 = slice_graph(assembly, "shared", max_nodes=60)
    result2 = slice_graph(assembly, "shared", max_nodes=60)

    assert result1.seed_ids == ["a_node"]
    assert result1.seed_ids == result2.seed_ids


def test_expansion_respects_edge_weight_routes_to_reaches_further_than_call_chain():
    # seed -> a (routes_to, weight 0.5) -> b (routes_to, weight 0.5) -> c (routes_to, weight 0.5)
    #   cumulative cost to c = 1.5, well within MAX_HOP_BUDGET (3.0)
    # seed2 -> x (call, weight 1.0) -> y (call, weight 1.0) -> z (call, weight 1.0) -> w (call, weight 1.0)
    #   cumulative cost to w = 4.0, exceeds MAX_HOP_BUDGET (3.0)
    nodes = [
        _node("seed", attrs={"name": "seed"}),
        _node("a"), _node("b"), _node("c"),
    ]
    edges = [
        _edge("seed", "a", tier=0, attrs={"relation": "routes_to"}),
        _edge("a", "b", tier=0, attrs={"relation": "routes_to"}),
        _edge("b", "c", tier=0, attrs={"relation": "routes_to"}),
    ]
    assembly = assemble_graph(nodes, edges)

    result = slice_graph(assembly, "seed", max_nodes=60)

    assert "c" in result.graph.nodes


def test_infra_node_beyond_hop_budget_is_still_included():
    # a chain of 5 tier-2 call edges (weight 1.0 each) exceeds MAX_HOP_BUDGET (3.0)
    # at the far end: one tier-2 code node (should be excluded) and one tier-0
    # infra node (should be included regardless of distance).
    #
    # The chain is exactly MAX_HOP_BUDGET (3) long, so n2 sits right at the
    # budget boundary -- reachable by ordinary weighted traversal. far_code
    # and far_infra both hang one hop past that boundary (cost 4, over
    # budget): far_code is ordinary code and must be excluded, far_infra is
    # infra and must be included despite being over budget. (A chain of
    # *non-infra* nodes beyond budget is never traversed at all -- the infra
    # exemption applies to an infra node's own admission, not to tunneling
    # through ordinary code past the budget to find one further out.)
    nodes = [_node("seed", attrs={"name": "seed"})]
    chain_ids = [f"n{i}" for i in range(3)]
    for cid in chain_ids:
        nodes.append(_node(cid))
    nodes.append(_node("far_code", tier=2))
    nodes.append(_node("far_infra", tier=0))

    edges = []
    prev = "seed"
    for cid in chain_ids:
        edges.append(_edge(prev, cid))
        prev = cid
    edges.append(_edge(prev, "far_code"))
    edges.append(_edge(prev, "far_infra", tier=0))

    assembly = assemble_graph(nodes, edges)
    result = slice_graph(assembly, "seed", max_nodes=60)

    assert "far_infra" in result.graph.nodes
    assert "far_code" not in result.graph.nodes


def test_infra_does_not_teleport_its_neighbors_in_for_free():
    # seed -> (budget-length chain) -> infra_hub (1 hop past budget,
    # included via the infra exemption) -> unrelated_service (1 more hop
    # past that): must stay excluded -- the hub's own any-depth exemption
    # must not extend to its neighbors, or a shared infra node would
    # silently pull in everything that references it.
    nodes = [_node("seed", attrs={"name": "seed"})]
    chain_ids = [f"n{i}" for i in range(3)]
    for cid in chain_ids:
        nodes.append(_node(cid))
    nodes.append(_node("infra_hub", tier=0))
    nodes.append(_node("unrelated_service", tier=2))

    edges = []
    prev = "seed"
    for cid in chain_ids:
        edges.append(_edge(prev, cid))
        prev = cid
    edges.append(_edge(prev, "infra_hub", tier=0))
    edges.append(_edge("infra_hub", "unrelated_service"))

    assembly = assemble_graph(nodes, edges)
    result = slice_graph(assembly, "seed", max_nodes=60)

    assert "infra_hub" in result.graph.nodes
    assert "unrelated_service" not in result.graph.nodes


def test_cap_drops_farthest_nodes_first_deterministically():
    nodes = [_node("seed", attrs={"name": "seed"})]
    edges = []
    # a star of 10 one-hop neighbors, all equally close -- with max_nodes=5,
    # keep the seed + 4 lowest-identity neighbors, drop the rest.
    for i in range(10):
        nid = f"leaf{i}"
        nodes.append(_node(nid))
        edges.append(_edge("seed", nid))

    assembly = assemble_graph(nodes, edges)
    result = slice_graph(assembly, "seed", max_nodes=5)

    assert result.graph.number_of_nodes() == 5
    assert "seed" in result.graph.nodes
    assert len(result.dropped_for_cap) == 6
    assert result.dropped_for_cap == sorted(result.dropped_for_cap)
    kept_leaves = sorted(n for n in result.graph.nodes if n != "seed")
    assert kept_leaves == ["leaf0", "leaf1", "leaf2", "leaf3"]


def test_ambiguous_query_returns_candidates_instead_of_guessing():
    # two disjoint components, each with a node matching one half of the query
    nodes = [
        _node("svc_a_login", attrs={"name": "login"}),
        _node("svc_a_helper", attrs={"name": "helper"}),
        _node("svc_b_login", attrs={"name": "login"}),
        _node("svc_b_helper", attrs={"name": "helper"}),
    ]
    edges = [
        _edge("svc_a_login", "svc_a_helper"),
        _edge("svc_b_login", "svc_b_helper"),
    ]
    assembly = assemble_graph(nodes, edges)

    result = slice_graph(assembly, "login", max_nodes=60)

    assert result.ambiguous is True
    assert result.graph is None
    assert len(result.candidates) == 2
    labels = {c.label for c in result.candidates}
    assert labels == {"svc_a_login", "svc_b_login"}


def test_monorepo_slicing_does_not_bleed_across_disconnected_services():
    # service A and service B share no direct edges -- only a shared infra
    # node connects them, sitting past the hop budget (so the infra
    # exemption is actually exercised, not incidentally within normal
    # budget). Seeding in A must not pull in B's private nodes.
    nodes = [
        _node("a_entry", attrs={"name": "entry_alpha"}),
        _node("a_private"),
        _node("a1"), _node("a2"),
        _node("shared_infra", tier=0),
        _node("b_private"),
    ]
    edges = [
        _edge("a_entry", "a_private"),
        _edge("a_entry", "a1"),
        _edge("a1", "a2"),
        _edge("a2", "shared_infra", tier=0),
        _edge("shared_infra", "b_private", tier=0),
    ]
    assembly = assemble_graph(nodes, edges)

    result = slice_graph(assembly, "entry_alpha", max_nodes=60)

    assert "a_entry" in result.graph.nodes
    assert "a_private" in result.graph.nodes
    assert "shared_infra" in result.graph.nodes
    assert "b_private" not in result.graph.nodes


def test_dominant_match_is_not_flagged_ambiguous_by_weaker_unrelated_matches():
    # a healthy-sized corpus (not a 2-3 node synthetic case) so BM25 scores
    # are ordinary positive numbers, not the degenerate 0/negative case a
    # tiny corpus produces. One node matches the full query strongly; a
    # node in a disconnected component only shares one of three query
    # tokens and should not be enough to force an ambiguous result.
    nodes = [
        _node("strong_match", attrs={"name": "unique_target_alpha_beta"}),
        _node("strong_neighbor"),
        _node("weak_partial_match", attrs={"name": "alpha_only"}),
        _node("weak_neighbor"),
    ]
    filler = [_node(f"filler{i}", attrs={"name": f"unrelated_thing_{i}"}) for i in range(8)]
    nodes += filler

    edges = [_edge("strong_match", "strong_neighbor"), _edge("weak_partial_match", "weak_neighbor")]
    assembly = assemble_graph(nodes, edges)

    result = slice_graph(assembly, "unique_target_alpha_beta", max_nodes=60)

    assert result.ambiguous is False
    assert result.graph is not None
    assert result.seed_ids == ["strong_match"]


def test_parent_directory_names_do_not_leak_into_search_relevance():
    # A repo checked out under a folder whose name happens to share a word
    # with the query (e.g. cloned as ".../Knowledge-News-App/...") must not
    # make every node in the repo spuriously match that word -- only the
    # file's own basename and qualname are searchable text, not the full
    # absolute path's directory ancestry.
    repo_file = "C:\\Users\\dev\\Knowledge-News-App\\app\\config.py"
    node = _node(
        f"{repo_file}:Settings",
        file=repo_file,
        kind="class",
        attrs={"name": "Settings", "qualname": "Settings"},
    )
    assembly = assemble_graph([node], [])

    result = slice_graph(assembly, "chat about the news", max_nodes=60)

    assert result.graph is None
    assert result.ambiguous is False


def test_file_basename_is_still_searchable():
    # the fix for the above must not throw out the basename itself --
    # "qdrant.py" is real, meaningful signal, unlike its parent directories.
    repo_file = "C:\\Users\\dev\\Knowledge-News-App\\app\\db\\qdrant.py"
    node = _node(
        f"{repo_file}:search_similar",
        file=repo_file,
        attrs={"name": "search_similar", "qualname": "search_similar"},
    )
    assembly = assemble_graph([node], [])

    result = slice_graph(assembly, "qdrant", max_nodes=60)

    assert result.seed_ids == [f"{repo_file}:search_similar"]


def test_no_match_returns_no_graph_rather_than_guessing():
    nodes = [_node("a", attrs={"name": "alpha"})]
    assembly = assemble_graph(nodes, [])

    result = slice_graph(assembly, "completely_unrelated_zzz_query", max_nodes=60)

    assert result.graph is None
    assert result.ambiguous is False


def test_real_fixture_integration_seed_and_cap_respected():
    nodes, edges = parse_python_ast(FIXTURE)
    assembly = resolve_same_scope_calls(assemble_graph(nodes, edges))

    result = slice_graph(assembly, "do_local_work", max_nodes=60)

    assert result.graph is not None
    assert result.graph.number_of_nodes() <= 60
    assert result.graph.number_of_nodes() > 0
    assert any("do_local_work" in seed for seed in result.seed_ids)
