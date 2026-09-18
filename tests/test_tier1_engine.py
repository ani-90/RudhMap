from pathlib import Path

import pytest

from rudhmap.extract.tier1_rules.engine import _compile_rule, parse_tier1_rules

FIXTURE = Path(__file__).parent / "fixtures" / "tier1_rules"


def test_tier1_never_produces_edges():
    _, edges = parse_tier1_rules(FIXTURE)
    assert edges == []


def test_matches_real_usage_across_python_js_and_go():
    nodes, _ = parse_tier1_rules(FIXTURE)
    rule_ids_by_file = {}
    for n in nodes:
        rule_ids_by_file.setdefault(Path(n.file).name, set()).add(n.attrs["rule_id"])

    assert rule_ids_by_file["app.py"] == {
        "aws-s3-client",
        "aws-s3-bucket-name",
        "aws-dynamodb-client",
        "aws-sqs-client",
        "postgres-client",
        "redis-client",
    }
    assert rule_ids_by_file["main.go"] == {
        "aws-s3-client",
        "aws-dynamodb-client",
        "aws-sqs-client",
        "redis-client",
        "postgres-client",
    }
    assert rule_ids_by_file["worker.js"] == {
        "aws-s3-client",
        "aws-dynamodb-client",
        "postgres-client",
        "redis-client",
    }


def test_commented_out_python_usage_is_not_matched():
    # app.py line 5 is `# boto3.client("sqs") -- old queue code, no longer used`.
    # The real, uncommented sqs usage is on line 11 -- only that one should match.
    nodes, _ = parse_tier1_rules(FIXTURE)
    sqs_lines = {n.line for n in nodes if n.file.endswith("app.py") and n.attrs["rule_id"] == "aws-sqs-client"}
    assert sqs_lines == {11}


def test_commented_out_js_line_comment_is_not_matched():
    # worker.js line 1 is `// new SQSClient() setup used to live here, ripped out`.
    nodes, _ = parse_tier1_rules(FIXTURE)
    assert not any(n.file.endswith("worker.js") and n.attrs["rule_id"] == "aws-sqs-client" for n in nodes)


def test_multiline_block_comment_is_not_matched_but_real_usage_after_it_is():
    # worker.js lines 8-9 are a /* ... new Redis() should not match inside here ... */
    # block comment; the real `new Redis()` on line 13 must still match.
    nodes, _ = parse_tier1_rules(FIXTURE)
    redis_matches = [n for n in nodes if n.file.endswith("worker.js") and n.attrs["rule_id"] == "redis-client"]
    assert len(redis_matches) == 1
    assert redis_matches[0].line == 13


def test_non_source_extension_is_never_scanned():
    # notes.md contains literal text that would match aws-s3-client and
    # redis-client if it were scanned -- .md isn't in LANGUAGE_BY_EXT, so it
    # must never be opened for matching at all.
    nodes, _ = parse_tier1_rules(FIXTURE)
    assert not any(n.file.endswith("notes.md") for n in nodes)


def test_capture_arg_produces_resource_named_identity():
    nodes, _ = parse_tier1_rules(FIXTURE)
    bucket_node = next(n for n in nodes if n.attrs["rule_id"] == "aws-s3-bucket-name")
    assert bucket_node.identity == "aws-s3-bucket-name:raw-telemetry"
    assert bucket_node.attrs["bucket_name"] == "raw-telemetry"
    assert bucket_node.kind == "datastore"
    assert bucket_node.subtype == "s3"
    assert bucket_node.confidence == 0.9


def test_uncaptured_match_falls_back_to_file_line_identity():
    nodes, _ = parse_tier1_rules(FIXTURE)
    s3_client_node = next(n for n in nodes if n.file.endswith("app.py") and n.attrs["rule_id"] == "aws-s3-client")
    assert s3_client_node.identity == f"aws-s3-client:{s3_client_node.file}:{s3_client_node.line}"


