from pathlib import Path

from rudhmap.extract.tier0_iac.compose import parse_compose

FIXTURE = Path(__file__).parent / "fixtures" / "compose"


def test_extracts_all_services():
    nodes, _ = parse_compose(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {"compose:api", "compose:db", "compose:cache", "compose:worker"}


def test_infers_kind_from_image_name():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:db"].kind == "datastore"
    assert by_id["compose:cache"].kind == "datastore"
    assert by_id["compose:api"].kind == "service"
    assert by_id["compose:worker"].kind == "service"  # no image, build-only


def test_depends_on_becomes_edges():
    _, edges = parse_compose(FIXTURE)
    pairs = {(e.src, e.dst) for e in edges}
    assert ("compose:api", "compose:db") in pairs
    assert ("compose:api", "compose:cache") in pairs


def test_line_numbers_point_at_service_key():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:api"].line == 2
    assert by_id["compose:db"].line == 8
    assert by_id["compose:cache"].line == 11


def test_subtype_populated_from_image_and_none_for_unmatched():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:db"].subtype == "postgres"
    assert by_id["compose:cache"].subtype == "redis"
    assert by_id["compose:api"].subtype is None  # "myorg/api:latest" matches no needle
    assert by_id["compose:worker"].subtype is None  # no image at all


def test_build_context_captured_for_bare_string_form():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:worker"].attrs["build_context"] == "./worker"
    assert "build_context" not in by_id["compose:api"].attrs  # image-only, no build key


def test_build_context_captured_for_mapping_form(tmp_path):
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n"
        "  api:\n"
        "    build:\n"
        "      context: ./app\n"
        "      dockerfile: Dockerfile.api\n"
    )
    nodes, _ = parse_compose(tmp_path)
    assert nodes[0].attrs["build_context"] == "./app"
