"""Tier 0 extractor: Terraform HCL.

Highest-confidence evidence in the pipeline — infrastructure topology is
declared explicitly here, not inferred from code. See spec Part II, Stage 1,
Tier 0: "parse the declarative artifact, treat it as authoritative, never let
the model guess what it already states."
"""
from __future__ import annotations

import re
from pathlib import Path

import hcl2

from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 0
CONFIDENCE = 1.0

# Seed mapping. Grows as tier0 coverage expands — not meant to be exhaustive;
# unmapped resource types still produce a node with kind="unknown" rather
# than being dropped, since the identity/evidence is still real signal.
# Values are (kind, subtype): kind is the coarse bucket everything downstream
# reasons about, subtype is the granular resource type used for naming,
# icon selection, and eval ground-truth matching.
KIND_MAP: dict[str, tuple[str, str]] = {
    "aws_s3_bucket": ("datastore", "s3"),
    "aws_lambda_function": ("service", "lambda"),
    "aws_dynamodb_table": ("datastore", "dynamodb"),
    "aws_sqs_queue": ("queue", "sqs"),
    "aws_sns_topic": ("queue", "sns"),
    "aws_rds_cluster": ("datastore", "rds"),
    "aws_rds_instance": ("datastore", "rds"),
    "aws_db_instance": ("datastore", "rds"),
    "aws_kinesis_stream": ("queue", "kinesis"),
    "aws_api_gateway_rest_api": ("service", "apigateway"),
    "aws_apigatewayv2_api": ("service", "apigateway"),
    "aws_ecs_service": ("service", "ecs"),
    "aws_ecs_task_definition": ("service", "ecs"),
    "aws_sfn_state_machine": ("service", "stepfunctions"),
    "aws_elasticache_cluster": ("datastore", "elasticache"),
    "aws_msk_cluster": ("queue", "msk"),
}

_SKIP_DIRS = COMMON_SKIP_DIRS | {".terraform"}

# python-hcl2 renders interpolations as "${type.name.attr}" strings even
# where HCL2 syntax itself has dropped the ${} wrapper for top-level refs.
_REF_RE = re.compile(r"\$\{([a-zA-Z_][\w-]*)\.([a-zA-Z_][\w-]*)")

# Reference prefixes that are not resource identities and would otherwise
# produce dangling edges to nodes that don't exist in the structural graph.
_NON_RESOURCE_PREFIXES = {"var", "local", "data", "module", "each", "count", "path", "terraform"}


def _strip_quotes(value: object) -> object:
    """python-hcl2 (>=8.x) keeps literal quote characters on parsed string
    tokens, e.g. rtype comes back as '"aws_s3_bucket"' not 'aws_s3_bucket'."""
    if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _find_resource_line(raw: str, rtype: str, name: str) -> int | None:
    """Anchor on the actual `resource "type" "name" {` declaration syntax
    rather than any line that happens to contain both substrings."""
    pattern = re.compile(r'resource\s+"' + re.escape(rtype) + r'"\s+"' + re.escape(name) + r'"\s*\{')
    match = pattern.search(raw)
    if match is None:
        return None
    return raw.count("\n", 0, match.start()) + 1


def _iter_refs(value: object):
    """Recursively yield (ref_type, ref_name) pairs found anywhere inside a
    parsed resource config's interpolation expressions."""
    if isinstance(value, str):
        for ref_type, ref_name in _REF_RE.findall(value):
            if ref_type in _NON_RESOURCE_PREFIXES:
                continue
            yield ref_type, ref_name
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from _iter_refs(v)


def _iter_tf_files(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if path.suffix == ".tf":
            yield path


def parse_terraform(repo_path: str | Path) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    for tf_file in _iter_tf_files(repo_path):
        try:
            raw = tf_file.read_text(encoding="utf-8")
            parsed = hcl2.loads(raw)
        except Exception:
            # Malformed/unparseable file: degrade gracefully, don't crash the scan.
            continue

        for block in parsed.get("resource", []):
            for rtype_raw, instances in block.items():
                rtype = _strip_quotes(rtype_raw)
                for name_raw, config in instances.items():
                    name = _strip_quotes(name_raw)
                    identity = f"{rtype}.{name}"
                    line = _find_resource_line(raw, rtype, name)
                    file_str = str(tf_file)
                    kind, subtype = KIND_MAP.get(rtype, ("unknown", None))

                    nodes.append(
                        EvidenceRecord(
                            kind=kind,
                            identity=identity,
                            file=file_str,
                            line=line,
                            tier=TIER,
                            confidence=CONFIDENCE,
                            subtype=subtype,
                            attrs={"resource_type": rtype},
                        )
                    )

                    for ref_type, ref_name in _iter_refs(config):
                        edges.append(
                            EdgeRecord(
                                src=identity,
                                dst=f"{ref_type}.{ref_name}",
                                file=file_str,
                                line=line,
                                tier=TIER,
                                confidence=CONFIDENCE,
                                attrs={},
                            )
                        )

    return nodes, edges
