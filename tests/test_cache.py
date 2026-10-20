from pathlib import Path

from rudhmap.cache import ExtractionCache
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord


def test_cache_miss_calls_compute_and_stores_result(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    calls = []

    def compute():
        calls.append(1)
        return [EvidenceRecord(kind="function", identity="a.py:x", file=str(f), line=1, tier=2, confidence=1.0)], []

    nodes, edges = cache.get_or_compute(f, "python", compute)
    assert len(calls) == 1
    assert nodes[0].identity == "a.py:x"
    assert edges == []


def test_cache_hit_does_not_call_compute_again(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    calls = []

    def compute():
        calls.append(1)
        return [EvidenceRecord(kind="function", identity="a.py:x", file=str(f), line=1, tier=2, confidence=1.0)], []

    cache.get_or_compute(f, "python", compute)
    nodes, edges = cache.get_or_compute(f, "python", compute)

    assert len(calls) == 1  # second call was a cache hit, compute() not invoked again
    assert nodes[0].identity == "a.py:x"


def test_changed_content_is_a_guaranteed_cache_miss(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    calls = []

    def compute():
        calls.append(1)
        return [], []

    cache.get_or_compute(f, "python", compute)
    f.write_text("x = 2")  # different content -> different hash
    cache.get_or_compute(f, "python", compute)

    assert len(calls) == 2


def test_different_extractor_name_is_a_separate_cache_entry(tmp_path):
    """Same file content, two different extractors (e.g. tier1 regex vs
    tier2 AST both run over the same .py file) must not collide."""
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    python_calls = []
    tier1_calls = []

    cache.get_or_compute(f, "python", lambda: (python_calls.append(1), ([], []))[1])
    cache.get_or_compute(f, "tier1", lambda: (tier1_calls.append(1), ([], []))[1])

    assert len(python_calls) == 1
    assert len(tier1_calls) == 1


def test_cache_persists_across_instances_after_flush(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")

    cache1 = ExtractionCache(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return [EvidenceRecord(kind="function", identity="a.py:x", file=str(f), line=1, tier=2, confidence=1.0)], []

    cache1.get_or_compute(f, "python", compute)
    cache1.flush()

    cache2 = ExtractionCache(tmp_path)  # simulates a fresh process/run
    nodes, edges = cache2.get_or_compute(f, "python", compute)

    assert len(calls) == 1  # cache2 read the persisted entry, never called compute
    assert nodes[0].identity == "a.py:x"


def test_unflushed_cache_does_not_persist(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")

    cache1 = ExtractionCache(tmp_path)
    cache1.get_or_compute(f, "python", lambda: ([], []))
    # no flush()

    cache2 = ExtractionCache(tmp_path)
    calls = []
    cache2.get_or_compute(f, "python", lambda: (calls.append(1), ([], []))[1])
    assert len(calls) == 1  # cache2 never saw cache1's unflushed entry


def test_evidence_records_round_trip_through_json_including_attrs(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    original_node = EvidenceRecord(
        kind="datastore", identity="s3:my-bucket", file=str(f), line=4, tier=1,
        confidence=0.9, subtype="s3", attrs={"bucket_name": "my-bucket"},
    )
    original_edge = EdgeRecord(
        src="a.py:handler", dst="a.py:helper", file=str(f), line=2, tier=2,
        confidence=1.0, attrs={"callee_chain": ["helper"], "likely_import_alias": False},
    )

    cache.get_or_compute(f, "python", lambda: ([original_node], [original_edge]))
    cache.flush()

    cache2 = ExtractionCache(tmp_path)
    nodes, edges = cache2.get_or_compute(f, "python", lambda: (_ for _ in ()).throw(AssertionError("should be a hit")))

    assert nodes[0] == original_node
    assert edges[0] == original_edge


def test_unreadable_file_falls_back_to_compute_without_caching(tmp_path):
    cache = ExtractionCache(tmp_path)
    missing = tmp_path / "does_not_exist.py"

    calls = []

    def compute():
        calls.append(1)
        return [], []

    cache.get_or_compute(missing, "python", compute)
    cache.get_or_compute(missing, "python", compute)

    assert len(calls) == 2  # never cached, since there was no content to hash


def test_flush_with_nothing_new_is_a_noop(tmp_path):
    cache = ExtractionCache(tmp_path)
    cache.flush()  # must not create a cache file when nothing was computed
    assert not (tmp_path / ".rudhmap_cache").exists()


def test_corrupt_cache_file_degrades_to_cold_cache(tmp_path):
    cache_dir = tmp_path / ".rudhmap_cache"
    cache_dir.mkdir()
    (cache_dir / "extraction_cache.v2.json").write_text("not valid json{{{")

    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)

    calls = []
    cache.get_or_compute(f, "python", lambda: (calls.append(1), ([], []))[1])
    assert len(calls) == 1  # didn't crash, just treated corrupt cache as empty


def test_identical_content_in_two_files_does_not_share_an_entry(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("def helper():\n    return 1\n")
    b.write_text("def helper():\n    return 1\n")
    cache = ExtractionCache(tmp_path)

    def compute_for(path):
        return lambda: ([EvidenceRecord(kind="function", identity=f"{path}:helper", file=str(path), line=1, tier=2, confidence=1.0)], [])

    nodes_a, _ = cache.get_or_compute(a, "python", compute_for(a))
    nodes_b, _ = cache.get_or_compute(b, "python", compute_for(b))

    assert nodes_a[0].file == str(a)
    assert nodes_b[0].file == str(b)


def test_identical_files_both_appear_in_the_assembled_graph(tmp_path):
    from rudhmap.pipeline import build_assembly

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("def helper():\n    return 1\n")
    (pkg / "b.py").write_text("def helper():\n    return 1\n")

    for _ in range(2):  # cold, then warm from the flushed cache
        graph = build_assembly(str(tmp_path), verbose=False).result.graph
        assert sorted(n.rsplit("pkg", 1)[1] for n in graph.nodes) == [
            str(Path("/a.py")) + ":helper",
            str(Path("/b.py")) + ":helper",
        ]


def test_extractor_version_is_part_of_the_key(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1")
    cache = ExtractionCache(tmp_path)
    calls = []

    cache.get_or_compute(f, "python@1", lambda: (calls.append(1), ([], []))[1])
    cache.get_or_compute(f, "python@2", lambda: (calls.append(2), ([], []))[1])

    assert calls == [1, 2]
