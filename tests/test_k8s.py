from pathlib import Path

from rudhmap.extract.tier0_iac.k8s import parse_k8s

FIXTURE = Path(__file__).parent / "fixtures" / "k8s"


def test_extracts_deployment_service_and_configmap():
    nodes, _ = parse_k8s(FIXTURE)
    identities = {n.identity for n in nodes}
    assert identities == {
        "Deployment/default/api",
        "Service/default/api-svc",
        "ConfigMap/default/api-config",
    }


def test_kind_bucketing():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["Deployment/default/api"].kind == "service"
    assert by_id["Service/default/api-svc"].kind == "route"
    assert by_id["ConfigMap/default/api-config"].kind == "config"


def test_line_numbers_point_at_metadata_name():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["Deployment/default/api"].line == 4
    assert by_id["Service/default/api-svc"].line == 22
    assert by_id["ConfigMap/default/api-config"].line == 33


def test_service_selector_matches_deployment_labels():
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    assert ("Service/default/api-svc", "Deployment/default/api", "routes_to") in pairs


def test_deployment_configmapref_becomes_edge():
    _, edges = parse_k8s(FIXTURE)
    pairs = {(e.src, e.dst, e.attrs.get("relation")) for e in edges}
    assert ("Deployment/default/api", "ConfigMap/default/api-config", "mounts_or_reads") in pairs


def test_subtype_is_lowercased_k8s_kind():
    nodes, _ = parse_k8s(FIXTURE)
    by_id = {n.identity: n for n in nodes}
    assert by_id["Deployment/default/api"].subtype == "deployment"
    assert by_id["Service/default/api-svc"].subtype == "service"
    assert by_id["ConfigMap/default/api-config"].subtype == "configmap"
