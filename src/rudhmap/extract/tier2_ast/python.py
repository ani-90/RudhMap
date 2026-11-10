"""Tier 2 extractor: tree-sitter AST for Python.

Single-file parsing only. An import's module string and a call's callee
chain are emitted exactly as the AST states them -- resolving either
against another file's definitions is Stage 2 (graph assembly)'s job, not
this tier's. See docs/tier2_ast_schema.md for the emission contract this
module implements.

Besides definitions, imports and calls, this pass records what a later
resolver needs to connect calls the raw text can't (all still single-file
facts, nothing guessed):
  - a `module` node per non-empty file, so top-level code (`settings =
    Settings()`) has a caller;
  - the type of a local name when the file states it: `x = Foo()`, a
    parameter annotated `x: Foo`, `self.x = Foo()` (stored on the class);
  - references: a definition passed as a value (`add_task(_run_bg)`,
    `Depends(get_db)`, `db.query(User)`), emitted as `relation:
    references` edges;
  - base classes, as `relation: inherits` edges.
"""
from __future__ import annotations

import re
from pathlib import Path

from tree_sitter import Language, Node, Parser, Tree
import tree_sitter_python as tspython

from rudhmap.cache import ExtractionCache
from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 2
CONFIDENCE = 1.0
# Bump the version whenever this extractor's output changes, so cached
# results from the old version are never served (see rudhmap.cache).
_EXTRACTOR_NAME = "python@5"

_SKIP_DIRS = COMMON_SKIP_DIRS

_LANGUAGE = Language(tspython.language())

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SELF_NAMES = ("self", "cls")
# Wrappers that don't change what an annotated value is an instance of.
_TYPING_WRAPPERS = {"Optional", "Union", "Annotated", "Final", "ClassVar"}
_PARAM_TYPES = ("identifier", "typed_parameter", "default_parameter", "typed_default_parameter",
                "list_splat_pattern", "dictionary_splat_pattern")


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


def _is_plain_chain(chain: list[str]) -> bool:
    return bool(chain) and all(_IDENT_RE.match(part) for part in chain)


def _annotation_chain(node: Node, source: bytes) -> list[str] | None:
    """The single class an annotation says a value is an instance of, or
    None. `Foo`, `mod.Foo`, `Optional[Foo]`, `Foo | None` -> Foo;
    `List[Foo]`, `Foo | Bar`, string forward references -> None."""
    chains: list[list[str]] = []
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == "attribute":
            chains.append(_flatten_callee(n, source))
            continue
        if n.type == "identifier":
            chains.append([_text(n, source)])
            continue
        if n.type == "string":
            return None
        stack.extend(n.children)
    # Exactly one remaining name: `List[Foo]` names two (List, Foo) and is
    # rejected, so a container never passes as an instance of its contents.
    chains = [c for c in chains if c[-1] not in _TYPING_WRAPPERS]
    if len(chains) == 1 and _is_plain_chain(chains[0]):
        return chains[0]
    return None


def _bound_names(node: Node, source: bytes) -> list[str]:
    """Every plain name an assignment/for/with target binds."""
    if node.type == "identifier":
        return [_text(node, source)]
    if node.type in ("pattern_list", "tuple_pattern", "list_pattern", "expression_list", "tuple", "list",
                     "list_splat_pattern", "parenthesized_expression"):
        names: list[str] = []
        for child in node.children:
            names.extend(_bound_names(child, source))
        return names
    return []


