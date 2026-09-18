"""The IR: a flat, ordered, NetworkX-free shape for a verified graph. See
rudhmap spec Part II, Stage 2 (verifier). Reuses `EvidenceRecord`/
`EdgeRecord` unchanged -- they already carry everything (file, line, tier,
confidence) a citation needs; the IR only adds the stable node/edge
container shape that layout, render, and the phase-8 abstraction step can
consume without importing NetworkX.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord


@dataclass
class IRNode:
    id: str
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class IREdge:
    src: str
    dst: str
    evidence: EdgeRecord


@dataclass
class IRGraph:
    nodes: list[IRNode] = field(default_factory=list)
    edges: list[IREdge] = field(default_factory=list)
