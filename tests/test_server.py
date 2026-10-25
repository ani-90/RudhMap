from pathlib import Path

import anyio
from mcp import Client

from rudhmap.server import mcp

SERVICE_PY = """\
from app.store import save_upload


def handle_upload(data):
    return save_upload(data)
"""

STORE_PY = """\
def save_upload(data):
    return _write(data)


def _write(data):
    return len(data)
"""

COMPOSE_YML = """\
services:
  api:
    build: .
    depends_on:
      - db
  db:
    image: postgres:16
"""


def _make_repo(parent: Path, name: str = "repo") -> Path:
    root = parent / name
    (root / "app").mkdir(parents=True)
    (root / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "app" / "service.py").write_text(SERVICE_PY, encoding="utf-8")
    (root / "app" / "store.py").write_text(STORE_PY, encoding="utf-8")
    (root / "docker-compose.yml").write_text(COMPOSE_YML, encoding="utf-8")
    return root


def _call(name: str, arguments: dict):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(name, arguments)

    return anyio.run(run)


def _list_tools():
    async def run():
        async with Client(mcp) as client:
            return await client.list_tools()

    return anyio.run(run)


def test_lists_tools_with_correct_annotations():
    tools = {t.name: t for t in _list_tools().tools}

    assert set(tools) == {"scan", "slice", "generate_diagram", "get_context"}
    for name in ("scan", "slice", "get_context"):
        assert tools[name].annotations.read_only_hint is True
        assert tools[name].annotations.destructive_hint is False
    assert tools["generate_diagram"].annotations.read_only_hint is False
    assert tools["generate_diagram"].annotations.destructive_hint is False
    assert set(tools["slice"].input_schema["properties"]) == {"repo_path", "query", "max_nodes"}
    assert set(tools["generate_diagram"].input_schema["properties"]) == {
        "repo_path", "query", "max_nodes", "output_path"
    }
    assert set(tools["get_context"].input_schema["properties"]) == {
        "repo_path", "query", "token_budget", "max_nodes"
    }


def test_scan_returns_verified_graph_with_relative_ids_and_evidence(tmp_path):
    repo = _make_repo(tmp_path)

    result = _call("scan", {"repo_path": str(repo)})

    assert result.is_error is False
    data = result.structured_content
    node_ids = {n["id"] for n in data["nodes"]}
    assert "app/service.py:handle_upload" in node_ids
    assert "app/store.py:save_upload" in node_ids
    assert "compose:api" in node_ids
    assert data["dropped_by_verifier"] == {"nodes": 0, "edges": 0}

    for node in data["nodes"]:
        for ev in node["evidence"]:
            assert not Path(ev["file"]).is_absolute()
            assert "\\" not in ev["file"]
            assert str(tmp_path) not in node["id"]


def test_scan_labels_edge_relations(tmp_path):
    repo = _make_repo(tmp_path)

    edges = _call("scan", {"repo_path": str(repo)}).structured_content["edges"]
    by_pair = {(e["src"], e["dst"]): e for e in edges}

    cross_file = by_pair[("app/service.py:handle_upload", "app/store.py:save_upload")]
    assert cross_file["relation"] == "calls"
    assert cross_file["evidence"] == {"file": "app/service.py", "line": 5, "tier": 2, "confidence": 1.0}
    assert by_pair[("compose:api", "compose:db")]["relation"] == "depends_on"


def test_scan_output_is_identical_across_checkout_locations(tmp_path):
    first = _make_repo(tmp_path / "a")
    second = _make_repo(tmp_path / "somewhere" / "else")

    one = _call("scan", {"repo_path": str(first)}).structured_content
    two = _call("scan", {"repo_path": str(second)}).structured_content

    assert one == two


def test_slice_returns_scoped_subgraph(tmp_path):
    repo = _make_repo(tmp_path)

    data = _call("slice", {"repo_path": str(repo), "query": "handle upload"}).structured_content

    assert data["status"] == "ok"
    assert data["seed_ids"] == ["app/service.py:handle_upload"]
    node_ids = {n["id"] for n in data["nodes"]}
    assert "app/store.py:save_upload" in node_ids
    assert data["dropped_by_verifier"] == {"nodes": 0, "edges": 0}


