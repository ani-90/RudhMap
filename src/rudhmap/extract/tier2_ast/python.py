"""Tier 2 extractor: tree-sitter AST for Python.

Single-file parsing only. An import's module string and a call's callee
chain are emitted exactly as the AST states them -- resolving either
against another file's definitions is Stage 2 (graph assembly)'s job, not
this tier's. See docs/tier2_ast_schema.md for the emission contract this
module implements.
"""
from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Node, Parser, Tree
import tree_sitter_python as tspython

from rudhmap.cache import ExtractionCache
from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 2
CONFIDENCE = 1.0
_EXTRACTOR_NAME = "python"

_SKIP_DIRS = COMMON_SKIP_DIRS

_LANGUAGE = Language(tspython.language())


def _iter_py_files(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if path.suffix == ".py":
            yield path


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _flatten_callee(node: Node, source: bytes) -> list[str]:
    """Turn a call's `function` field into an attribute chain list, e.g.
    `writer.put_object` -> ["writer", "put_object"]. Falls back to the raw
    source text as a single-element chain for shapes that aren't a plain
    identifier/attribute walk (e.g. `foo()()`) -- rare, and still a
    faithful (if unstructured) record of what's there."""
    if node.type == "identifier":
        return [_text(node, source)]
    if node.type == "attribute":
        obj = node.child_by_field_name("object")
        attr = node.child_by_field_name("attribute")
        chain = _flatten_callee(obj, source) if obj is not None else []
        if attr is not None:
            chain = chain + [_text(attr, source)]
        return chain
    return [_text(node, source)]


def _process_file(py_file: Path, source: bytes, tree: Tree) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    file_str = str(py_file)
    # alias -> {"module": dotted module path, "name": original imported
    # name, or None for a whole-module import like `import x as y`}.
    # Kept separate (not concatenated) so a call resolving through this
    # table can tell "which file" apart from "which name in that file".
    import_table: dict[str, dict[str, str | None]] = {}

    def scope_identity(scope_stack: list[str]) -> str:
        return f"{file_str}:{'.'.join(scope_stack)}" if scope_stack else file_str

    def handle_import(node: Node, scope_stack: list[str]) -> None:
        raw = _text(node, source)
        line = _line(node)
        src_identity = scope_identity(scope_stack)

        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    module = _text(child, source)
                    import_table[module.split(".")[0]] = {"module": module, "name": None}
                    emit_import(src_identity, module, [], raw, line)
                elif child.type == "aliased_import":
                    dotted = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    module = _text(dotted, source) if dotted is not None else ""
                    alias_name = _text(alias, source) if alias is not None else module
                    import_table[alias_name] = {"module": module, "name": None}
                    emit_import(src_identity, module, [], raw, line)
        else:  # import_from_statement
            module_node = node.child_by_field_name("module_name")
            module = _text(module_node, source) if module_node is not None else ""
            names: list[str] = []
            for child in node.children:
                if module_node is not None and child.start_byte == module_node.start_byte and child.end_byte == module_node.end_byte:
                    continue
                if child.type == "dotted_name":
                    name = _text(child, source)
                    names.append(name)
                    import_table[name] = {"module": module, "name": name}
                elif child.type == "aliased_import":
                    dotted = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    name = _text(dotted, source) if dotted is not None else ""
                    alias_name = _text(alias, source) if alias is not None else name
                    names.append(name)
                    import_table[alias_name] = {"module": module, "name": name}
                elif child.type == "wildcard_import":
                    names.append("*")
            emit_import(src_identity, module, names, raw, line)

    def emit_import(src_identity: str, module: str, names: list[str], raw: str, line: int) -> None:
        edges.append(
            EdgeRecord(
                src=src_identity,
                dst=module,
                file=file_str,
                line=line,
                tier=TIER,
                confidence=CONFIDENCE,
                attrs={"kind": "import", "module": module, "names": names, "raw": raw},
            )
        )

    def handle_call(node: Node, scope_stack: list[str]) -> None:
        func = node.child_by_field_name("function")
        if func is None:
            return
        chain = _flatten_callee(func, source)
        if not chain:
            return
        import_entry = import_table.get(chain[0])
        likely_alias = import_entry is not None
        attrs = {"callee_chain": chain, "likely_import_alias": likely_alias}
        # Only a bare call of a `from module import name [as alias]`
        # binding is unambiguous enough to resolve cross-file -- a
        # whole-module import (import_entry["name"] is None) followed by
        # further attribute access could be an attribute on the
        # returned object, not a module path, so it's left unresolved.
        if likely_alias and len(chain) == 1 and import_entry["name"] is not None:
            attrs["resolved_module"] = import_entry["module"]
            attrs["resolved_name"] = import_entry["name"]
        edges.append(
            EdgeRecord(
                src=scope_identity(scope_stack),
                dst=".".join(chain),
                file=file_str,
                line=_line(node),
                tier=TIER,
                confidence=CONFIDENCE,
                attrs=attrs,
            )
        )

    def visit_def_or_class(node: Node, scope_stack: list[str], kind: str) -> None:
        name_node = node.child_by_field_name("name")
        name = _text(name_node, source) if name_node is not None else "<anonymous>"
        qualname = ".".join(scope_stack + [name])
        nodes.append(
            EvidenceRecord(
                kind=kind,
                identity=f"{file_str}:{qualname}",
                file=file_str,
                line=_line(node),
                tier=TIER,
                confidence=CONFIDENCE,
                attrs={"name": name, "qualname": qualname},
            )
        )
        body = node.child_by_field_name("body")
        if body is not None:
            walk(body, scope_stack + [name])

    def visit(node: Node, scope_stack: list[str]) -> None:
        if node.type == "decorated_definition":
            for deco in node.children:
                if deco.type == "decorator":
                    walk(deco, scope_stack)
            inner = node.child_by_field_name("definition")
            if inner is not None:
                visit(inner, scope_stack)
            return
        if node.type == "function_definition":
            visit_def_or_class(node, scope_stack, "function")
            return
        if node.type == "class_definition":
            visit_def_or_class(node, scope_stack, "class")
            return
        if node.type in ("import_statement", "import_from_statement"):
            handle_import(node, scope_stack)
            return
        if node.type == "call":
            handle_call(node, scope_stack)
            walk(node, scope_stack)
            return
        walk(node, scope_stack)

    def walk(node: Node, scope_stack: list[str]) -> None:
        for child in node.children:
            visit(child, scope_stack)

    walk(tree.root_node, [])

    return nodes, edges


def parse_python_ast(
    repo_path: str | Path, cache: ExtractionCache | None = None
) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    parser = Parser(_LANGUAGE)

    all_nodes: list[EvidenceRecord] = []
    all_edges: list[EdgeRecord] = []

    for py_file in _iter_py_files(repo_path):
        try:
            source = py_file.read_bytes()
            tree = parser.parse(source)
        except Exception:
            # Malformed/unreadable file: degrade gracefully, don't crash the scan.
            continue

        def compute(py_file=py_file, source=source, tree=tree):
            return _process_file(py_file, source, tree)

        if cache is not None:
            nodes, edges = cache.get_or_compute(py_file, _EXTRACTOR_NAME, compute)
        else:
            nodes, edges = compute()

        all_nodes.extend(nodes)
        all_edges.extend(edges)

    return all_nodes, all_edges
