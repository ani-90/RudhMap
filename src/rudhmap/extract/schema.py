"""Shared evidence record shapes. Every extraction tier (0-3) emits these same
shapes so downstream graph assembly never needs to know which tier produced
what. See rudhmap spec Part II, Stage 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceRecord:
    kind: str
    identity: str
    file: str
    line: int | None
    tier: int
    confidence: float
    subtype: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeRecord:
    src: str
    dst: str
    file: str
    line: int | None
    tier: int
    confidence: float
    attrs: dict[str, Any] = field(default_factory=dict)
