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

The cache lives outside the scanned repo (step B): a `.rudhmap_cache/` folder
inside a user's repo is clutter, shows up in their searches, and in the
benchmark it was visible to the agents' Grep/Glob. Location:
`$RUDHMAP_CACHE_DIR`, else `%LOCALAPPDATA%\rudhmap\cache` on Windows,
`$XDG_CACHE_HOME/rudhmap` or `~/.cache/rudhmap` elsewhere; one subfolder per
repo, named by a hash of its resolved path. Each flush keeps only the
entries used by that scan, so entries for old file contents don't pile up.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

_CACHE_FILENAME = "extraction_cache.v3.json"


def cache_root() -> Path:
    override = os.environ.get("RUDHMAP_CACHE_DIR")
    if override:
        return Path(override)
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "rudhmap" / "cache"
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "rudhmap"


def cache_path_for(repo_path: str | Path) -> Path:
    resolved = str(Path(repo_path).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in Path(resolved).name)[:40]
    return cache_root() / f"{name}-{digest}" / _CACHE_FILENAME


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ExtractionCache:
    def __init__(self, repo_path: str | Path):
        self._path = cache_path_for(repo_path)
        self._entries: dict[str, dict] = {}
        self._used: set[str] = set()
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
        self._used.add(key)
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

    @property
    def path(self) -> Path:
        return self._path

    def flush(self) -> None:
        stale = len(self._entries) - len(self._used & self._entries.keys())
        if not self._dirty and not stale:
            return
        if not self._used:
            return
        kept = {k: v for k, v in self._entries.items() if k in self._used}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(kept), encoding="utf-8")
        os.replace(tmp, self._path)
        self._entries = kept
        self._dirty = False
