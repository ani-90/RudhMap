"""Tier 0 extractor: Dockerfiles.

Covers build-stage topology declared via FROM / COPY --from -- explicit,
not inferred. Multi-stage builds produce one node per stage (Docker itself
addresses unnamed stages by index, so we do too) plus edges for stage
extension (`FROM <prior-stage>`) and layer copying (`COPY --from=<stage>`).
See spec Part II, Stage 1, Tier 0.
"""
from __future__ import annotations

import re
from pathlib import Path

from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.extract.tier0_iac.compose import _kind_and_subtype_for_image

TIER = 0
CONFIDENCE = 1.0

_DOCKERFILE_RE = re.compile(r"^dockerfile(\..+)?$|.+\.dockerfile$", re.IGNORECASE)
_SKIP_DIRS = COMMON_SKIP_DIRS

_FROM_RE = re.compile(r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?\s*$", re.IGNORECASE)
_EXPOSE_RE = re.compile(r"^EXPOSE\s+(.+)$", re.IGNORECASE)
_COPY_OR_ADD_RE = re.compile(r"^(?:COPY|ADD)\b", re.IGNORECASE)
_COPY_FROM_RE = re.compile(r"--from=(\S+)")


def _iter_dockerfiles(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if _DOCKERFILE_RE.match(path.name):
            yield path


def _logical_lines(raw: str):
    """Yield (line_no, logical_line) pairs: backslash line-continuations are
    joined into one instruction (anchored at its first physical line), and
    blank/comment-only lines are dropped."""
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        start_no = i + 1
        parts = []
        line = lines[i]
        while line.rstrip().endswith("\\") and i + 1 < len(lines):
            parts.append(line.rstrip()[:-1])
            i += 1
            line = lines[i]
        parts.append(line)
        i += 1
        joined = " ".join(part.strip() for part in parts).strip()
        if not joined or joined.startswith("#"):
            continue
        yield start_no, joined


def parse_dockerfile(repo_path: str | Path) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    for docker_file in _iter_dockerfiles(repo_path):
        try:
            raw = docker_file.read_text(encoding="utf-8")
        except Exception:
            continue

        file_str = str(docker_file)
        stage_identities: dict[str, str] = {}  # lowercased label/index -> identity
        stages: list[dict] = []
        current = None

        for line_no, line in _logical_lines(raw):
            from_match = _FROM_RE.match(line)
            if from_match:
                base_image, stage_name = from_match.groups()
                idx = len(stages)
                label = stage_name if stage_name else f"stage{idx}"
                identity = f"docker:{file_str}#{label}"
                kind, subtype = _kind_and_subtype_for_image(base_image)

                current = {
                    "identity": identity,
                    "line": line_no,
                    "base_image": base_image,
                    "kind": kind,
                    "subtype": subtype,
                    "exposed_ports": [],
                    "extends": stage_identities.get(base_image.lower()),
                }
                stages.append(current)
                stage_identities[label.lower()] = identity
                stage_identities[str(idx)] = identity
                continue

            if current is None:
                continue

            expose_match = _EXPOSE_RE.match(line)
            if expose_match:
                current["exposed_ports"].extend(expose_match.group(1).split())
                continue

            if _COPY_OR_ADD_RE.match(line):
                for ref in _COPY_FROM_RE.findall(line):
                    referenced = stage_identities.get(ref.lower())
                    if referenced and referenced != current["identity"]:
                        edges.append(
                            EdgeRecord(
                                src=current["identity"],
                                dst=referenced,
                                file=file_str,
                                line=line_no,
                                tier=TIER,
                                confidence=CONFIDENCE,
                                attrs={"relation": "copies_from"},
                            )
                        )

        for stage in stages:
            attrs = {"base_image": stage["base_image"]}
            if stage["exposed_ports"]:
                attrs["exposed_ports"] = stage["exposed_ports"]

            nodes.append(
                EvidenceRecord(
                    kind=stage["kind"],
                    identity=stage["identity"],
                    file=file_str,
                    line=stage["line"],
                    tier=TIER,
                    confidence=CONFIDENCE,
                    subtype=stage["subtype"],
                    attrs=attrs,
                )
            )
            if stage["extends"]:
                edges.append(
                    EdgeRecord(
                        src=stage["identity"],
                        dst=stage["extends"],
                        file=file_str,
                        line=stage["line"],
                        tier=TIER,
                        confidence=CONFIDENCE,
                        attrs={"relation": "extends"},
                    )
                )

    return nodes, edges
