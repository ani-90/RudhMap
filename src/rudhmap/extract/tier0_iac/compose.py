"""Tier 0 extractor: docker-compose.yml.

Same authority as Terraform within tier 0 — a compose file declares services
and their dependencies explicitly. See spec Part II, Stage 1, Tier 0.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 0
CONFIDENCE = 1.0

# Substring match against the service's image name. First match wins.
# Anything unmatched defaults to ("service", None) (compose services are
# application code, not infra, unless the image says otherwise).
# Entries are (needle, kind, subtype).
IMAGE_KIND_MAP = [
    ("postgres", "datastore", "postgres"),
    ("mysql", "datastore", "mysql"),
    ("mariadb", "datastore", "mariadb"),
    ("mongo", "datastore", "mongodb"),
    ("redis", "datastore", "redis"),
    ("dynamodb", "datastore", "dynamodb"),
    ("cassandra", "datastore", "cassandra"),
    ("elasticsearch", "datastore", "elasticsearch"),
    ("opensearch", "datastore", "opensearch"),
    ("rabbitmq", "queue", "rabbitmq"),
    ("kafka", "queue", "kafka"),
    ("sqs", "queue", "sqs"),
    ("nats", "queue", "nats"),
    ("nginx", "gateway", "nginx"),
    ("traefik", "gateway", "traefik"),
    ("envoy", "gateway", "envoy"),
]

_COMPOSE_FILE_RE = re.compile(r"^docker-compose.*\.ya?ml$|^compose\.ya?ml$", re.IGNORECASE)
_SKIP_DIRS = COMMON_SKIP_DIRS


def _kind_and_subtype_for_image(image: str | None) -> tuple[str, str | None]:
    if not image:
        return "service", None
    lowered = image.lower()
    for needle, kind, subtype in IMAGE_KIND_MAP:
        if needle in lowered:
            return kind, subtype
    return "service", None


def _find_service_line(raw: str, service_name: str) -> int | None:
    """Match the service's own key line, e.g. '  raw_telemetry:' under a
    'services:' block. Anchored at line start + indentation to avoid matching
    the same name if it also appears as a value elsewhere (env vars, etc.)."""
    pattern = re.compile(r"^[ \t]+" + re.escape(service_name) + r":[ \t]*$", re.MULTILINE)
    match = pattern.search(raw)
    if match is None:
        return None
    return raw.count("\n", 0, match.start()) + 1


def _iter_compose_files(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if _COMPOSE_FILE_RE.match(path.name):
            yield path


def _extract_build_context(config: dict) -> str | None:
    """`build:` is either a bare path string or a mapping with a `context`
    key -- both name the directory holding this service's code, relative to
    the compose file's own directory."""
    build = config.get("build")
    if isinstance(build, str):
        return build
    if isinstance(build, dict):
        context = build.get("context")
        if isinstance(context, str):
            return context
    return None


def _normalize_depends_on(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return list(value.keys())
    return []


def parse_compose(repo_path: str | Path) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    for compose_file in _iter_compose_files(repo_path):
        try:
            raw = compose_file.read_text(encoding="utf-8")
            parsed = yaml.safe_load(raw)
        except Exception:
            continue

        if not isinstance(parsed, dict):
            continue
        services = parsed.get("services")
        if not isinstance(services, dict):
            continue

        file_str = str(compose_file)

        for service_name, config in services.items():
            config = config or {}
            image = config.get("image") if isinstance(config, dict) else None
            line = _find_service_line(raw, service_name)
            kind, subtype = _kind_and_subtype_for_image(image)

            attrs: dict[str, object] = {}
            if image:
                attrs["image"] = image
            build_context = _extract_build_context(config) if isinstance(config, dict) else None
            if build_context:
                attrs["build_context"] = build_context

            nodes.append(
                EvidenceRecord(
                    kind=kind,
                    identity=f"compose:{service_name}",
                    file=file_str,
                    line=line,
                    tier=TIER,
                    confidence=CONFIDENCE,
                    subtype=subtype,
                    attrs=attrs,
                )
            )

            depends_on = _normalize_depends_on(config.get("depends_on")) if isinstance(config, dict) else []
            for dep in depends_on:
                edges.append(
                    EdgeRecord(
                        src=f"compose:{service_name}",
                        dst=f"compose:{dep}",
                        file=file_str,
                        line=line,
                        tier=TIER,
                        confidence=CONFIDENCE,
                        attrs={"relation": "depends_on"},
                    )
                )

    return nodes, edges
