from pathlib import Path

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.extract.tier2_ast.typescript import parse_typescript_ast
from rudhmap.graph.assemble import assemble_graph
from rudhmap.graph.resolve import resolve_cross_file_calls, resolve_same_scope_calls

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def _node(identity: str, file: str, **kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=identity,
        file=file,
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
    )


def _call_edge(src: str, file: str, chain: list[str], resolved_module=None, resolved_name=None, **kwargs) -> EdgeRecord:
    attrs = {"callee_chain": chain, "likely_import_alias": True}
    if resolved_module is not None:
        attrs["resolved_module"] = resolved_module
        attrs["resolved_name"] = resolved_name
    return EdgeRecord(
        src=src,
        dst=".".join(chain),
        file=file,
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        attrs=attrs,
    )


def test_ts_relative_import_resolves_to_target_file_node():
    nodes = [
        _node("app.ts:Handler.process", "app.ts"),
        _node("ingest/writer.ts:putObject", "ingest/writer.ts"),
    ]
    edge = _call_edge(
        "app.ts:Handler.process", "app.ts", ["writeObject"],
        resolved_module="./ingest/writer", resolved_name="putObject",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.has_edge("app.ts:Handler.process", "ingest/writer.ts:putObject")
    assert result.dropped_edges == []


def test_python_dotted_import_resolves_via_unambiguous_suffix_match():
    nodes = [
        _node("app.py:Handler.process", "app.py"),
        _node("ingest/writer.py:put_object", "ingest/writer.py"),
    ]
    edge = _call_edge(
        "app.py:Handler.process", "app.py", ["write_object"],
        resolved_module="ingest.writer", resolved_name="put_object",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.has_edge("app.py:Handler.process", "ingest/writer.py:put_object")
    assert result.dropped_edges == []


def test_ambiguous_python_suffix_match_across_two_files_stays_dropped():
    nodes = [
        _node("app.py:Handler.process", "app.py"),
        _node("pkg_a/writer.py:put_object", "pkg_a/writer.py"),
        _node("pkg_b/writer.py:put_object", "pkg_b/writer.py"),
    ]
    edge = _call_edge(
        "app.py:Handler.process", "app.py", ["write_object"],
        resolved_module="writer", resolved_name="put_object",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_bare_ts_module_specifier_is_never_resolved():
    """A non-relative specifier like "boto3" is an external package --
    nothing was ever scanned for it, so it must never attempt resolution."""
    nodes = [_node("app.ts:Handler.process", "app.ts")]
    edge = _call_edge(
        "app.ts:Handler.process", "app.ts", ["s3Client"],
        resolved_module="boto3", resolved_name="S3Client",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_python_leading_dot_relative_import_is_left_unresolved():
    nodes = [
        _node("app.py:Handler.process", "app.py"),
        _node("writer.py:put_object", "writer.py"),
    ]
    edge = _call_edge(
        "app.py:Handler.process", "app.py", ["write_object"],
        resolved_module=".writer", resolved_name="put_object",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_no_matching_target_node_leaves_edge_dropped():
    nodes = [_node("app.ts:Handler.process", "app.ts")]  # ingest/writer.ts never scanned
    edge = _call_edge(
        "app.ts:Handler.process", "app.ts", ["writeObject"],
        resolved_module="./ingest/writer", resolved_name="putObject",
    )
    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_real_python_fixture_still_leaves_write_object_dropped_since_ingest_writer_not_scanned():
    """The fixture repo only contains app.py -- ingest/writer.py was never
    scanned, so even with resolved_module/resolved_name present, this must
    stay a legitimate drop, not a fabricated match."""
    nodes, edges = parse_python_ast(FIXTURE)
    result = resolve_cross_file_calls(resolve_same_scope_calls(assemble_graph(nodes, edges)))

    write_edges = [e for e in result.dropped_edges if e.attrs.get("callee_chain") == ["write_object"]]
    assert len(write_edges) == 1
    assert write_edges[0].attrs["resolved_module"] == "ingest.writer"


def test_real_typescript_fixture_still_leaves_write_object_dropped_since_ingest_writer_not_scanned():
    nodes, edges = parse_typescript_ast(FIXTURE)
    result = resolve_cross_file_calls(resolve_same_scope_calls(assemble_graph(nodes, edges)))

    write_edges = [e for e in result.dropped_edges if e.attrs.get("callee_chain") == ["writeObject"]]
    assert len(write_edges) == 1
    assert write_edges[0].attrs["resolved_module"] == "./ingest/writer"


# --- attribute calls through an imported name (module or class) -----------


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolved_pairs(root: Path) -> set[tuple[str, str]]:
    nodes, edges = parse_python_ast(str(root))
    result = resolve_cross_file_calls(resolve_same_scope_calls(assemble_graph(nodes, edges)))
    prefix = str(root) + "\\" if "\\" in str(root) else str(root) + "/"

    def rel(identity: str) -> str:
        return identity.removeprefix(prefix).replace("\\", "/")

    return {(rel(u), rel(v)) for u, v in result.graph.edges()}


_CRUD = "def create_user(db, name):\n    return name\n"


def test_module_imported_from_package_then_attribute_call_resolves(tmp_path):
    _write(tmp_path, "app/db/crud.py", _CRUD)
    _write(tmp_path, "app/api/user.py", "from app.db import crud\n\n\ndef create_user(req):\n    return crud.create_user(None, req)\n")

    assert ("app/api/user.py:create_user", "app/db/crud.py:create_user") in _resolved_pairs(tmp_path)


def test_aliased_module_import_then_attribute_call_resolves(tmp_path):
    _write(tmp_path, "app/db/crud.py", _CRUD)
    _write(tmp_path, "app/api/user.py", "import app.db.crud as store\n\n\ndef handler(req):\n    return store.create_user(None, req)\n")

    assert ("app/api/user.py:handler", "app/db/crud.py:create_user") in _resolved_pairs(tmp_path)


def test_unaliased_dotted_import_full_path_call_resolves(tmp_path):
    _write(tmp_path, "app/db/crud.py", _CRUD)
    _write(tmp_path, "app/api/user.py", "import app.db.crud\n\n\ndef handler(req):\n    return app.db.crud.create_user(None, req)\n")

    assert ("app/api/user.py:handler", "app/db/crud.py:create_user") in _resolved_pairs(tmp_path)


def test_class_imported_then_method_call_resolves_to_the_method(tmp_path):
    _write(tmp_path, "app/models.py", "class User:\n    @classmethod\n    def create(cls):\n        return cls()\n")
    _write(tmp_path, "app/api.py", "from app.models import User\n\n\ndef handler():\n    return User.create()\n")

    assert ("app/api.py:handler", "app/models.py:User.create") in _resolved_pairs(tmp_path)


def test_attribute_call_into_unscanned_package_stays_dropped(tmp_path):
    _write(tmp_path, "app/api.py", "import os\n\n\ndef handler(p):\n    return os.path.join(p, 'x')\n")

    assert _resolved_pairs(tmp_path) == set()


def test_attribute_call_with_two_valid_splits_stays_dropped():
    nodes = [
        _node("app/api.py:handler", "app/api.py"),
        _node("app/db.py:crud.create_user", "app/db.py"),  # attribute `crud` on module app/db.py
        _node("app/db/crud.py:create_user", "app/db/crud.py"),  # submodule app/db/crud.py
    ]
    edge = _call_edge("app/api.py:handler", "app/api.py", ["db", "crud", "create_user"])
    edge.attrs["resolved_dotted_path"] = "app.db.crud.create_user"

    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_module_suffix_match_respects_path_boundaries():
    nodes = [
        _node("app.py:Handler.process", "app.py"),
        _node("ingest/rewriter.py:put_object", "ingest/rewriter.py"),
    ]
    edge = _call_edge(
        "app.py:Handler.process", "app.py", ["put_object"],
        resolved_module="writer", resolved_name="put_object",
    )

    result = resolve_cross_file_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0


def _resolved_ts_pairs(root: Path) -> set[tuple[str, str]]:
    nodes, edges = parse_typescript_ast(str(root))
    result = resolve_cross_file_calls(resolve_same_scope_calls(assemble_graph(nodes, edges)))
    prefix = str(root) + ("\\" if "\\" in str(root) else "/")
    return {(u.removeprefix(prefix).replace("\\", "/"), v.removeprefix(prefix).replace("\\", "/")) for u, v in result.graph.edges()}


def test_ts_namespace_import_then_attribute_call_resolves(tmp_path):
    _write(tmp_path, "src/db/crud.ts", "export function createUser(name: string) {\n  return name;\n}\n")
    _write(tmp_path, "src/api/user.ts", "import * as crud from '../db/crud';\n\nexport function handler(n: string) {\n  return crud.createUser(n);\n}\n")

    assert ("src/api/user.ts:handler", "src/db/crud.ts:createUser") in _resolved_ts_pairs(tmp_path)


def test_ts_default_import_attribute_call_stays_dropped(tmp_path):
    _write(tmp_path, "src/db/crud.ts", "export function createUser(name: string) {\n  return name;\n}\n")
    _write(tmp_path, "src/api/user.ts", "import crud from '../db/crud';\n\nexport function handler(n: string) {\n  return crud.createUser(n);\n}\n")

    assert ("src/api/user.ts:handler", "src/db/crud.ts:createUser") not in _resolved_ts_pairs(tmp_path)
