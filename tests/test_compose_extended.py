from pathlib import Path

from rudhmap.extract.tier0_iac.compose import parse_compose

FIXTURE = Path(__file__).parent / "fixtures" / "compose_extended"


def test_extracts_all_services():
    nodes, _ = parse_compose(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {
        "compose:web",
        "compose:api",
        "compose:queue",
        "compose:search-index",
        "compose:scratch",
    }


def test_dict_form_depends_on_becomes_edges():
    # web's depends_on uses the long "condition:" mapping syntax rather than
    # a plain list -- _normalize_depends_on must still resolve it to a dep name.
    _, edges = parse_compose(FIXTURE)
    pairs = {(e.src, e.dst) for e in edges}
    assert ("compose:web", "compose:api") in pairs


def test_list_form_depends_on_becomes_edges():
    _, edges = parse_compose(FIXTURE)
    pairs = {(e.src, e.dst) for e in edges}
    assert ("compose:api", "compose:queue") in pairs
    assert ("compose:api", "compose:search-index") in pairs


def test_image_kind_matching_is_case_insensitive():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:queue"].kind == "queue"  # "RABBITMQ" uppercase in image


def test_image_kind_substring_match_for_search_engine():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:search-index"].kind == "datastore"  # opensearch


def test_service_with_only_build_has_no_image_attr_and_service_kind():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    scratch = by_id["compose:scratch"]
    assert scratch.kind == "service"
    assert "image" not in scratch.attrs


def test_dashed_service_name_line_anchor():
    nodes, _ = parse_compose(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:search-index"].line == 17
    assert by_id["compose:queue"].line == 14
    assert by_id["compose:scratch"].line == 20


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_compose(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)


def test_alternate_filenames_are_recognized(tmp_path):
    (tmp_path / "compose.yaml").write_text("services:\n  only:\n    image: alpine\n")
    nodes, _ = parse_compose(tmp_path)
    assert {n.identity for n in nodes} == {"compose:only"}


def test_dated_docker_compose_variant_filename_is_recognized(tmp_path):
    (tmp_path / "docker-compose.prod.yaml").write_text(
        "services:\n  prod-svc:\n    image: alpine\n"
    )
    nodes, _ = parse_compose(tmp_path)
    assert {n.identity for n in nodes} == {"compose:prod-svc"}


def test_unrelated_yaml_filename_is_ignored(tmp_path):
    (tmp_path / "values.yaml").write_text("services:\n  ignored:\n    image: alpine\n")
    nodes, _ = parse_compose(tmp_path)
    assert nodes == []


def test_top_level_list_instead_of_mapping_is_skipped(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("- not\n- a\n- mapping\n")
    nodes, edges = parse_compose(tmp_path)
    assert nodes == []
    assert edges == []


def test_missing_services_key_is_skipped(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("version: '3'\nnetworks:\n  default: {}\n")
    nodes, _ = parse_compose(tmp_path)
    assert nodes == []


def test_malformed_yaml_does_not_crash_scan(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("services:\n  broken: [unterminated\n")
    nodes, edges = parse_compose(tmp_path)
    assert nodes == []
    assert edges == []


def test_skips_git_and_node_modules_dirs(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "docker-compose.yml").write_text(
        "services:\n  hidden:\n    image: alpine\n"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "docker-compose.yml").write_text(
        "services:\n  vendored:\n    image: alpine\n"
    )
    nodes, _ = parse_compose(tmp_path)
    assert nodes == []


def test_skips_venv_dirs(tmp_path):
    """Regression: a docker-compose.yaml bundled inside a third-party pip
    package under .venv must never be scanned as if it were the repo's own
    infrastructure -- see e.g. langsmith's cli/docker-compose.yaml."""
    for d in ("venv", ".venv", "vendor", "__pycache__", "dist", "build"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "docker-compose.yml").write_text(
            "services:\n  bundled:\n    image: alpine\n"
        )
    nodes, _ = parse_compose(tmp_path)
    assert nodes == []


def test_service_with_null_config_defaults_to_service_kind(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("services:\n  empty:\n")
    nodes, _ = parse_compose(tmp_path)
    by_id = {n.identity: n for n in nodes}
    assert by_id["compose:empty"].kind == "service"
    assert by_id["compose:empty"].attrs == {}
