"""Step 1 engine fixes, end to end through `build_assembly`: each test writes a
tiny repo, builds the graph, and checks one connection is (or is not) drawn.
Negative cases matter as much as positive ones: the resolver must never
connect a name it can't prove."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from rudhmap.paths import Relativizer
from rudhmap.pipeline import build_assembly


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _edges(root: Path) -> set[tuple[str, str, str]]:
    """(src, dst, relation) with repo-relative ids; module nodes as `file:<module>`."""
    assembly = build_assembly(str(root), verbose=False).result
    rel = Relativizer(root)
    graph = assembly.graph
    files = {ev.file for _, d in graph.nodes(data=True) for ev in d["evidence"]}

    def name(n: str) -> str:
        return f"{rel(n)}:<module>" if n in files else rel(n)

    out = set()
    for u, v, d in graph.edges(data=True):
        ev = d["evidence"]
        if ev.attrs.get("kind") == "import":
            continue
        out.add((name(u), name(v), ev.attrs.get("relation", "calls")))
    return out


def test_nested_function_call_resolves_to_enclosing_scope(tmp_path):
    _write(tmp_path, {"a.py": (
        "def outer():\n"
        "    def helper():\n"
        "        return 1\n"
        "    def inner():\n"
        "        return helper()\n"
        "    return inner()\n"
    )})
    edges = _edges(tmp_path)
    assert ("a.py:outer.inner", "a.py:outer.helper", "calls") in edges
    assert ("a.py:outer", "a.py:outer.inner", "calls") in edges


def test_method_cannot_call_sibling_method_unqualified(tmp_path):
    # Python scoping: class bodies aren't visible from methods, so a bare
    # `validate()` inside a method means the module-level one.
    _write(tmp_path, {"a.py": (
        "def validate():\n"
        "    return 0\n"
        "class A:\n"
        "    def validate(self):\n"
        "        return 1\n"
        "    def run(self):\n"
        "        return validate()\n"
    )})
    edges = _edges(tmp_path)
    assert ("a.py:A.run", "a.py:validate", "calls") in edges
    assert ("a.py:A.run", "a.py:A.validate", "calls") not in edges


def test_top_level_code_has_a_module_caller(tmp_path):
    _write(tmp_path, {"config.py": "class Settings:\n    pass\n\nsettings = Settings()\n"})
    assert ("config.py:<module>", "config.py:Settings", "calls") in _edges(tmp_path)


def test_method_call_on_constructed_local_resolves(tmp_path):
    _write(tmp_path, {
        "store.py": "class Store:\n    def put(self, x):\n        return x\n",
        "app.py": "from store import Store\n\ndef save(x):\n    s = Store()\n    return s.put(x)\n",
    })
    assert ("app.py:save", "store.py:Store.put", "calls") in _edges(tmp_path)


def test_method_call_on_annotated_parameter_resolves(tmp_path):
    _write(tmp_path, {
        "models.py": "class Request:\n    def domains(self):\n        return []\n",
        "api.py": (
            "from typing import Optional\n"
            "from models import Request\n\n"
            "def a(req: Request):\n    return req.domains()\n\n"
            "def b(req: Optional[Request]):\n    return req.domains()\n\n"
            "def c(req: Request | None):\n    return req.domains()\n"
        ),
    })
    edges = _edges(tmp_path)
    for fn in ("a", "b", "c"):
        assert (f"api.py:{fn}", "models.py:Request.domains", "calls") in edges


def test_container_annotation_is_not_a_receiver_type(tmp_path):
    # `items: List[Item]` -> items.append() is a list method, not Item.append.
    _write(tmp_path, {"a.py": (
        "from typing import List\n"
        "class Item:\n    def append(self, x):\n        return x\n"
        "def f(items: List[Item]):\n    items.append(1)\n"
    )})
    assert not any(dst == "a.py:Item.append" for _, dst, _ in _edges(tmp_path))


def test_untyped_rebinding_clears_a_known_type(tmp_path):
    _write(tmp_path, {"a.py": (
        "class Store:\n    def put(self, x):\n        return x\n"
        "def other():\n    return 1\n"
        "def f(make):\n    s = Store()\n    s = make()\n    return s.put(1)\n"
    )})
    assert ("a.py:f", "a.py:Store.put", "calls") not in _edges(tmp_path)


def test_self_attribute_type_from_init_resolves(tmp_path):
    _write(tmp_path, {
        "client.py": "class Client:\n    def search(self, q):\n        return q\n",
        "service.py": (
            "from client import Client\n\n"
            "class Service:\n"
            "    def __init__(self):\n        self.client = Client()\n"
            "    def find(self, q):\n        return self.client.search(q)\n"
        ),
    })
    assert ("service.py:Service.find", "client.py:Client.search", "calls") in _edges(tmp_path)


def test_inherited_method_and_inherits_edge_resolve_across_files(tmp_path):
    _write(tmp_path, {
        "base.py": "class Base:\n    def fetch(self):\n        return 1\n",
        "child.py": (
            "from base import Base\n\n"
            "class Child(Base):\n    def run(self):\n        return self.fetch()\n"
        ),
    })
    edges = _edges(tmp_path)
    assert ("child.py:Child", "base.py:Base", "inherits") in edges
    assert ("child.py:Child.run", "base.py:Base.fetch", "calls") in edges


def test_definitions_passed_as_values_become_references(tmp_path):
    _write(tmp_path, {
        "db.py": "def get_db():\n    yield 1\n",
        "api.py": (
            "from db import get_db\n\n"
            "def _bg(x):\n    return x\n\n"
            "def route(tasks, db=Depends(get_db)):\n"
            "    tasks.add_task(_bg, 1)\n"
            "    tasks.add_task(func=_bg)\n"
        ),
    })
    edges = _edges(tmp_path)
    assert ("api.py:route", "api.py:_bg", "references") in edges
    assert ("api.py:route", "db.py:get_db", "references") in edges


def test_local_variable_with_a_definitions_name_is_not_a_reference(tmp_path):
    _write(tmp_path, {"a.py": (
        "def result():\n    return 1\n"
        "def f(result):\n    print(result)\n"
        "def g():\n    result = 2\n    print(result)\n"
    )})
    edges = _edges(tmp_path)
    assert ("a.py:f", "a.py:result", "references") not in edges
    assert ("a.py:g", "a.py:result", "references") not in edges


def test_decorator_arguments_belong_to_the_decorated_route(tmp_path):
    _write(tmp_path, {"api.py": (
        "class Resp:\n    pass\n\n"
        "@router.post('/x', response_model=Resp)\n"
        "def route():\n    return 1\n"
    )})
    assert ("api.py:route", "api.py:Resp", "references") in _edges(tmp_path)


def test_unresolved_references_are_not_reported_as_dropped(tmp_path):
    _write(tmp_path, {"a.py": "def f(x):\n    y = 1\n    print(y, x, undefined_name)\n"})
    dropped = build_assembly(str(tmp_path), verbose=False).result.dropped_edges
    assert not any(e.attrs.get("relation") == "references" for e in dropped)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_git_ignored_files_and_tool_folders_are_not_scanned(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _write(tmp_path, {
        ".gitignore": "generated/\n",
        "app.py": "def real():\n    return 1\n",
        "generated/out.py": "def ignored():\n    return 1\n",
        ".claude/worktrees/copy/app.py": "def real():\n    return 1\n",
    })
    nodes = set(build_assembly(str(tmp_path), verbose=False).result.graph.nodes)
    rel = Relativizer(tmp_path)
    assert {rel(n) for n in nodes} == {"app.py", "app.py:real"}
