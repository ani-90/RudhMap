"""Tier 2 extractor: tree-sitter AST for TypeScript/TSX.

Single-file parsing only. An import's module string and a call's callee
chain are emitted exactly as the AST states them -- resolving either
against another file's definitions is Stage 2 (graph assembly)'s job, not
this tier's. See docs/tier2_ast_schema.md for the emission contract this
module implements (same contract as the Python visitor).
"""
from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Node, Parser, Tree
import tree_sitter_typescript as tsts

from rudhmap.cache import ExtractionCache
from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 2
CONFIDENCE = 1.0
_EXTRACTOR_NAME = "typescript"

_SKIP_DIRS = COMMON_SKIP_DIRS

# .tsx uses a distinct grammar from .ts (JSX syntax support) even though
# both are otherwise TypeScript -- tree-sitter-typescript ships them as two
# separate compiled languages, not one with a mode flag.
_LANGUAGE_BY_EXT = {
    ".ts": Language(tsts.language_typescript()),
    ".tsx": Language(tsts.language_tsx()),
}

_DEF_NODE_TYPES = {
    "function_declaration": "function",
    "function_expression": "function",
    "generator_function_declaration": "function",
    "method_definition": "function",
    "class_declaration": "class",
}


def _iter_ts_files(repo_path: Path):
    for path in iter_files(repo_path, _SKIP_DIRS):
        if path.suffix.lower() in _LANGUAGE_BY_EXT:
            yield path


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _flatten_callee(node: Node, source: bytes) -> list[str]:
    """Turn a call's `function` field into an attribute chain list, e.g.
    `this.validate` -> ["this", "validate"]. Falls back to the raw source
    text as a single-element chain for shapes that aren't a plain
    identifier/member walk -- rare, and still a faithful (if unstructured)
    record of what's there."""
    if node.type in ("identifier", "this", "property_identifier"):
        return [_text(node, source)]
    if node.type == "member_expression":
        obj = node.child_by_field_name("object")
        prop = node.child_by_field_name("property")
        chain = _flatten_callee(obj, source) if obj is not None else []
        if prop is not None:
            chain = chain + [_text(prop, source)]
        return chain
    return [_text(node, source)]


def _process_file(ts_file: Path, source: bytes, tree: Tree) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    file_str = str(ts_file)
    # alias -> {"module": import source string, "name": original
    # exported name, or None when it can't be resolved to a single
    # exported name (namespace import, default import)}.
    import_table: dict[str, dict[str, str | None]] = {}

    def scope_identity(scope_stack: list[str]) -> str:
        return f"{file_str}:{'.'.join(scope_stack)}" if scope_stack else file_str

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

    def handle_import(node: Node, scope_stack: list[str]) -> None:
        raw = _text(node, source)
        line = _line(node)
        src_identity = scope_identity(scope_stack)

        source_node = node.child_by_field_name("source")
        module = _text(source_node, source)[1:-1] if source_node is not None else ""

        clause = next((c for c in node.children if c.type == "import_clause"), None)
        if clause is None:
            # Side-effect-only import, e.g. `import "./polyfill";` -- no
            # local bindings, so nothing to add to import_table.
            emit_import(src_identity, module, [], raw, line)
            return

        names: list[str] = []
        for child in clause.children:
            if child.type == "identifier":
                # Default import: `import Foo from "x"`. There's no
                # single exported name to look up cross-file (tier2
                # doesn't track `export default` under a fixed
                # identity), so this stays unresolvable -- name=None.
                local_name = _text(child, source)
                names.append("default")
                import_table[local_name] = {"module": module, "name": None}
            elif child.type == "namespace_import":
                # `import * as boto3 from "x"` -- last child is the bound identifier.
                ident = child.children[-1]
                local_name = _text(ident, source)
                names.append("*")
                import_table[local_name] = {"module": module, "name": None}
            elif child.type == "named_imports":
                for spec in child.children:
                    if spec.type != "import_specifier":
                        continue
                    name_node = spec.child_by_field_name("name")
                    alias_node = spec.child_by_field_name("alias")
                    name = _text(name_node, source) if name_node is not None else ""
                    alias_name = _text(alias_node, source) if alias_node is not None else name
                    names.append(name)
                    import_table[alias_name] = {"module": module, "name": name}

        emit_import(src_identity, module, names, raw, line)

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
        # Only a bare call of a named-import binding is unambiguous
        # enough to resolve cross-file -- namespace/default imports
        # (import_entry["name"] is None) followed by attribute access
        # could be a property on the returned object, not a module
        # path, so they're left unresolved.
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

    def visit_def(node: Node, scope_stack: list[str], kind: str) -> None:
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
        kind = _DEF_NODE_TYPES.get(node.type)
        if kind is not None:
            visit_def(node, scope_stack, kind)
            return
        if node.type == "import_statement":
            handle_import(node, scope_stack)
            return
        if node.type == "call_expression":
            handle_call(node, scope_stack)
            walk(node, scope_stack)
            return
        walk(node, scope_stack)

    def walk(node: Node, scope_stack: list[str]) -> None:
        for child in node.children:
            visit(child, scope_stack)

    walk(tree.root_node, [])

    return nodes, edges


def parse_typescript_ast(
    repo_path: str | Path, cache: ExtractionCache | None = None
) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)

    all_nodes: list[EvidenceRecord] = []
    all_edges: list[EdgeRecord] = []

    for ts_file in _iter_ts_files(repo_path):
        language = _LANGUAGE_BY_EXT[ts_file.suffix.lower()]
        parser = Parser(language)

        try:
            source = ts_file.read_bytes()
            tree = parser.parse(source)
        except Exception:
            # Malformed/unreadable file: degrade gracefully, don't crash the scan.
            continue

        def compute(ts_file=ts_file, source=source, tree=tree):
            return _process_file(ts_file, source, tree)

        if cache is not None:
            nodes, edges = cache.get_or_compute(ts_file, _EXTRACTOR_NAME, compute)
        else:
            nodes, edges = compute()

        all_nodes.extend(nodes)
        all_edges.extend(edges)

    return all_nodes, all_edges
