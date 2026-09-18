from pathlib import Path

from rudhmap.extract.tier2_ast.typescript import parse_typescript_ast

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def test_defs_get_local_file_scoped_identity():
    nodes, _ = parse_typescript_ast(FIXTURE)
    by_qualname = {n.attrs["qualname"]: n for n in nodes}

    assert set(by_qualname) == {
        "Handler",
        "Handler.process",
        "Handler.validate",
        "handlePost",
        "doLocalWork",
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
    _, edges = parse_typescript_ast(FIXTURE)
    imports = [e for e in edges if e.attrs.get("kind") == "import"]

    namespace = next(e for e in imports if e.attrs["module"] == "boto3")
    assert namespace.attrs["names"] == ["*"]
    assert namespace.dst == "boto3"
    assert namespace.src == namespace.file  # module-level import, no enclosing scope

    named = next(e for e in imports if e.attrs["module"] == "./ingest/writer")
    assert named.attrs["names"] == ["putObject"]
    assert named.attrs["raw"] == 'import { putObject as writeObject } from "./ingest/writer";'


def test_call_edges_carry_callee_chain_as_a_list():
    _, edges = parse_typescript_ast(FIXTURE)
    calls = [e for e in edges if "callee_chain" in e.attrs]

    boto_call = next(e for e in calls if e.attrs["callee_chain"] == ["boto3", "client"])
    assert boto_call.attrs["likely_import_alias"] is True  # "boto3" is bound by `import * as boto3`
    assert boto_call.src == boto_call.file  # module-level call site

    write_call = next(e for e in calls if e.attrs["callee_chain"] == ["writeObject"])
    assert write_call.attrs["likely_import_alias"] is True  # bound by the `as writeObject` alias
    assert write_call.src == f"{write_call.file}:Handler.process"
    # bare call of a named-import binding -- resolvable cross-file
    assert write_call.attrs["resolved_module"] == "./ingest/writer"
    assert write_call.attrs["resolved_name"] == "putObject"

    assert "resolved_module" not in boto_call.attrs  # namespace import + attr access, not resolved

    this_call = next(e for e in calls if e.attrs["callee_chain"] == ["this", "validate"])
    assert this_call.attrs["likely_import_alias"] is False  # "this" is not an import

    local_call = next(e for e in calls if e.attrs["callee_chain"] == ["doLocalWork"])
    assert local_call.attrs["likely_import_alias"] is False  # local def, not an import
    assert local_call.src == f"{local_call.file}:handlePost"


def test_decorator_call_is_captured_at_enclosing_scope():
    _, edges = parse_typescript_ast(FIXTURE)
    calls = [e for e in edges if "callee_chain" in e.attrs]
    deco_call = next(e for e in calls if e.attrs["callee_chain"] == ["Route"])
    assert deco_call.src == f"{deco_call.file}:Handler"  # decorator runs at class scope, not inside process
    assert deco_call.line == 7


def test_no_filesystem_resolution_happens_in_tier2(tmp_path):
    # An import referencing a module that doesn't exist on disk anywhere
    # near this fixture must still emit a normal dangling edge -- tier2
    # never touches the filesystem to check whether "module" resolves.
    (tmp_path / "a.ts").write_text('import "totally_nonexistent_module";\n')
    _, edges = parse_typescript_ast(tmp_path)
    assert len(edges) == 1
    assert edges[0].attrs["module"] == "totally_nonexistent_module"


def test_skips_vendor_and_venv_dirs(tmp_path):
    for d in ("vendor", "node_modules", "venv", ".venv", "__pycache__"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "x.ts").write_text('import boto3 from "boto3";\n')
    nodes, edges = parse_typescript_ast(tmp_path)
    assert nodes == []
    assert edges == []


def test_unreadable_file_does_not_crash_scan(tmp_path):
    (tmp_path / "broken.ts").write_bytes(b"\xff\xfeimport boto3\xff")
    nodes, edges = parse_typescript_ast(tmp_path)
    assert isinstance(nodes, list)
    assert isinstance(edges, list)


def test_tsx_files_are_parsed_with_the_tsx_grammar(tmp_path):
    (tmp_path / "widget.tsx").write_text(
        "function Widget() {\n  return <div>hi</div>;\n}\n"
    )
    nodes, _ = parse_typescript_ast(tmp_path)
    assert [n.attrs["qualname"] for n in nodes] == ["Widget"]
