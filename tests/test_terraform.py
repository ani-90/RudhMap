from pathlib import Path

from rudhmap.extract.tier0_iac.terraform import parse_terraform

FIXTURE = Path(__file__).parent / "fixtures" / "terraform"


def test_extracts_all_resource_nodes():
    nodes, _ = parse_terraform(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {
        "aws_s3_bucket.raw_telemetry",
        "aws_lambda_function.normalize",
        "aws_dynamodb_table.events",
        "aws_iam_role.unmapped_kind",
    }


def test_no_literal_quotes_leak_into_identity():
    nodes, _ = parse_terraform(FIXTURE)
    for n in nodes:
        assert '"' not in n.identity


def test_kind_mapping_and_unmapped_fallback():
    nodes, _ = parse_terraform(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["aws_s3_bucket.raw_telemetry"].kind == "datastore"
    assert by_id["aws_lambda_function.normalize"].kind == "service"
    assert by_id["aws_iam_role.unmapped_kind"].kind == "unknown"


def test_line_numbers_point_at_resource_declaration():
    nodes, _ = parse_terraform(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["aws_s3_bucket.raw_telemetry"].line == 1
    assert by_id["aws_lambda_function.normalize"].line == 5
    assert by_id["aws_dynamodb_table.events"].line == 15


def test_extracts_cross_resource_reference_edges():
    _, edges = parse_terraform(FIXTURE)
    pairs = {(e.src, e.dst) for e in edges}
    assert ("aws_lambda_function.normalize", "aws_s3_bucket.raw_telemetry") in pairs
    assert ("aws_lambda_function.normalize", "aws_dynamodb_table.events") in pairs


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_terraform(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)


def test_malformed_file_does_not_crash_scan(tmp_path):
    (tmp_path / "broken.tf").write_text('resource "aws_s3_bucket" "x" {\n  bucket = ')
    nodes, edges = parse_terraform(tmp_path)
    assert nodes == []
    assert edges == []


def test_subtype_populated_for_mapped_resources_and_none_for_unmapped():
    nodes, _ = parse_terraform(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["aws_s3_bucket.raw_telemetry"].subtype == "s3"
    assert by_id["aws_lambda_function.normalize"].subtype == "lambda"
    assert by_id["aws_dynamodb_table.events"].subtype == "dynamodb"
    assert by_id["aws_iam_role.unmapped_kind"].subtype is None