def _process_file(py_file: Path, source: bytes, tree: Tree) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    nodes: list[EvidenceRecord] = []
    edges: list[EdgeRecord] = []

    file_str = str(py_file)
    # alias -> {"module": dotted module path, "name": original imported
    # name, or None for a whole-module import like `import x as y`,
    # "bound": the full dotted path the local name stands for}.
    # Kept separate (not concatenated) so a call resolving through this
    # table can tell "which file" apart from "which name in that file".
    # "bound" differs from "module" for `import a.b.c` (binds `a`, so
    # bound == "a") and for `from a.b import c` (bound == "a.b.c").
    import_table: dict[str, dict[str, str | None]] = {}
    # scope key ("" = module, "f" / "A.m" = inside that function) -> name -> type ref.
    var_types: dict[str, dict[str, dict]] = {}
    # scope key -> names bound there (params, assignment/for/with targets).
    local_names: dict[str, set[str]] = {}
    # class qualname -> its EvidenceRecord, so `self.x = Foo()` can record x's type.
    class_records: dict[str, EvidenceRecord] = {}
    in_param_default = [False]

    if source.strip():
        nodes.append(
            EvidenceRecord(
                kind="module",
                identity=file_str,
                file=file_str,
                line=1,
                tier=TIER,
                confidence=CONFIDENCE,
                attrs={"name": py_file.stem, "qualname": ""},
            )
        )

    def scope_identity(scope_stack: list[str]) -> str:
        return f"{file_str}:{'.'.join(scope_stack)}" if scope_stack else file_str

    def type_ref(chain: list[str] | None) -> dict | None:
        """Where a type name points: through an import binding (`bound`
        dotted path, resolved against scanned files later) or a name
        defined in this file (`local`)."""
        if not chain or not _is_plain_chain(chain):
            return None
        entry = import_table.get(chain[0])
        if entry is not None:
            return {"bound": ".".join([entry["bound"], *chain[1:]])}
        return {"local": ".".join(chain)}

    def function_scopes(scope_stack: list[str]):
        """Scope keys visible from here, innermost first. Class bodies are
        skipped: a method can't see its class's names unqualified."""
        for i in range(len(scope_stack), -1, -1):
            key = ".".join(scope_stack[:i])
            if i > 0 and key in class_records:
                continue
            yield key

    def lookup_var_type(name: str, scope_stack: list[str]) -> dict | None:
        for key in function_scopes(scope_stack):
            ref = var_types.get(key, {}).get(name)
            if ref is not None:
                return ref
            if name in local_names.get(key, ()):
                return None  # bound here, type unknown -- shadows anything outer
        return None

    def locally_bound(name: str, scope_stack: list[str]) -> bool:
        return any(name in local_names.get(key, ()) for key in function_scopes(scope_stack) if key)

    def enclosing_class(scope_stack: list[str]) -> str | None:
        for i in range(len(scope_stack), 0, -1):
            key = ".".join(scope_stack[:i])
            if key in class_records:
                return key
        return None

    def bind(scope_stack: list[str], name: str, ref: dict | None) -> None:
        key = ".".join(scope_stack)
        local_names.setdefault(key, set()).add(name)
        if ref is not None:
            var_types.setdefault(key, {})[name] = ref
        else:
            var_types.get(key, {}).pop(name, None)

    def handle_import(node: Node, scope_stack: list[str]) -> None:
        raw = _text(node, source)
        line = _line(node)
        src_identity = scope_identity(scope_stack)

        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    module = _text(child, source)
                    root = module.split(".")[0]
                    import_table[root] = {"module": module, "name": None, "bound": root}
                    emit_import(src_identity, module, [], raw, line)
                elif child.type == "aliased_import":
                    dotted = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    module = _text(dotted, source) if dotted is not None else ""
                    alias_name = _text(alias, source) if alias is not None else module
                    import_table[alias_name] = {"module": module, "name": None, "bound": module}
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
                    import_table[name] = {"module": module, "name": name, "bound": f"{module}.{name}"}
                elif child.type == "aliased_import":
                    dotted = child.child_by_field_name("name")
                    alias = child.child_by_field_name("alias")
                    name = _text(dotted, source) if dotted is not None else ""
                    alias_name = _text(alias, source) if alias is not None else name
                    names.append(name)
                    import_table[alias_name] = {"module": module, "name": name, "bound": f"{module}.{name}"}
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

    def name_attrs(chain: list[str]) -> dict:
        """Import-resolution hints shared by calls and references."""
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
        # An attribute call through an imported name (`crud.create_user()`
        # after `from app.db import crud`) can't be classified here -- the
        # name may be a module or an object -- so record the full dotted path
        # and let the resolver decide from what was actually scanned.
        if likely_alias and len(chain) >= 2:
            attrs["resolved_dotted_path"] = ".".join([import_entry["bound"], *chain[1:]])
        if in_param_default[0]:
            attrs["via"] = "param_default"
        return attrs

    def handle_call(node: Node, scope_stack: list[str]) -> None:
        func = node.child_by_field_name("function")
        if func is None:
            return
        chain = _flatten_callee(func, source)
        if not chain:
            return
        attrs = name_attrs(chain)
        # A call on a local name whose type this file states (`x = Foo()`,
        # `x: Foo`): the resolver looks the method up on that class.
        if len(chain) >= 2 and chain[0] not in _SELF_NAMES and not attrs["likely_import_alias"]:
            ref = lookup_var_type(chain[0], scope_stack)
            if ref is not None:
                attrs["receiver_type"] = ref
                attrs["receiver_rest"] = chain[1:]
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
        handle_references(node.child_by_field_name("arguments"), scope_stack)

    def handle_references(arguments: Node | None, scope_stack: list[str]) -> None:
        """A bare name passed as an argument may be a definition handed over
        as a value (callback, background task, model class). Names bound
        locally are variables, so they're skipped; whatever's left is
        emitted and kept only if the resolver finds a definition for it."""
        if arguments is None:
            return
        for arg in arguments.children:
            value = arg.child_by_field_name("value") if arg.type == "keyword_argument" else arg
            if value is None or value.type != "identifier":
                continue
            name = _text(value, source)
            if locally_bound(name, scope_stack):
                continue
            attrs = name_attrs([name])
            attrs["relation"] = "references"
            edges.append(
                EdgeRecord(
                    src=scope_identity(scope_stack),
                    dst=name,
                    file=file_str,
                    line=_line(value),
                    tier=TIER,
                    confidence=CONFIDENCE,
                    attrs=attrs,
                )
            )

    def handle_assignment(node: Node, scope_stack: list[str]) -> None:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        annotation = node.child_by_field_name("type")
        if left is None:
            return
        chain = _annotation_chain(annotation, source) if annotation is not None else None
        if chain is None and right is not None and right.type == "call":
            func = right.child_by_field_name("function")
            if func is not None and func.type in ("identifier", "attribute"):
                chain = _flatten_callee(func, source)
        ref = type_ref(chain)
        if left.type == "attribute":
            obj = left.child_by_field_name("object")
            attr = left.child_by_field_name("attribute")
            cls = enclosing_class(scope_stack)
            if (obj is not None and attr is not None and obj.type == "identifier"
                    and _text(obj, source) == "self" and cls is not None and ref is not None):
                class_records[cls].attrs.setdefault("attr_types", {})[_text(attr, source)] = ref
            return
        names = _bound_names(left, source)
        for name in names:
            bind(scope_stack, name, ref if len(names) == 1 else None)

    def handle_parameters(params: Node | None, scope_stack: list[str]) -> None:
        """Bind parameter names (and annotated types) in the function's own
        scope, then walk default values: `Depends(get_db)` is a reference
        the function depends on, so it's attributed to the function."""
        if params is None:
            return
        defaults: list[Node] = []
        for p in params.children:
            if p.type not in _PARAM_TYPES:
                continue
            if p.type == "identifier":
                bind(scope_stack, _text(p, source), None)
                continue
            name_node = p.child_by_field_name("name")
            if name_node is None:
                name_node = next((c for c in p.children if c.type == "identifier"), None)
            if name_node is None:
                continue
            annotation = p.child_by_field_name("type")
            chain = _annotation_chain(annotation, source) if annotation is not None else None
            bind(scope_stack, _text(name_node, source), type_ref(chain))
            value = p.child_by_field_name("value")
            if value is not None:
                defaults.append(value)
        in_param_default[0] = True
        try:
            for value in defaults:
                visit(value, scope_stack)
        finally:
            in_param_default[0] = False

    def visit_def_or_class(node: Node, scope_stack: list[str], kind: str) -> None:
        name_node = node.child_by_field_name("name")
        name = _text(name_node, source) if name_node is not None else "<anonymous>"
        qualname = ".".join(scope_stack + [name])
        identity = f"{file_str}:{qualname}"
        record = EvidenceRecord(
            kind=kind,
            identity=identity,
            file=file_str,
            line=_line(node),
            tier=TIER,
            confidence=CONFIDENCE,
            attrs={"name": name, "qualname": qualname, "end_line": node.end_point[0] + 1},
        )
        nodes.append(record)
        if kind == "class":
            class_records[qualname] = record
            bases = []
            superclasses = node.child_by_field_name("superclasses")
            for base in superclasses.children if superclasses is not None else []:
                if base.type not in ("identifier", "attribute"):
                    continue
                chain = _flatten_callee(base, source)
                ref = type_ref(chain)
                if ref is None:
                    continue
                bases.append(ref)
                edges.append(
                    EdgeRecord(
                        src=identity,
                        dst=".".join(chain),
                        file=file_str,
                        line=_line(node),
                        tier=TIER,
                        confidence=CONFIDENCE,
                        attrs={"relation": "inherits", "type_ref": ref, "callee_chain": chain},
                    )
                )
            if bases:
                record.attrs["bases"] = bases
        else:
            handle_parameters(node.child_by_field_name("parameters"), scope_stack + [name])
        body = node.child_by_field_name("body")
        if body is not None:
            walk(body, scope_stack + [name])

    def visit(node: Node, scope_stack: list[str]) -> None:
        if node.type == "decorated_definition":
            # Decorator arguments describe the definition they decorate
            # (`@router.post("/x", response_model=Resp)` is part of what the
            # route is), so calls and references in them are attributed to
            # that definition, not to the enclosing scope.
            inner = node.child_by_field_name("definition")
            name_node = inner.child_by_field_name("name") if inner is not None else None
            deco_scope = scope_stack + [_text(name_node, source)] if name_node is not None else scope_stack
            for deco in node.children:
                if deco.type == "decorator":
                    walk(deco, deco_scope)
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
        if node.type == "assignment":
            # Walk the right-hand side first: in `x = f(x)` the call sees the
            # old binding of x, not the new one.
            walk(node, scope_stack)
            handle_assignment(node, scope_stack)
            return
        if node.type in ("for_statement", "for_in_clause"):
            left = node.child_by_field_name("left")
            if left is not None:
                for name in _bound_names(left, source):
                    bind(scope_stack, name, None)
        elif node.type == "as_pattern":
            alias = node.child_by_field_name("alias")
            if alias is not None:
                for name in _bound_names(alias.children[0] if alias.children else alias, source):
                    bind(scope_stack, name, None)
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
