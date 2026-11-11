"""Step B tools (find_symbol, show, trace, repo_map) on a small fixture repo:
exact expected content, budgets, ambiguity, freshness after an edit."""
from __future__ import annotations

import time
from pathlib import Path

from rudhmap.tools import views
from rudhmap.tools.index import RepoIndex

FILES = {
    "app/api.py": (
        "from fastapi import APIRouter, BackgroundTasks\n"
        "from app.crud import get_item\n"
        "from app.work import build_pipeline\n\n"
        'router = APIRouter(prefix="/api/items")\n\n'
        "pipeline = build_pipeline()\n\n\n"
        '@router.post("/refresh")\n'
        "def refresh(tasks: BackgroundTasks, db=None):\n"
        '    """Refresh items in the background."""\n'
        "    item = get_item(db, 1)\n"
        "    tasks.add_task(_run_bg, item)\n"
        "    return item\n\n\n"
        "def _run_bg(item):\n"
        "    return pipeline.run(item)\n"
    ),
    "app/crud.py": (
        "SECRET_LIMIT = 10\n\n\n"
        "def get_item(db, item_id):\n"
        "    return db.get(item_id, SECRET_LIMIT)\n\n\n"
        "def embed(text):\n"
        "    return []\n"
    ),
    "app/work.py": (
        "from app.crud import embed\n\n\n"
        "def step_one(x):\n"
        "    return embed(x)\n\n\n"
        "def build_pipeline():\n"
        "    return register(step_one)\n\n\n"
        "def register(fn):\n"
        "    return fn\n"
    ),
    "app/transport.py": (
        "class Base:\n"
        "    def handle(self, request) -> str:\n"
        '        """Send one request."""\n'
        "        raise NotImplementedError\n\n\n"
        "class Fast(Base):\n"
        "    def handle(self, request) -> str:\n"
        "        return 'fast'\n\n\n"
        "class Client:\n"
        "    def pick(self) -> Base:\n"
        "        return Fast()\n\n"
        "    def send(self, request):\n"
        "        transport = self.pick()\n"
        "        return transport.handle(request)\n"
    ),
    "app/other.py": "def get_item(x):\n    return x\n",
}


def _repo(tmp_path: Path) -> RepoIndex:
    for rel, text in FILES.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    RepoIndex._instances.clear()
    return RepoIndex.get(tmp_path)


def test_show_lists_body_callees_tiny_bodies_callers_and_route(tmp_path):
    index = _repo(tmp_path)
    out = views.show(index, "refresh")
    assert out.splitlines()[0].startswith("app/api.py:11-15  def refresh(")
    assert "HTTP route: POST /api/items/refresh" in out
    assert "13      item = get_item(db, 1)" in out          # numbered source lines
    assert "get_item(db, item_id)  -> app/crud.py:4" in out  # callee with signature + location
    assert "return db.get(item_id, SECRET_LIMIT)" in out      # tiny callee body inline
    assert "[passed as value]" in out and "_run_bg" in out    # background task as a reference
    assert "called by: HTTP clients (POST /api/items/refresh)" in out


def test_show_ambiguous_name_returns_candidate_ids(tmp_path):
    index = _repo(tmp_path)
    # app/api.py imports get_item from crud, but the bare name exists in two files.
    out = views.show(index, "get_item")
    assert "matches 2 symbols" in out
    assert "app/crud.py:get_item" in out and "app/other.py:get_item" in out
    assert views.show(index, "app/crud.py:get_item").startswith("app/crud.py:4-5")


def test_show_method_lists_overrides_and_return_type_call_site(tmp_path):
    index = _repo(tmp_path)
    out = views.show(index, "Base.handle", "outline")
    assert "overridden by: Fast.handle (app/transport.py:" in out
    # `transport = self.pick()` with `def pick(self) -> Base` types transport as Base.
    assert "Client.send" in out


def test_trace_goes_through_background_task_and_module_value(tmp_path):
    index = _repo(tmp_path)
    out = views.trace(index, "refresh", "embed")
    assert "_run_bg [passed as value]" in out
    assert "build_pipeline [uses value it builds]" in out
    assert "step_one [passed as value]" in out
    assert out.strip().endswith("(L5 -> app/crud.py:8)")


def test_trace_up_lists_callers_and_says_when_none(tmp_path):
    index = _repo(tmp_path)
    assert "Client.send" in views.trace(index, "Base.handle", None, "up")
    assert "(no callers in this repo)" in views.trace(index, "refresh", None, "up")


def test_find_symbol_ranks_exact_name_first_and_finds_identifier_usages(tmp_path):
    index = _repo(tmp_path)
    assert views.find_symbol(index, "build pipeline").splitlines()[1].split()[1] == "app/work.py:8"
    usage = views.find_symbol(index, "SECRET_LIMIT")
    assert "is not a function/class name; it appears on 2 lines" in usage
    assert "app/crud.py:5  [get_item]" in usage


def test_repo_map_lists_files_routes_and_stays_in_budget(tmp_path):
    index = _repo(tmp_path)
    out = views.repo_map(index)
    assert "1 HTTP routes" in out and "refresh [POST /api/items/refresh]" in out
    assert views.tokens(out) <= views.MAP_BUDGET
    assert "No source files under" in views.repo_map(index, "nope")


def test_long_body_is_cut_with_a_pointer_to_the_rest(tmp_path):
    body = "".join(f"    x{i} = {i}  # " + "padding " * 8 + "\n" for i in range(400))
    (tmp_path / "big.py").write_text("def huge():\n" + body + "    return 0\n", encoding="utf-8")
    RepoIndex._instances.clear()
    out = views.show(RepoIndex.get(tmp_path), "huge")
    assert views.tokens(out) <= views.SHOW_BUDGET
    assert "body cut at line" in out and "Read big.py:" in out


def test_index_rebuilds_after_a_file_changes(tmp_path):
    index = _repo(tmp_path)
    assert "No symbol" in views.show(index, "brand_new") or "matches" not in views.show(index, "brand_new")
    (tmp_path / "app" / "crud.py").write_text(FILES["app/crud.py"] + "\n\ndef brand_new():\n    return 1\n",
                                              encoding="utf-8")
    time.sleep(0.6)
    out = views.show(RepoIndex.get(tmp_path), "brand_new")
    assert out.startswith("app/crud.py:")


def test_trace_tree_depth_ignores_indirection_hops(tmp_path):
    # refresh -> _run_bg [value] -> build_pipeline [built_by] -> step_one [value] -> embed:
    # only the last hop is a real call level, so embed is within the default depth 3.
    index = _repo(tmp_path)
    assert "embed" in views.trace(index, "refresh")


def test_absolute_paths_from_grep_output_resolve(tmp_path):
    index = _repo(tmp_path)
    absolute = str(tmp_path / "app" / "crud.py")
    assert views.show(index, absolute).startswith("app/crud.py")
    assert views.show(index, absolute + ":get_item").startswith("app/crud.py:4-5")


def test_mcp_server_exposes_the_four_tools_and_answers(tmp_path, monkeypatch):
    import anyio
    from mcp import Client

    from rudhmap.server import mcp

    _repo(tmp_path)
    monkeypatch.setenv("RUDHMAP_REPO", str(tmp_path))

    async def run():
        async with Client(mcp) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            result = await client.call_tool("show", {"symbol": "refresh"})
            return tools, result

    tools, result = anyio.run(run)
    assert tools == {"find_symbol", "show", "trace", "repo_map"}
    text = "".join(getattr(c, "text", "") for c in result.content)
    assert "HTTP route: POST /api/items/refresh" in text
