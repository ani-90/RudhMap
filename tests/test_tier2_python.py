from pathlib import Path

from rudhmap.extract.tier2_ast.python import parse_python_ast

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def test_defs_get_local_file_scoped_identity():
    nodes, _ = parse_python_ast(FIXTURE)
    by_qualname = {n.attrs["qualname"]: n for n in nodes}

    assert set(by_qualname) == {
        "Handler",
        "Handler.process",
        "Handler.validate",
        "handle_post",
        "do_local_work",
    }

    handler = by_qualname["Handler"]
    assert handler.kind == "class"
    assert handler.identity == f"{handler.file}:Handler"
    assert handler.tier == 2
    assert handler.confidence == 1.0

    process = by_qualname["Handler.process"]
    assert process.kind == "function"
    assert process.identity == f"{process.file}:Handler.process"


def test_import_edges_are_structured_not_joined_strings():
    _, edges = parse_python_ast(FIXTURE)
    imports = [e for e in edges if e.attrs.get("kind") == "import"]

    plain = next(e for e in imports if e.attrs["module"] == "boto3")
    assert plain.attrs["names"] == []
    assert plain.dst == "boto3"
    assert plain.src == plain.file  # module-level import, no enclosing scope

    aliased = next(e for e in imports if e.attrs["module"] == "ingest.writer")
    assert aliased.attrs["names"] == ["put_object"]
    assert aliased.attrs["raw"] == "from ingest.writer import put_object as write_object"


def test_call_edges_carry_callee_chain_as_a_list():
    _, edges = parse_python_ast(FIXTURE)
    calls = [e for e in edges if "callee_chain" in e.attrs]

    boto_call = next(e for e in calls if e.attrs["callee_chain"] == ["boto3", "client"])
    assert boto_call.attrs["likely_import_alias"] is True  # "boto3" is bound by `import boto3`
    assert boto_call.src == boto_call.file  # module-level call site

    write_call = next(e for e in calls if e.attrs["callee_chain"] == ["write_object"])
    assert write_call.attrs["likely_import_alias"] is True  # bound by the `as write_object` alias
    assert write_call.src == f"{write_call.file}:Handler.process"
    # bare call of a `from module import name as alias` binding -- resolvable cross-file
    assert write_call.attrs["resolved_module"] == "ingest.writer"
    assert write_call.attrs["resolved_name"] == "put_object"

    assert "resolved_module" not in boto_call.attrs  # whole-module import + attr access, not resolved

    self_call = next(e for e in calls if e.attrs["callee_chain"] == ["self", "validate"])
    assert self_call.attrs["likely_import_alias"] is False  # "self" is not an import

    local_call = next(e for e in calls if e.attrs["callee_chain"] == ["do_local_work"])
    assert local_call.attrs["likely_import_alias"] is False  # local def, not an import
    assert local_call.src == f"{local_call.file}:handle_post"


def test_decorator_call_is_captured_at_enclosing_scope():
    _, edges = parse_python_ast(FIXTURE)
    calls = [e for e in edges if "callee_chain" in e.attrs]
    deco_call = next(e for e in calls if e.attrs["callee_chain"] == ["app", "route"])
    assert deco_call.src == deco_call.file  # decorator runs at module scope, not inside handle_post
    assert deco_call.line == 16


def test_no_filesystem_resolution_happens_in_tier2(tmp_path):
    # An import referencing a module that doesn't exist on disk anywhere
    # near this fixture must still emit a normal dangling edge -- tier2
    # never touches the filesystem to check whether "module" resolves.
    (tmp_path / "a.py").write_text("import totally_nonexistent_module\n")
    _, edges = parse_python_ast(tmp_path)
    assert len(edges) == 1
    assert edges[0].attrs["module"] == "totally_nonexistent_module"


def test_skips_vendor_and_venv_dirs(tmp_path):
    for d in ("vendor", "node_modules", "venv", ".venv", "__pycache__"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "x.py").write_text("import boto3\n")
    nodes, edges = parse_python_ast(tmp_path)
    assert nodes == []
    assert edges == []


def test_skips_test_dirs(tmp_path):
    """A repo's own test suite isn't architecture -- excluded the same way
    as vendor/build output, not because it's worthless but because a
    widely-shared utility's twenty test callers would otherwise dominate a
    slice query's node budget instead of the real production-code
    neighborhood. See eval/cases.md, "test file exclusion"."""
    for d in ("tests", "test", "__tests__", "spec", "specs"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "test_x.py").write_text("def test_thing():\n    pass\n")
    nodes, edges = parse_python_ast(tmp_path)
    assert nodes == []
    assert edges == []


def test_unreadable_file_does_not_crash_scan(tmp_path):
    (tmp_path / "broken.py").write_bytes(b"\xff\xfeimport boto3\xff")
    nodes, edges = parse_python_ast(tmp_path)
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
