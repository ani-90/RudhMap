from rudhmap.extract.schema import EvidenceRecord
from rudhmap.graph.assemble import assemble_graph
from rudhmap.graph.resolve import resolve_build_context_containment


def _compose_service(identity: str, compose_file: str, build_context: str) -> EvidenceRecord:
    return EvidenceRecord(
        kind="service",
        identity=identity,
        file=compose_file,
        line=2,
        tier=0,
        confidence=1.0,
        attrs={"build_context": build_context},
    )


def _code_node(identity: str, file: str, tier: int = 2) -> EvidenceRecord:
    return EvidenceRecord(
        kind="function",
        identity=identity,
        file=file,
        line=1,
        tier=tier,
        confidence=1.0,
    )


def test_code_under_build_context_gets_linked_to_service():
    service = _compose_service("compose:api", "repo/docker-compose.yml", "./app")
    in_scope = _code_node("repo/app/main.py:handler", "repo/app/main.py")
    result = resolve_build_context_containment(
        assemble_graph([service, in_scope], [])
    )

    assert result.graph.has_edge("compose:api", "repo/app/main.py:handler")
    edge_data = result.graph.get_edge_data("compose:api", "repo/app/main.py:handler")[0]
    assert edge_data["evidence"].attrs["relation"] == "build_context_contains"
    assert edge_data["evidence"].file == "repo/docker-compose.yml"  # cites the compose file, not the code file


def test_code_outside_build_context_is_not_linked():
    service = _compose_service("compose:api", "repo/docker-compose.yml", "./app")
    outside = _code_node("repo/worker/main.py:handler", "repo/worker/main.py")
    result = resolve_build_context_containment(
        assemble_graph([service, outside], [])
    )

    assert not result.graph.has_edge("compose:api", "repo/worker/main.py:handler")


def test_sibling_directory_sharing_a_name_prefix_is_not_falsely_matched():
    """repo/app2/... must not be treated as "under" repo/app -- a naive
    string startswith() would get this wrong, os.path.commonpath must not."""
    service = _compose_service("compose:api", "repo/docker-compose.yml", "./app")
    sibling = _code_node("repo/app2/main.py:handler", "repo/app2/main.py")
    result = resolve_build_context_containment(
        assemble_graph([service, sibling], [])
    )

    assert not result.graph.has_edge("compose:api", "repo/app2/main.py:handler")


def test_tier0_code_node_is_never_linked_by_containment():
    """Containment only makes sense for tiers 1/2 (application code) -- a
    tier 0 node happening to share a file path is not a case this pass
    should touch."""
    service = _compose_service("compose:api", "repo/docker-compose.yml", "./app")
    other_infra = EvidenceRecord(
        kind="resource", identity="aws_instance.web", file="repo/app/main.tf",
        line=1, tier=0, confidence=1.0,
    )
    result = resolve_build_context_containment(
        assemble_graph([service, other_infra], [])
    )

    assert not result.graph.has_edge("compose:api", "aws_instance.web")


def test_service_without_build_context_links_nothing():
    service = EvidenceRecord(
        kind="service", identity="compose:db", file="repo/docker-compose.yml",
        line=8, tier=0, confidence=1.0, attrs={"image": "postgres:16"},
    )
    code = _code_node("repo/app/main.py:handler", "repo/app/main.py")
    result = resolve_build_context_containment(
        assemble_graph([service, code], [])
    )

    assert result.graph.number_of_edges() == 0


def test_dropped_edges_pass_through_unchanged():
    from rudhmap.extract.schema import EdgeRecord

    service = _compose_service("compose:api", "repo/docker-compose.yml", "./app")
    dangling = EdgeRecord(
        src="repo/app/main.py:handler", dst="unscanned", file="repo/app/main.py",
        line=1, tier=2, confidence=1.0, attrs={},
    )
    before = assemble_graph([service], [dangling])
    after = resolve_build_context_containment(before)

    assert after.dropped_edges == before.dropped_edges
