from pathlib import Path

from rudhmap.extract.tier0_iac.terraform import parse_terraform

FIXTURE = Path(__file__).parent / "fixtures" / "terraform_extended"


def test_extracts_all_resource_nodes_including_unmapped():
    nodes, _ = parse_terraform(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {
        "aws_sqs_queue.events_queue",
        "aws_lambda_function.consumer",
        "aws_iam_role.consumer_role",
        "random_id.suffix",
        "aws_sns_topic.alerts-topic",
        "aws_lambda_function.publisher",
    }


def test_kind_mapping_covers_queue_and_unknown_fallback():
    nodes, _ = parse_terraform(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["aws_sqs_queue.events_queue"].kind == "queue"
    assert by_id["aws_sns_topic.alerts-topic"].kind == "queue"
    assert by_id["aws_iam_role.consumer_role"].kind == "unknown"
    assert by_id["random_id.suffix"].kind == "unknown"


def test_resource_name_with_dash_is_preserved_in_identity():
    nodes, _ = parse_terraform(FIXTURE)
    identities = {n.identity for n in nodes}
    assert "aws_sns_topic.alerts-topic" in identities


def test_var_data_module_refs_are_filtered_out_of_edges():
    # consumer's env references var.table_name, data.aws_region.current, and
    # module.storage.bucket_name alongside a real resource ref -- only the
    # real resource ref should surface as an edge.
    _, edges = parse_terraform(FIXTURE)
    dsts_from_consumer = {e.dst for e in edges if e.src == "aws_lambda_function.consumer"}
    assert dsts_from_consumer == {"aws_sqs_queue.events_queue"}


def test_cross_resource_edge_with_dashed_name():
    _, edges = parse_terraform(FIXTURE)
    pairs = {(e.src, e.dst) for e in edges}
    assert ("aws_lambda_function.publisher", "aws_sns_topic.alerts-topic") in pairs


def test_resource_with_no_interpolations_produces_no_edges():
    _, edges = parse_terraform(FIXTURE)
    assert not any(e.src == "aws_sqs_queue.events_queue" for e in edges)
    assert not any(e.src == "aws_iam_role.consumer_role" for e in edges)
    assert not any(e.src == "random_id.suffix" for e in edges)


def test_line_numbers_point_at_resource_declaration():
    nodes, _ = parse_terraform(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["aws_sqs_queue.events_queue"].line == 1
    assert by_id["aws_lambda_function.consumer"].line == 5
    assert by_id["aws_sns_topic.alerts-topic"].line == 25
    assert by_id["aws_lambda_function.publisher"].line == 29


def test_skips_dot_terraform_and_node_modules_dirs(tmp_path):
    (tmp_path / ".terraform").mkdir()
    (tmp_path / ".terraform" / "cached.tf").write_text(
        'resource "aws_s3_bucket" "cached" {\n  bucket = "cached"\n}\n'
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "vendored.tf").write_text(
        'resource "aws_s3_bucket" "vendored" {\n  bucket = "vendored"\n}\n'
    )
    nodes, _ = parse_terraform(tmp_path)
    assert nodes == []


def test_skips_venv_dirs(tmp_path):
    for d in ("venv", ".venv", "vendor", "__pycache__", "dist", "build"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "bundled.tf").write_text(
            'resource "aws_s3_bucket" "bundled" {\n  bucket = "bundled"\n}\n'
        )
    nodes, _ = parse_terraform(tmp_path)
    assert nodes == []


def test_file_with_no_resource_blocks_is_a_noop(tmp_path):
    (tmp_path / "vars.tf").write_text('variable "region" {\n  default = "us-east-1"\n}\n')
    nodes, edges = parse_terraform(tmp_path)
    assert nodes == []
    assert edges == []


def test_multiple_files_aggregate_across_the_repo(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "main.tf").write_text(
        'resource "aws_s3_bucket" "left" {\n  bucket = "left"\n}\n'
    )
    (tmp_path / "b" / "main.tf").write_text(
        'resource "aws_s3_bucket" "right" {\n  bucket = "right"\n}\n'
    )
    nodes, _ = parse_terraform(tmp_path)
    identities = {n.identity for n in nodes}
    assert identities == {"aws_s3_bucket.left", "aws_s3_bucket.right"}


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_terraform(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)
