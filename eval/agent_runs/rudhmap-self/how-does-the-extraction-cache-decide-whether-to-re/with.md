# with get_context: how does the extraction cache decide whether to reuse a previous result

The cache reuses a result only when an exact key already exists. That key is built from the extractor name, the file path, and a hash of the file's content.

- **Key:** `get_or_compute` builds `f"{extractor_name}:{file_path}:{sha256(content)}"` (`src/rudhmap/cache.py:66`). It reads the file's bytes and hashes them with SHA-256 (`cache.py:36-37`, `cache.py:60`).
- **Hit:** If `self._entries` already has that key, it rebuilds the `EvidenceRecord` and `EdgeRecord` objects from the stored dicts and returns them without calling `compute()` (`cache.py:67-71`).
- **Miss:** Otherwise it runs `compute()`, stores the serialized nodes and edges under the key, and marks the cache dirty (`cache.py:73-78`). `flush()` writes to disk only when dirty (`cache.py:81-86`).
- **Content, not mtime:** A file that was only touched still hits. A file whose content changed gets a new hash and always misses (`cache.py:6-11`).
- **Path in the key:** This is a bug fix. Two files with identical bytes used to share one entry, so the second file's nodes vanished (`cache.py:12-15`).
- **Extractor version:** Callers put a version in `extractor_name`, such as `python@3`. Changing an extractor's output therefore invalidates its old entries (`cache.py:15-17`). `CLAUDE.md` says to bump the version whenever an extractor's output changes.
- **Format version:** The cache file is `.rudhmap_cache/extraction_cache.v2.json` (`cache.py:32-33`). Bumping the `v2` in the filename discards caches written under an older key scheme.
- **Fallbacks:** If the cache file is corrupt, it starts cold (`cache.py:48-51`). If the source file can't be read, it calls `compute()` and skips caching (`cache.py:61-64`).

`get_context` returned the call graph around `graph_to_ir` and didn't include `cache.py`, so I read `cache.py` directly. I didn't open `pipeline.py` to check where the extractor names are set.
