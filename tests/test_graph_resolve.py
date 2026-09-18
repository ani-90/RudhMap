from pathlib import Path

from rudhmap.extract.schema import EdgeRecord, EvidenceRecord
from rudhmap.extract.tier2_ast.python import parse_python_ast
from rudhmap.extract.tier2_ast.typescript import parse_typescript_ast
from rudhmap.graph.assemble import assemble_graph
from rudhmap.graph.resolve import resolve_same_scope_calls

FIXTURE = Path(__file__).parent / "fixtures" / "tier2_ast"


def _node(identity: str, **kwargs) -> EvidenceRecord:
    return EvidenceRecord(
        kind=kwargs.pop("kind", "function"),
        identity=identity,
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
    )


def _call_edge(src: str, chain: list[str], **kwargs) -> EdgeRecord:
    return EdgeRecord(
        src=src,
        dst=".".join(chain),
        file=kwargs.pop("file", "app.py"),
        line=kwargs.pop("line", 1),
        tier=kwargs.pop("tier", 2),
        confidence=kwargs.pop("confidence", 1.0),
        attrs={"callee_chain": chain, "likely_import_alias": kwargs.pop("likely_import_alias", False)},
    )


def test_self_dot_call_resolves_to_sibling_method_in_same_class():
    nodes = [_node("app.py:Handler.process"), _node("app.py:Handler.validate")]
    edge = _call_edge("app.py:Handler.process", ["self", "validate"])
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert result.graph.has_edge("app.py:Handler.process", "app.py:Handler.validate")
    assert result.dropped_edges == []


def test_bare_call_resolves_to_module_level_function_in_same_file():
    nodes = [_node("app.py:handle_post"), _node("app.py:do_local_work")]
    edge = _call_edge("app.py:handle_post", ["do_local_work"])
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert result.graph.has_edge("app.py:handle_post", "app.py:do_local_work")
    assert result.dropped_edges == []


def test_import_aliased_bare_call_is_not_resolved():
    """write_object(batch) where write_object came from an import -- cross-file,
    step B's job, not step A's."""
    nodes = [_node("app.py:Handler.process"), _node("app.py:write_object")]
    edge = _call_edge(
        "app.py:Handler.process", ["write_object"], likely_import_alias=True
    )
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert not result.graph.has_edge("app.py:Handler.process", "app.py:write_object")
    assert result.dropped_edges == [edge]


def test_call_through_non_self_receiver_is_not_resolved():
    """obj.method() where obj isn't self/this -- would need type info, not
    deterministically resolvable, must stay dropped."""
    nodes = [_node("app.py:handler"), _node("app.py:Obj.method")]
    edge = _call_edge("app.py:handler", ["obj", "method"])
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_module_scope_call_target_does_not_auto_create_a_phantom_src_node():
    """A call written at bare module scope has src == file path, which was
    never itself extracted as a node. Resolution must not silently
    auto-vivify it via add_edge."""
    nodes = [_node("app.py:initialize")]
    edge = _call_edge("app.py", ["initialize"])  # src is the bare file, not a node
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert "app.py" not in result.graph.nodes
    assert result.dropped_edges == [edge]


def test_candidate_node_missing_leaves_edge_dropped():
    nodes = [_node("app.py:Handler.process")]
    edge = _call_edge("app.py:Handler.process", ["self", "not_declared"])
    result = resolve_same_scope_calls(assemble_graph(nodes, [edge]))

    assert result.graph.number_of_edges() == 0
    assert result.dropped_edges == [edge]


def test_real_python_fixture_resolves_self_and_bare_calls():
    nodes, edges = parse_python_ast(FIXTURE)
    before = assemble_graph(nodes, edges)
    after = resolve_same_scope_calls(before)

    file_str = str(FIXTURE / "app.py")
    assert after.graph.has_edge(f"{file_str}:Handler.process", f"{file_str}:Handler.validate")
    assert after.graph.has_edge(f"{file_str}:handle_post", f"{file_str}:do_local_work")
    assert len(after.dropped_edges) < len(before.dropped_edges)


def test_real_typescript_fixture_resolves_this_and_bare_calls():
    nodes, edges = parse_typescript_ast(FIXTURE)
    before = assemble_graph(nodes, edges)
    after = resolve_same_scope_calls(before)

    file_str = str(FIXTURE / "app.ts")
    assert after.graph.has_edge(f"{file_str}:Handler.process", f"{file_str}:Handler.validate")
    assert after.graph.has_edge(f"{file_str}:handlePost", f"{file_str}:doLocalWork")
    assert len(after.dropped_edges) < len(before.dropped_edges)
