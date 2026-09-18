from pathlib import Path

from rudhmap.extract.tier0_iac.dockerfile import parse_dockerfile

FIXTURE = Path(__file__).parent / "fixtures" / "dockerfile"


def test_extracts_single_stage_node():
    nodes, _ = parse_dockerfile(FIXTURE)
    assert len(nodes) == 1
    node = nodes[0]
    assert node.identity.endswith("#stage0")
    assert node.kind == "service"  # "node:18-alpine" matches no datastore/queue/gateway needle


def test_line_points_at_from_instruction():
    nodes, _ = parse_dockerfile(FIXTURE)
    assert nodes[0].line == 1


def test_base_image_and_exposed_ports_in_attrs():
    nodes, _ = parse_dockerfile(FIXTURE)
    assert nodes[0].attrs["base_image"] == "node:18-alpine"
    assert nodes[0].attrs["exposed_ports"] == ["3000"]


def test_single_stage_has_no_edges():
    _, edges = parse_dockerfile(FIXTURE)
    assert edges == []


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_dockerfile(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)


def test_filename_variants_are_recognized(tmp_path):
    # Note: "Dockerfile" vs "dockerfile" is deliberately not covered here --
    # on a case-insensitive filesystem (default on Windows/macOS) they are
    # the same path, so writing both would just overwrite one with the
    # other rather than testing two distinct files.
    (tmp_path / "Dockerfile").write_text("FROM alpine\n")
    (tmp_path / "Dockerfile.dev").write_text("FROM alpine\n")
    (tmp_path / "api.Dockerfile").write_text("FROM alpine\n")
    nodes, _ = parse_dockerfile(tmp_path)
    assert len(nodes) == 3


def test_unrelated_filename_is_ignored(tmp_path):
    (tmp_path / "notes.txt").write_text("FROM alpine\n")
    (tmp_path / "README.md").write_text("FROM alpine\n")
    nodes, _ = parse_dockerfile(tmp_path)
    assert nodes == []


def test_skips_git_and_node_modules_dirs(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "Dockerfile").write_text("FROM alpine\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "Dockerfile").write_text("FROM alpine\n")
    nodes, _ = parse_dockerfile(tmp_path)
    assert nodes == []


def test_skips_venv_dirs(tmp_path):
    for d in ("venv", ".venv", "vendor", "__pycache__", "dist", "build"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "Dockerfile").write_text("FROM alpine\n")
    nodes, _ = parse_dockerfile(tmp_path)
    assert nodes == []


def test_unreadable_file_does_not_crash_scan(tmp_path):
    # A directory that merely looks like a Dockerfile by name but can't be
    # read as text (binary) should be skipped, not raise.
    (tmp_path / "Dockerfile").write_bytes(b"\xff\xfe\x00\x01FROM alpine\xff")
    nodes, edges = parse_dockerfile(tmp_path)
    assert isinstance(nodes, list)
    assert isinstance(edges, list)


def test_no_from_instruction_produces_no_nodes(tmp_path):
    (tmp_path / "Dockerfile").write_text("# just a comment\nENV FOO=bar\n")
    nodes, edges = parse_dockerfile(tmp_path)
    assert nodes == []
    assert edges == []


def test_subtype_is_none_when_base_image_matches_no_needle():
    nodes, _ = parse_dockerfile(FIXTURE)
    assert nodes[0].subtype is None  # "node:18-alpine" matches no datastore/queue/gateway needle


def test_subtype_populated_for_recognized_base_image(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM postgres:16\n")
    nodes, _ = parse_dockerfile(tmp_path)
    assert nodes[0].kind == "datastore"
    assert nodes[0].subtype == "postgres"
