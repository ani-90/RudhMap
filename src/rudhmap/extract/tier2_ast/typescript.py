"""Tier 2 extractor: tree-sitter AST for TypeScript/TSX.

Single-file parsing only. An import's module string and a call's callee
chain are emitted exactly as the AST states them -- resolving either
against another file's definitions is Stage 2 (graph assembly)'s job, not
this tier's. See docs/tier2_ast_schema.md for the emission contract this
module implements (same contract as the Python visitor).
"""
from __future__ import annotations

import functools
import json
import os
import re
from pathlib import Path

from tree_sitter import Language, Node, Parser, Tree
import tree_sitter_typescript as tsts

from rudhmap.cache import ExtractionCache
from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 2
CONFIDENCE = 1.0
# Bump the version whenever this extractor's output changes, so cached
# results from the old version are never served (see rudhmap.cache).
_EXTRACTOR_NAME = "typescript@5"

_SKIP_DIRS = COMMON_SKIP_DIRS

# resolved_name placeholder for a default import; the resolver swaps in the
# target file's default_export name.
DEFAULT_EXPORT = "<default>"

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


def _strip_jsonc(text: str) -> str:
    """tsconfig.json allows comments and trailing commas; drop both without
    touching string contents (a path pattern like "@/*" contains `/*`)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


@functools.lru_cache(maxsize=256)
def _tsconfig_aliases(directory: str) -> tuple[tuple[str, str], ...]:
    """(prefix, target dir) pairs from the nearest tsconfig.json's
    compilerOptions.paths, e.g. ("@/", "<abs>/src/"). Only `prefix/*` ->
    `dir/*` patterns are supported; that covers the common `@/*` alias."""
    current = Path(directory)
    for _ in range(8):
        config = current / "tsconfig.json"
        if config.is_file():
            seen = 0
            while config is not None and seen < 3:
                seen += 1
                try:
                    data = json.loads(_strip_jsonc(config.read_text(encoding="utf-8", errors="replace")))
                except (OSError, ValueError):
                    return ()
                options = data.get("compilerOptions") or {}
                paths = options.get("paths")
                if paths:
                    base = config.parent / (options.get("baseUrl") or ".")
                    rules = []
                    for pattern, targets in paths.items():
                        if not (pattern.endswith("*") and targets and str(targets[0]).endswith("*")):
                            continue
                        rules.append((pattern[:-1], str((base / str(targets[0])[:-1]).resolve()) + os.sep))
                    return tuple(sorted(rules, key=lambda r: -len(r[0])))
                extends = data.get("extends")
                config = (config.parent / extends) if isinstance(extends, str) and extends.startswith(".") else None
            return ()
        if current.parent == current:
            break
        current = current.parent
    return ()


def _relative_module(ts_file: Path, module: str) -> str:
    """Rewrite a tsconfig path alias (`@/components/X`) to a relative
    specifier (`../components/X`) so the resolver treats it like any other
    relative import. Bare package names are returned unchanged."""
    if module.startswith("."):
        return module
    for prefix, target in _tsconfig_aliases(str(ts_file.parent)):
        if module.startswith(prefix):
            rel = os.path.relpath(target + module[len(prefix):], ts_file.parent).replace("\\", "/")
            return rel if rel.startswith(".") else "./" + rel
    return module


def _jsdoc(node: Node, source: bytes) -> str | None:
    """First line of a /** ... */ comment right before a declaration (or
    before the export/const statement wrapping it)."""
    for candidate in (node, node.parent, node.parent.parent if node.parent is not None else None):
        if candidate is None:
            continue
        prev = candidate.prev_named_sibling
        if prev is not None and prev.type == "comment":
            text = _text(prev, source)
            if text.startswith("/**"):
                for line in text[3:-2].splitlines():
                    line = line.strip().lstrip("*").strip()
                    if line and not line.startswith("@"):
                        return line if len(line) <= 160 else line[:157] + "..."
            return None
        if candidate.type in ("program", "statement_block", "class_body"):
            return None
    return None


def _ts_signature(header: str) -> str:
    text = " ".join(header.split()).rstrip("{").rstrip().rstrip("=>").rstrip()
    text = text.replace("( ", "(").replace(", )", ")").replace(",)", ")")
    return text if len(text) <= 240 else text[:237] + "..."


def _process_file(ts_file: Path, source: bytes, tree: Tree) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    file_str = str(ts_file)
    # alias -> {"module": import source string, "name": original
    # exported name, or None when it can't be resolved to a single
    # exported name (namespace import, default import)}.
    import_table: dict[str, dict[str, str | None]] = {}

    # Top-level code needs a caller node, same as the Python visitor. The
    # module node also records what the file exports by default and which
    # other modules it re-exports, so imports through `export default X`
    # and barrel files (`export * from "./sdk.gen"`) can be resolved.
    module_record = None
    if source.strip():
        module_record = EvidenceRecord(
            kind="module",
            identity=file_str,
            file=file_str,
            line=1,
            tier=TIER,
            confidence=CONFIDENCE,
            attrs={"name": ts_file.stem, "qualname": "", "end_line": source.count(b"\n") + 1},
        )
        nodes.append(module_record)

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
        module = _relative_module(ts_file, _text(source_node, source)[1:-1]) if source_node is not None else ""

        clause = next((c for c in node.children if c.type == "import_clause"), None)
        if clause is None:
            # Side-effect-only import, e.g. `import "./polyfill";` -- no
            # local bindings, so nothing to add to import_table.
            emit_import(src_identity, module, [], raw, line)
            return

        names: list[str] = []
        for child in clause.children:
            if child.type == "identifier":
                # Default import: `import Foo from "x"`. Resolved against the
                # target file's `export default <name>` (module attr
                # default_export) by the resolver.
                local_name = _text(child, source)
                names.append("default")
                import_table[local_name] = {"module": module, "name": DEFAULT_EXPORT}
            elif child.type == "namespace_import":
                # `import * as boto3 from "x"` -- last child is the bound identifier.
                ident = child.children[-1]
                local_name = _text(ident, source)
                names.append("*")
                import_table[local_name] = {"module": module, "name": None, "namespace": True}
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

    def handle_export(node: Node) -> None:
        """`export default X` / `export default function X` and
        `export {A, B} from "./x"` / `export * from "./x"`."""
        if module_record is None:
            return
        children = node.children
        if any(c.type == "default" for c in children):
            target = next((c for c in children if c.type in ("identifier", "function_declaration",
                                                            "class_declaration", "generator_function_declaration")), None)
            if target is not None:
                name_node = target if target.type == "identifier" else target.child_by_field_name("name")
                if name_node is not None:
                    module_record.attrs["default_export"] = _text(name_node, source)
        source_node = node.child_by_field_name("source")
        if source_node is not None:
            module = _relative_module(ts_file, _text(source_node, source)[1:-1])
            clause = next((c for c in children if c.type == "export_clause"), None)
            names = None
            if clause is not None:
                names = []
                for spec in clause.children:
                    if spec.type == "export_specifier":
                        name_node = spec.child_by_field_name("name")
                        alias_node = spec.child_by_field_name("alias")
                        name = _text(name_node, source) if name_node is not None else ""
                        names.append([_text(alias_node, source) if alias_node is not None else name, name])
            module_record.attrs.setdefault("reexports", []).append({"module": module, "names": names})

    def emit_use(chain: list[str], node: Node, scope_stack: list[str], via: str | None = None) -> None:
        import_entry = import_table.get(chain[0])
        likely_alias = import_entry is not None
        attrs = {"callee_chain": chain, "likely_import_alias": likely_alias}
        if via:
            attrs["via"] = via
        # A bare call of a named-import binding names its target exactly.
        # So does an attribute call through a binding that is known to be
        # a module (`import * as crud` then `crud.createUser()`) or a named
        # export (`import { User }` then `User.create()`): the qualname is
        # the rest of the chain. The resolver still only connects the edge
        # if that exact node was extracted from the resolved file. A default
        # import resolves through the target file's default export.
        if likely_alias and import_entry["name"] is not None:
            attrs["resolved_module"] = import_entry["module"]
            attrs["resolved_name"] = ".".join([import_entry["name"], *chain[1:]])
        elif likely_alias and len(chain) >= 2 and import_entry.get("namespace"):
            attrs["resolved_module"] = import_entry["module"]
            attrs["resolved_name"] = ".".join(chain[1:])
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

    def handle_call(node: Node, scope_stack: list[str]) -> None:
        func = node.child_by_field_name("function")
        if func is None:
            return
        chain = _flatten_callee(func, source)
        # `handleError.bind(x)` / `fn.call(...)` use `handleError` / `fn`.
        if len(chain) >= 2 and chain[-1] in ("bind", "call", "apply"):
            chain = chain[:-1]
        if chain:
            emit_use(chain, node, scope_stack)

    def handle_jsx(node: Node, scope_stack: list[str]) -> None:
        """`<AddItem />` / `<Foo.Bar>` is a use of that component. Lower-case
        names are HTML elements, not components."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        chain = _flatten_callee(name_node, source) if name_node.type != "nested_identifier" \
            else _text(name_node, source).split(".")
        if not chain or not chain[0][:1].isupper():
            return
        emit_use(chain, node, scope_stack, via="jsx")

    def add_def(name: str, node: Node, scope_stack: list[str], kind: str, header_end: int, doc_node: Node) -> str:
        qualname = ".".join(scope_stack + [name])
        attrs = {
            "name": name,
            "qualname": qualname,
            "end_line": node.end_point[0] + 1,
            "signature": _ts_signature(source[node.start_byte:header_end].decode("utf-8", errors="replace")),
        }
        doc = _jsdoc(doc_node, source)
        if doc:
            attrs["doc"] = doc
        nodes.append(
            EvidenceRecord(
                kind=kind,
                identity=f"{file_str}:{qualname}",
                file=file_str,
                line=_line(node),
                tier=TIER,
                confidence=CONFIDENCE,
                attrs=attrs,
            )
        )
        return qualname

    def visit_def(node: Node, scope_stack: list[str], kind: str) -> None:
        name_node = node.child_by_field_name("name")
        name = _text(name_node, source) if name_node is not None else "<anonymous>"
        body = node.child_by_field_name("body")
        add_def(name, node, scope_stack, kind, body.start_byte if body is not None else node.end_byte, node)
        if body is not None:
            walk(body, scope_stack + [name])

    def visit_declarator(node: Node, scope_stack: list[str]) -> bool:
        """`const AddItem = () => {...}` / `const f = function () {...}`:
        a named function, like a declaration. Returns False for any other
        value so the caller walks it as ordinary code."""
        value = node.child_by_field_name("value")
        name_node = node.child_by_field_name("name")
        if value is None or name_node is None or name_node.type != "identifier":
            return False
        if value.type not in ("arrow_function", "function_expression", "function"):
            return False
        name = _text(name_node, source)
        body = value.child_by_field_name("body")
        header_end = body.start_byte if body is not None else value.end_byte
        add_def(name, node, scope_stack, "function", header_end, node.parent if node.parent is not None else node)
        keyword = node.parent.children[0].type if node.parent is not None and node.parent.children else ""
        if keyword in ("const", "let", "var"):
            nodes[-1].attrs["signature"] = f"{keyword} {nodes[-1].attrs['signature']}"
        # Expression-bodied arrows (`() => <Foo />`) have the expression as body.
        if body is not None:
            visit(body, scope_stack + [name]) if body.type != "statement_block" else walk(body, scope_stack + [name])
        return True

    def visit(node: Node, scope_stack: list[str]) -> None:
        kind = _DEF_NODE_TYPES.get(node.type)
        if kind is not None:
            visit_def(node, scope_stack, kind)
            return
        if node.type == "variable_declarator" and visit_declarator(node, scope_stack):
            return
        if node.type == "import_statement":
            handle_import(node, scope_stack)
            return
        if node.type == "export_statement":
            handle_export(node)
            walk(node, scope_stack)
            return
        if node.type == "call_expression":
            handle_call(node, scope_stack)
            walk(node, scope_stack)
            return
        if node.type in ("jsx_opening_element", "jsx_self_closing_element"):
            handle_jsx(node, scope_stack)
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
