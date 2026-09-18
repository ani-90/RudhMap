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
