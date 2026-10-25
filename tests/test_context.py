from pathlib import Path

from rudhmap.context import build_context_pack, estimate_tokens
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.extract.tier2_ast.typescript import parse_typescript_ast
from rudhmap.graph.slice import _node_text_blob

API_PY = """\
from app.store import save_upload


def handle_upload(data):
    checked = validate(data)
    save_upload(checked)
    return save_upload(checked)


def validate(data):
    if not data:
        raise ValueError("empty upload")
    return data
"""

STORE_PY = """\
class UploadStore:
    root = "/uploads"

    def put(self, data):
        return len(data)


def save_upload(data):
    return UploadStore().put(data)
"""


def _make_repo(parent: Path, name: str = "repo") -> Path:
    root = parent / name
    (root / "app").mkdir(parents=True)
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "api.py").write_text(API_PY, encoding="utf-8")
    (root / "app" / "store.py").write_text(STORE_PY, encoding="utf-8")
    return root


def test_python_and_typescript_defs_record_end_line(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    x = 1\n    return x\n\n\ndef g():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.ts").write_text("function h() {\n  return 1;\n}\n", encoding="utf-8")

    py = {n.attrs["qualname"]: n for n in parse_python_ast(tmp_path)[0]}
    ts = {n.attrs["qualname"]: n for n in parse_typescript_ast(tmp_path)[0]}

    assert (py["f"].line, py["f"].attrs["end_line"]) == (1, 3)
    assert (py["g"].line, py["g"].attrs["end_line"]) == (6, 7)
    assert (ts["h"].line, ts["h"].attrs["end_line"]) == (1, 3)


def test_end_line_is_not_indexed_for_search(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    node = parse_python_ast(tmp_path)[0][0]

    blob = _node_text_blob(node.identity, [node])

    assert "end_line" not in blob
    assert "qualname:f" in blob


def test_pack_has_call_graph_and_exact_function_source(tmp_path):
    repo = _make_repo(tmp_path)

    pack = build_context_pack(repo, "handle upload")

    assert pack.status == "ok"
    assert pack.seed_ids == ["app/api.py:handle_upload"]
    assert pack.snippets[0].node_id == "app/api.py:handle_upload"
    assert pack.snippets[0].text == "\n".join(API_PY.splitlines()[3:7])
    assert "### app/api.py:handle_upload (function, app/api.py:4-7)" in pack.text
    assert "- app/api.py:handle_upload -> app/api.py:validate [calls @ app/api.py:5]" in pack.text


def test_repeated_calls_between_a_pair_collapse_to_one_line(tmp_path):
    repo = _make_repo(tmp_path)

    pack = build_context_pack(repo, "handle upload")

    assert "- app/api.py:handle_upload -> app/store.py:save_upload [calls @ app/api.py:6,7]" in pack.text


def test_class_snippet_is_cut_before_methods_shown_on_their_own(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "app" / "admin.py").write_text(
        "from app.store import UploadStore\n\n\ndef purge_store(store):\n"
        "    UploadStore(store)\n    return UploadStore.put(store, b'')\n",
        encoding="utf-8",
    )

    pack = build_context_pack(repo, "app/admin.py:purge_store")

    by_id = {s.node_id: s for s in pack.snippets}
    store = by_id["app/store.py:UploadStore"]
    assert (store.start, store.end) == (1, 3)
    assert "def put" not in store.text
    assert by_id["app/store.py:UploadStore.put"].text.strip().startswith("def put(self, data):")


def test_class_keeps_methods_that_are_not_in_the_slice(tmp_path):
    repo = _make_repo(tmp_path)

    # `UploadStore().put(...)` is a call on an instance, which static resolution
    # can't follow, so `put` isn't in the slice -- the class body must keep it.
    pack = build_context_pack(repo, "upload store")

    by_id = {s.node_id: s for s in pack.snippets}
    assert "app/store.py:UploadStore.put" not in by_id
    assert "def put(self, data):" in by_id["app/store.py:UploadStore"].text


def test_tight_budget_moves_bodies_to_cited_references(tmp_path):
    repo = _make_repo(tmp_path)

    roomy = build_context_pack(repo, "handle upload", token_budget=6000)
    tight = build_context_pack(repo, "handle upload", token_budget=250)

    assert tight.pack_tokens <= 250
    assert tight.pack_tokens == estimate_tokens(tight.text)
    assert len(tight.snippets) < len(roomy.snippets)
    assert tight.references
    assert "## Also involved, not shown" in tight.text
    for ref in tight.references:
        assert f"{ref.file}:{ref.start}-{ref.end}" in tight.text


def test_baseline_counts_touched_files_read_whole(tmp_path):
    repo = _make_repo(tmp_path)

    pack = build_context_pack(repo, "handle upload")

    assert pack.baseline_files == 2
    assert pack.baseline_tokens == estimate_tokens(API_PY.rstrip("\n")) + estimate_tokens(STORE_PY.rstrip("\n"))


def test_pack_is_identical_across_checkout_locations(tmp_path):
    one = build_context_pack(_make_repo(tmp_path / "a"), "handle upload")
    two = build_context_pack(_make_repo(tmp_path / "b", name="elsewhere"), "handle upload")

    assert one.text == two.text
    assert str(tmp_path) not in one.text


def test_no_match(tmp_path):
    repo = _make_repo(tmp_path)

    pack = build_context_pack(repo, "kafka billing invoices")

    assert pack.status == "no_match"
    assert pack.text == ""
