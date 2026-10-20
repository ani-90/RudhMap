"""SHA-256 content-keyed cache for extraction results.

Extraction is deterministic: the same file bytes always produce the same
EvidenceRecord/EdgeRecord list. So instead of re-parsing a file on every
scan, its result is cached under a hash of its own content. A file that
changed produces a different hash and is a guaranteed cache miss -- this can
never serve a stale result for changed content (spec invariant 4: same
commit -> byte-identical diagram).

Keyed by (extractor_name, file_path, content_hash), never by mtime: hashing
content means a file that was merely touched but not modified still hits the
cache. The path is part of the key because cached records cite their own
file -- an earlier version keyed on content alone, so two files with
identical bytes shared one entry and the second silently got the first
file's records (its own nodes vanished from the graph). Callers fold an
extractor version into `extractor_name`, so changing what an extractor emits
invalidates its old entries instead of serving them.

The on-disk filename carries a format version; bumping it discards caches
written under an older key scheme rather than leaving them to grow forever.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

_CACHE_DIRNAME = ".rudhmap_cache"
_CACHE_FILENAME = "extraction_cache.v2.json"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ExtractionCache:
    def __init__(self, repo_path: str | Path):
        self._path = Path(repo_path) / _CACHE_DIRNAME / _CACHE_FILENAME
        self._entries: dict[str, dict] = {}
        self._dirty = False
        if self._path.exists():
            try:
                self._entries = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                # Corrupt/unreadable cache file: degrade to a cold cache
                # rather than crashing the scan.
                self._entries = {}

    def get_or_compute(
        self,
        file_path: Path,
        extractor_name: str,
        compute: Callable[[], tuple[list[EvidenceRecord], list[EdgeRecord]]],
    ) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
        try:
            content = file_path.read_bytes()
        except Exception:
            # Let the extractor's own error handling decide what to do with
            # an unreadable file -- caching has nothing to key on here.
            return compute()

        key = f"{extractor_name}:{file_path}:{_hash_bytes(content)}"
        cached = self._entries.get(key)
        if cached is not None:
            nodes = [EvidenceRecord(**n) for n in cached["nodes"]]
            edges = [EdgeRecord(**e) for e in cached["edges"]]
            return nodes, edges

        nodes, edges = compute()
        self._entries[key] = {
            "nodes": [asdict(n) for n in nodes],
            "edges": [asdict(e) for e in edges],
        }
        self._dirty = True
        return nodes, edges

    def flush(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._entries), encoding="utf-8")
        self._dirty = False
