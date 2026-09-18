from pathlib import Path

from rudhmap.extract.tier0_iac.k8s import parse_k8s

FIXTURE = Path(__file__).parent / "fixtures" / "k8s_extended"


def test_extracts_all_named_resources_across_kinds():
    nodes, _ = parse_k8s(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {
        "StatefulSet/data/db",
        "DaemonSet/default/agent",
        "CronJob/default/nightly",
        "Job/default/onetime",
        "ReplicaSet/default/legacy",
        "PersistentVolumeClaim/data/db-pvc",
        "Secret/data/db-secret",
        "ConfigMap/data/db-cfg",
        "Secret/default/job-secret",
        "Service/data/db-svc",
        "Service/default/cross-ns-svc",
        "Service/default/legacy-svc",
        "Secret/default/quoted-secret",
    }


def test_doc_missing_metadata_name_is_skipped():
    nodes, _ = parse_k8s(FIXTURE)
    identities = {n.identity for n in nodes}
    assert not any("nameless" in i for i in identities)
    assert not any(i.startswith("Pod/") for i in identities)


def test_non_dict_document_is_skipped():
    # The bare scalar "justastring" document must not crash the scan or
    # produce a node -- total node count is exactly the 13 named resources.
    nodes, _ = parse_k8s(FIXTURE)
    assert len(nodes) == 13


def test_kind_bucketing_for_workloads_jobs_datastore_and_config():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["StatefulSet/data/db"].kind == "service"
    assert by_id["DaemonSet/default/agent"].kind == "service"
    assert by_id["ReplicaSet/default/legacy"].kind == "service"
    assert by_id["CronJob/default/nightly"].kind == "job"
    assert by_id["Job/default/onetime"].kind == "job"
    assert by_id["PersistentVolumeClaim/data/db-pvc"].kind == "datastore"
    assert by_id["Secret/data/db-secret"].kind == "config"
    assert by_id["ConfigMap/data/db-cfg"].kind == "config"


def test_quoted_name_is_matched_and_line_anchored():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    quoted = by_id["Secret/default/quoted-secret"]
    assert quoted.line == 163
    assert '"' not in quoted.identity


def test_line_numbers_point_at_metadata_name_across_docs():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["StatefulSet/data/db"].line == 4
    assert by_id["DaemonSet/default/agent"].line == 29
    assert by_id["CronJob/default/nightly"].line == 44
    assert by_id["Job/default/onetime"].line == 58
    assert by_id["ReplicaSet/default/legacy"].line == 73
    assert by_id["Service/data/db-svc"].line == 120


def test_secretref_and_configmap_and_pvc_volume_refs_become_edges():
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    assert ("StatefulSet/data/db", "Secret/data/db-secret", "mounts_or_reads") in pairs
    assert ("StatefulSet/data/db", "ConfigMap/data/db-cfg", "mounts_or_reads") in pairs
    assert ("StatefulSet/data/db", "PersistentVolumeClaim/data/db-pvc", "mounts_or_reads") in pairs


def test_job_kind_envfrom_secretref_becomes_edge():
    # Job's pod spec sits directly under spec.template.spec (same shape as a
    # Deployment), so _config_refs picks it up.
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    assert ("Job/default/onetime", "Secret/default/job-secret", "mounts_or_reads") in pairs


def test_cronjob_envfrom_is_not_picked_up_due_to_nested_pod_spec_path():
    # Current parser state: _config_refs only looks at spec.template.spec,
    # but CronJob nests its pod spec under spec.jobTemplate.spec.template.spec.
    # Documents this as a known limitation rather than asserting desired
    # behavior that doesn't exist yet.
    _, edges = parse_k8s(FIXTURE)
    srcs = {e.src for e in edges}
    assert "CronJob/default/nightly" not in srcs


def test_service_selector_matches_only_within_same_namespace():
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    # db-svc lives in the same namespace ("data") as the StatefulSet it selects.
    assert ("Service/data/db-svc", "StatefulSet/data/db", "routes_to") in pairs
    # cross-ns-svc has an identical selector but lives in "default" while the
    # StatefulSet lives in "data" -- must not match across namespaces.
    assert ("Service/default/cross-ns-svc", "StatefulSet/data/db", "routes_to") not in pairs
    assert not any(e.src == "Service/default/cross-ns-svc" for e in edges)


def test_replicaset_service_selector_edge():
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    assert ("Service/default/legacy-svc", "ReplicaSet/default/legacy", "routes_to") in pairs


def test_all_records_are_tier_0_declared_truth():
    nodes, edges = parse_k8s(FIXTURE)
    assert all(n.tier == 0 and n.confidence == 1.0 for n in nodes)
    assert all(e.tier == 0 and e.confidence == 1.0 for e in edges)


def test_skips_charts_and_templates_dirs(tmp_path):
    (tmp_path / "charts").mkdir()
    (tmp_path / "charts" / "helm-like.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: should-be-skipped\n"
    )
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "tpl.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: also-skipped\n"
    )
    nodes, _ = parse_k8s(tmp_path)
    assert nodes == []


def test_skips_git_and_node_modules_dirs(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "cfg.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: git-internal\n"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "cfg.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: nm-internal\n"
    )
    nodes, _ = parse_k8s(tmp_path)
    assert nodes == []


def test_skips_venv_dirs(tmp_path):
    for d in ("venv", ".venv", "vendor", "__pycache__", "dist", "build"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "cfg.yaml").write_text(
            "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: bundled\n"
        )
    nodes, _ = parse_k8s(tmp_path)
    assert nodes == []


def test_malformed_document_in_multidoc_file_is_skipped_not_fatal(tmp_path):
    raw = (
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: good-one\n"
        "---\n"
        "kind: ConfigMap\n"
        "metadata: [unterminated\n"
        "---\n"
        "apiVersion: v1\n"
        "kind: ConfigMap\n"
        "metadata:\n"
        "  name: good-two\n"
    )
    (tmp_path / "manifest.yaml").write_text(raw)
    nodes, _ = parse_k8s(tmp_path)
    identities = {n.identity for n in nodes}
    assert identities == {"ConfigMap/default/good-one", "ConfigMap/default/good-two"}


def test_non_yaml_extension_is_ignored(tmp_path):
    (tmp_path / "manifest.yaml.bak").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: ignored\n"
    )
    nodes, _ = parse_k8s(tmp_path)
    assert nodes == []


def test_empty_selector_produces_no_routes_to_edge(tmp_path):
    raw = (
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n"
        "  name: svc-no-selector\n"
        "spec:\n"
        "  selector: {}\n"
        "---\n"
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: dep\n"
        "spec:\n"
        "  template:\n"
        "    metadata:\n"
        "      labels:\n"
        "        app: dep\n"
    )
    (tmp_path / "svc.yaml").write_text(raw)
    _, edges = parse_k8s(tmp_path)
    assert not any(e.attrs.get("relation") == "routes_to" for e in edges)