def test_slice_reports_no_match(tmp_path):
    repo = _make_repo(tmp_path)

    data = _call("slice", {"repo_path": str(repo), "query": "kafka billing invoices"}).structured_content

    assert data == {"status": "no_match", "query": "kafka billing invoices"}


def test_bad_repo_path_is_a_tool_error_not_a_crash(tmp_path):
    result = _call("scan", {"repo_path": str(tmp_path / "missing")})

    assert result.is_error is True
    assert "not a directory" in result.content[0].text


def test_empty_query_is_a_tool_error(tmp_path):
    repo = _make_repo(tmp_path)

    result = _call("slice", {"repo_path": str(repo), "query": "   "})

    assert result.is_error is True
    assert "query must be non-empty" in result.content[0].text


def test_generate_diagram_writes_drawio_for_whole_repo(tmp_path):
    repo = _make_repo(tmp_path)

    result = _call("generate_diagram", {"repo_path": str(repo)})

    assert result.is_error is False
    data = result.structured_content
    assert data["status"] == "ok"
    out = Path(data["output_path"])
    assert out == repo.resolve() / "rudhmap.drawio"
    xml = out.read_text(encoding="utf-8")
    assert xml.startswith("<mxfile")
    assert 'rudhmap_id="app/service.py:handle_upload"' in xml
    assert data["nodes"] > 0 and data["edges"] > 0


def test_generate_diagram_for_query_uses_slug_and_custom_path(tmp_path):
    repo = _make_repo(tmp_path)

    default = _call("generate_diagram", {"repo_path": str(repo), "query": "handle upload"})
    assert Path(default.structured_content["output_path"]).name == "rudhmap-handle-upload.drawio"

    custom = tmp_path / "out" / "mine.drawio"
    result = _call("generate_diagram", {"repo_path": str(repo), "query": "handle upload", "output_path": str(custom)})
    assert result.structured_content["output_path"] == str(custom.resolve())
    assert custom.is_file()


def test_generate_diagram_writes_nothing_on_no_match(tmp_path):
    repo = _make_repo(tmp_path)

    data = _call("generate_diagram", {"repo_path": str(repo), "query": "kafka billing invoices"}).structured_content

    assert data == {"status": "no_match", "query": "kafka billing invoices"}
    assert not list(repo.glob("*.drawio"))


def test_generate_diagram_refuses_non_drawio_output_path(tmp_path):
    repo = _make_repo(tmp_path)
    precious = tmp_path / "notes.txt"
    precious.write_text("keep me", encoding="utf-8")

    result = _call("generate_diagram", {"repo_path": str(repo), "output_path": str(precious)})

    assert result.is_error is True
    assert precious.read_text(encoding="utf-8") == "keep me"


def test_slice_on_exact_node_id_skips_search(tmp_path):
    repo = _make_repo(tmp_path)

    data = _call("slice", {"repo_path": str(repo), "query": "app/store.py:_write"}).structured_content

    assert data["status"] == "ok"
    assert data["seed_ids"] == ["app/store.py:_write"]
    assert "app/store.py:save_upload" in {n["id"] for n in data["nodes"]}


def test_get_context_returns_cited_source_pack(tmp_path):
    repo = _make_repo(tmp_path)

    result = _call("get_context", {"repo_path": str(repo), "query": "handle upload"})

    assert result.is_error is False
    data = result.structured_content
    assert data["status"] == "ok"
    assert "- app/service.py:handle_upload -> app/store.py:save_upload [calls @ app/service.py:5]" in data["context"]
    assert "### app/store.py:save_upload (function, app/store.py:1-2)" in data["context"]
    assert "return _write(data)" in data["context"]
    assert str(tmp_path) not in data["context"]
    assert 0 < data["approx_tokens"] <= 6000


def test_get_context_no_match_and_bad_budget(tmp_path):
    repo = _make_repo(tmp_path)

    data = _call("get_context", {"repo_path": str(repo), "query": "kafka billing invoices"}).structured_content
    assert data == {"status": "no_match", "query": "kafka billing invoices"}

    result = _call("get_context", {"repo_path": str(repo), "query": "upload", "token_budget": 10})
    assert result.is_error is True
