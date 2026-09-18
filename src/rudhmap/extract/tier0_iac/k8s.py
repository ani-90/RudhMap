"""Tier 0 extractor: Kubernetes manifests.

Covers plain multi-document YAML manifests (not Helm templates — those
aren't valid YAML until rendered, and templating is out of scope for tier 0).
See spec Part II, Stage 1, Tier 0.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 0
CONFIDENCE = 1.0

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}
JOB_KINDS = {"CronJob", "Job"}
DATASTORE_KINDS = {"PersistentVolumeClaim"}
CONFIG_KINDS = {"ConfigMap", "Secret"}

_K8S_MANIFEST_RE = re.compile(r"\.ya?ml$", re.IGNORECASE)
_SKIP_DIRS = COMMON_SKIP_DIRS | {"charts", "templates"}  # + likely Helm template dirs
_DOC_SEP = re.compile(r"^---[ \t]*\n", re.MULTILINE)


def _kind_bucket(k8s_kind: str) -> str:
    if k8s_kind in WORKLOAD_KINDS:
        return "service"
    if k8s_kind in JOB_KINDS:
        return "job"
    if k8s_kind == "Service":
        return "route"
    if k8s_kind in DATASTORE_KINDS:
        return "datastore"
    if k8s_kind in CONFIG_KINDS:
        return "config"
    return "unknown"


def _iter_manifest_files(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if _K8S_MANIFEST_RE.search(path.name):
            yield path


def _iter_docs_with_offset(raw: str):
    starts = [0]
    ends = []
    for match in _DOC_SEP.finditer(raw):
        ends.append(match.start())  # exclude the '---' separator line itself
        starts.append(match.end())  # next chunk starts right after it
    ends.append(len(raw))
    for start, end in zip(starts, ends):
        yield raw[start:end], raw.count("\n", 0, start)


def _find_name_line(chunk: str, name: str, base_offset: int) -> int | None:
    pattern = re.compile(r'^\s*name:\s*["\']?' + re.escape(name) + r'["\']?\s*$', re.MULTILINE)
    match = pattern.search(chunk)
    if match is None:
        return None
    return base_offset + chunk.count("\n", 0, match.start()) + 1


def _selector_matches(selector: dict, labels: dict) -> bool:
    if not selector:
        return False
    return all(labels.get(k) == v for k, v in selector.items())


def _pod_labels(workload_doc: dict) -> dict:
    return (
        (workload_doc.get("spec") or {}).get("template", {}).get("metadata", {}).get("labels", {})
        or {}
    )


_ENVFROM_KEY_TO_KIND = {"configMapRef": "ConfigMap", "secretRef": "Secret"}
_VOLUME_KEY_TO_KIND = {"configMap": "ConfigMap", "secret": "Secret"}


def _config_refs(workload_doc: dict) -> list[tuple[str, str]]:
    """(k8s_kind, name) pairs referenced via envFrom or volumes — tagged with
    the concrete kind at the reference site so the resulting edge target
    matches the real node identity exactly (no guessing at edge-build time)."""
    refs: list[tuple[str, str]] = []
    spec = (workload_doc.get("spec") or {}).get("template", {}).get("spec", {}) or {}
    for container in spec.get("containers", []) or []:
        for env_from in container.get("envFrom", []) or []:
            for key, k8s_kind in _ENVFROM_KEY_TO_KIND.items():
                ref = env_from.get(key)
                if ref and ref.get("name"):
                    refs.append((k8s_kind, ref["name"]))
    for volume in spec.get("volumes", []) or []:
        for key, k8s_kind in _VOLUME_KEY_TO_KIND.items():
            ref = volume.get(key)
            if ref and ref.get("name"):
                refs.append((k8s_kind, ref["name"]))
        claim = volume.get("persistentVolumeClaim")
        if claim and claim.get("claimName"):
            refs.append(("PersistentVolumeClaim", claim["claimName"]))
    return refs


def parse_k8s(repo_path: str | Path) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    for manifest_file in _iter_manifest_files(repo_path):
        try:
            raw = manifest_file.read_text(encoding="utf-8")
        except Exception:
            continue

        file_str = str(manifest_file)
        docs_by_identity: dict[str, dict] = {}

        for chunk, offset in _iter_docs_with_offset(raw):
            try:
                doc = yaml.safe_load(chunk)
            except Exception:
                continue
            if not isinstance(doc, dict) or "kind" not in doc:
                continue

            k8s_kind = doc.get("kind")
            metadata = doc.get("metadata") or {}
            name = metadata.get("name")
            if not name:
                continue
            namespace = metadata.get("namespace", "default")
            identity = f"{k8s_kind}/{namespace}/{name}"
            line = _find_name_line(chunk, name, offset)

            nodes.append(
                EvidenceRecord(
                    kind=_kind_bucket(k8s_kind),
                    identity=identity,
                    file=file_str,
                    line=line,
                    tier=TIER,
                    confidence=CONFIDENCE,
                    subtype=k8s_kind.lower(),
                    attrs={"k8s_kind": k8s_kind, "namespace": namespace},
                )
            )
            docs_by_identity[identity] = {"doc": doc, "namespace": namespace, "line": line}

            if k8s_kind in WORKLOAD_KINDS or k8s_kind in JOB_KINDS:
                for ref_kind, ref_name in _config_refs(doc):
                    edges.append(
                        EdgeRecord(
                            src=identity,
                            dst=f"{ref_kind}/{namespace}/{ref_name}",
                            file=file_str,
                            line=line,
                            tier=TIER,
                            confidence=CONFIDENCE,
                            attrs={"relation": "mounts_or_reads"},
                        )
                    )

        # Service -> workload edges via label-selector matching, scoped to this file.
        services = {
            identity: entry for identity, entry in docs_by_identity.items() if entry["doc"].get("kind") == "Service"
        }
        workloads = {
            identity: entry
            for identity, entry in docs_by_identity.items()
            if entry["doc"].get("kind") in WORKLOAD_KINDS
        }
        for svc_identity, svc_entry in services.items():
            selector = (svc_entry["doc"].get("spec") or {}).get("selector", {}) or {}
            for wl_identity, wl_entry in workloads.items():
                if svc_entry["namespace"] != wl_entry["namespace"]:
                    continue
                if _selector_matches(selector, _pod_labels(wl_entry["doc"])):
                    edges.append(
                        EdgeRecord(
                            src=svc_identity,
                            dst=wl_identity,
                            file=file_str,
                            line=svc_entry["line"],
                            tier=TIER,
                            confidence=CONFIDENCE,
                            attrs={"relation": "routes_to"},
                        )
                    )

    return nodes, edges