def test_all_nodes_are_tier_1_with_rule_declared_confidence():
    nodes, _ = parse_tier1_rules(FIXTURE)
    assert all(n.tier == 1 for n in nodes)
    assert {n.confidence for n in nodes} == {0.75, 0.9}


def test_kind_and_subtype_match_rule_declarations():
    nodes, _ = parse_tier1_rules(FIXTURE)
    by_rule = {n.attrs["rule_id"]: n for n in nodes}
    assert by_rule["aws-sqs-client"].kind == "queue"
    assert by_rule["aws-sqs-client"].subtype == "sqs"
    assert by_rule["postgres-client"].kind == "datastore"
    assert by_rule["postgres-client"].subtype == "postgres"


def test_same_captured_identity_across_different_files_is_the_same_node_key(tmp_path):
    # Two different files independently referencing the same bucket name
    # should produce identical identities -- this is what lets a later
    # identity-resolution phase recognize them as the same real resource.
    (tmp_path / "a.py").write_text('s3.Bucket("shared-bucket")\n')
    (tmp_path / "b.py").write_text('s3.Bucket("shared-bucket")\n')
    nodes, _ = parse_tier1_rules(tmp_path)
    identities = {n.identity for n in nodes}
    assert identities == {"aws-s3-bucket-name:shared-bucket"}
    assert len(nodes) == 2  # still two distinct evidence records, same identity


def test_skips_vendor_and_node_modules_and_venv_dirs(tmp_path):
    for d in ("vendor", "node_modules", "venv", ".venv", "__pycache__"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "x.py").write_text('boto3.client("s3")\n')
    nodes, _ = parse_tier1_rules(tmp_path)
    assert nodes == []


def test_engine_ignores_files_with_no_applicable_rules(tmp_path):
    (tmp_path / "Main.java").write_text('S3Client.builder()\n')  # java has no rules in the starter set
    nodes, _ = parse_tier1_rules(tmp_path)
    assert nodes == []


def test_unreadable_file_does_not_crash_scan(tmp_path):
    (tmp_path / "broken.py").write_bytes(b"\xff\xfeboto3.client(\"s3\")\xff")
    nodes, edges = parse_tier1_rules(tmp_path)
    assert isinstance(nodes, list)
    assert isinstance(edges, list)


# --- rule loading / validation -----------------------------------------


def test_compile_rule_rejects_missing_required_field():
    with pytest.raises(ValueError):
        _compile_rule({"id": "x", "kind": "datastore", "patterns": []})


def test_compile_rule_rejects_capture_arg_without_named_group():
    with pytest.raises(ValueError):
        _compile_rule(
            {
                "id": "bad-rule",
                "kind": "datastore",
                "confidence": 0.8,
                "capture_arg": "name",
                "patterns": [{"lang": "python", "match": r"foo\(\)"}],
            }
        )


def test_compile_rule_accepts_valid_capture_arg_rule():
    rule = _compile_rule(
        {
            "id": "good-rule",
            "kind": "datastore",
            "subtype": "s3",
            "confidence": 0.8,
            "capture_arg": "name",
            "patterns": [{"lang": "python", "match": r"foo\((?P<value>\w+)\)"}],
        }
    )
    assert rule.id == "good-rule"
    assert rule.capture_arg == "name"
    assert rule.patterns[0].regex.groupindex.get("value") is not None


def test_parse_tier1_rules_with_custom_rules_dir(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "custom.yaml").write_text(
        "- id: custom-marker\n"
        "  kind: service\n"
        "  subtype: custom\n"
        "  confidence: 0.6\n"
        "  patterns:\n"
        "    - lang: python\n"
        "      match: MARKER_TOKEN\n"
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("MARKER_TOKEN\n")

    nodes, _ = parse_tier1_rules(repo, rules_dir=rules_dir)
    assert len(nodes) == 1
    assert nodes[0].attrs["rule_id"] == "custom-marker"
    assert nodes[0].kind == "service"
    assert nodes[0].subtype == "custom"
