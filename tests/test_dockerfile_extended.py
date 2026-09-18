from pathlib import Path

from rudhmap.extract.tier0_iac.dockerfile import parse_dockerfile

FIXTURE = Path(__file__).parent / "fixtures" / "dockerfile_extended"


def test_extracts_one_node_per_named_stage():
    nodes, _ = parse_dockerfile(FIXTURE)
    labels = {n.identity.rsplit("#", 1)[1] for n in nodes}
    assert labels == {"builder", "test", "runtime", "seed_db"}


def test_kind_inferred_from_each_stages_own_base_image():
    nodes, _ = parse_dockerfile(FIXTURE)
    by_label = {n.identity.rsplit("#", 1)[1]: n for n in nodes}
    assert by_label["builder"].kind == "service"  # golang -- no needle match
    assert by_label["runtime"].kind == "service"  # alpine -- no needle match
    assert by_label["seed_db"].kind == "datastore"  # postgres
    # "test" stage's FROM is another stage name ("builder"), not an image;
    # _kind_for_image("builder") matches no needle either, so it also falls
    # back to "service" -- current parser makes no special case here.
    assert by_label["test"].kind == "service"


def test_line_numbers_anchor_at_each_stages_from_instruction():
    nodes, _ = parse_dockerfile(FIXTURE)
    by_label = {n.identity.rsplit("#", 1)[1]: n for n in nodes}
    assert by_label["builder"].line == 2
    assert by_label["test"].line == 9
    assert by_label["runtime"].line == 12
    assert by_label["seed_db"].line == 19


def test_from_referencing_prior_stage_becomes_extends_edge():
    _, edges = parse_dockerfile(FIXTURE)
    extends = {(e.src.rsplit("#", 1)[1], e.dst.rsplit("#", 1)[1]) for e in edges if e.attrs.get("relation") == "extends"}
    assert ("test", "builder") in extends


def test_copy_from_prior_stage_becomes_copies_from_edge():
    _, edges = parse_dockerfile(FIXTURE)
    copies = {(e.src.rsplit("#", 1)[1], e.dst.rsplit("#", 1)[1]) for e in edges if e.attrs.get("relation") == "copies_from"}
    assert ("runtime", "builder") in copies


def test_seed_db_references_no_prior_stage():
    # postgres:16 is a genuine external image, not a stage name -- must not
    # produce an "extends" edge even though it comes after other FROMs.
    _, edges = parse_dockerfile(FIXTURE)
    srcs = {e.src.rsplit("#", 1)[1] for e in edges}
    assert "seed_db" not in srcs


def test_line_continuation_does_not_break_subsequent_parsing():
    # runtime's RUN instruction spans two physical lines via a trailing
    # backslash; EXPOSE on the line after must still be attributed correctly.
    nodes, _ = parse_dockerfile(FIXTURE)
    by_label = {n.identity.rsplit("#", 1)[1]: n for n in nodes}
    assert by_label["runtime"].attrs["exposed_ports"] == ["8080"]


def test_stages_without_expose_have_no_exposed_ports_attr():
    nodes, _ = parse_dockerfile(FIXTURE)
    by_label = {n.identity.rsplit("#", 1)[1]: n for n in nodes}
    assert "exposed_ports" not in by_label["builder"].attrs
    assert "exposed_ports" not in by_label["test"].attrs
    assert "exposed_ports" not in by_label["seed_db"].attrs


def test_comment_only_line_does_not_produce_a_stage():
    nodes, _ = parse_dockerfile(FIXTURE)
    assert not any("builder stage" in n.identity for n in nodes)


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_dockerfile(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)


def test_unnamed_stage_gets_index_based_label(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM golang:1.21 AS builder\nRUN build\n\nFROM alpine:3.19\nCOPY --from=builder /out /out\n"
    )
    nodes, edges = parse_dockerfile(tmp_path)
    labels = {n.identity.rsplit("#", 1)[1] for n in nodes}
    assert labels == {"builder", "stage1"}
    copies = {(e.src.rsplit("#", 1)[1], e.dst.rsplit("#", 1)[1]) for e in edges}
    assert ("stage1", "builder") in copies


def test_copy_from_numeric_stage_index(tmp_path):
    (tmp_path / "Dockerfile").write_text(
        "FROM golang:1.21\nRUN build\n\nFROM alpine:3.19\nCOPY --from=0 /out /out\n"
    )
    _, edges = parse_dockerfile(tmp_path)
    labels = {(e.src.rsplit("#", 1)[1], e.dst.rsplit("#", 1)[1]) for e in edges}
    assert ("stage1", "stage0") in labels
