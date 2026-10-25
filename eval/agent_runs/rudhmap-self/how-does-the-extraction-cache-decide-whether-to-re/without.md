# without get_context: how does the extraction cache decide whether to reuse a previous result

The cache in `src/rudhmap/cache.py` reuses a result only when the extractor name, file path and file content hash all match an existing entry.

- **Key:** `get_or_compute` reads the file's bytes and builds `f"{extractor_name}:{file_path}:{sha256(content)}"` (`cache.py:60-66`). The hash comes from `_hash_bytes` (`cache.py:36-37`).
- **Hit:** If that key is in `self._entries`, it rebuilds `EvidenceRecord` and `EdgeRecord` objects from the stored dicts and returns them without calling the extractor (`cache.py:67-71`).
- **Miss:** It calls `compute()`, stores the serialized nodes and edges under the key, and sets `_dirty` (`cache.py:73-78`). `flush()` writes to disk only if `_dirty` is set (`cache.py:81-86`).
- **Content, not mtime:** A file that was touched but not changed still hits. A file whose bytes changed gets a new hash, so it always misses (`cache.py:1-11`).
- **Path in the key:** Cached records cite their own file. Without the path, two files with identical bytes shared one entry, and the second file's nodes vanished (`cache.py:12-15`).
- **Extractor version:** Callers fold a version into `extractor_name`, such as `python@3`. Changing an extractor's output means bumping that version, which invalidates its old entries (`cache.py:15-17`). I didn't open the callers to confirm the exact names.
- **Format version:** The filename `extraction_cache.v2.json` (`cache.py:33`) carries a format version. Bumping it discards caches written under an older key scheme.
- **Fallbacks:**
  - A corrupt or unreadable cache file is treated as an empty cache (`cache.py:45-51`).
  - An unreadable source file skips caching and calls `compute()` directly (`cache.py:59-64`).

The cache lives at `<repo>/.rudhmap_cache/` (`cache.py:32,42`).
