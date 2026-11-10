"""Identity resolution, step A: same-file/same-scope call resolution.

Tier 2's call edges record the callee exactly as written in source (e.g.
`this.validate`, `doLocalWork`) because the AST parser has no notion of
which name resolves to which declaration -- that's not its job. assemble_graph
correctly drops these as dangling, since the raw text doesn't match any
node's qualified identity.

This pass recovers the subset that's resolvable with zero ambiguity, using
only information already present on the edge and in the graph:

  - `self.foo` / `this.foo` / `cls.foo` (chain starts with self/this/cls,
    length 2): the innermost class enclosing the caller is the target's
    class, so the target is `{file}:{that_class}.{foo}`. (Inherited
    methods are resolved later, in the typed pass.)
  - bare names (chain length 1, not flagged likely_import_alias): looked up
    the way Python/JS scoping does it -- the caller's own scope first, then
    each enclosing function, then the module. Class bodies are skipped: a
    method can't call a sibling method unqualified. So `walk()` inside
    `_process_file.visit` resolves to the nested `_process_file.walk`.

Anything else (an import-aliased call like `write_object`, a call through a
non-self/this receiver like `obj.method()`) requires cross-file resolution
or type information this pass doesn't have, and is deliberately left
dropped rather than guessed at -- that's step B.

The same rules apply to `relation: references` edges (a definition passed
as a value), which carry the same `callee_chain`.
"""
from __future__ import annotations

import os
from typing import Iterator

from rudhmap.extract.schema import EdgeRecord
from rudhmap.graph.assemble import AssemblyResult

_SELF_NAMES = ("self", "this", "cls")


def _kind(graph, node_id: str) -> str:
    return graph.nodes[node_id]["evidence"][0].kind


def _caller_qualname(edge: EdgeRecord) -> str:
    return edge.src[len(edge.file) + 1 :] if edge.src.startswith(edge.file + ":") else ""


def _enclosing_class(graph, file: str, qualname: str) -> str | None:
    parts = qualname.split(".") if qualname else []
    for i in range(len(parts), 0, -1):
        candidate = f"{file}:{'.'.join(parts[:i])}"
        if graph.has_node(candidate) and _kind(graph, candidate) == "class":
            return candidate
    return None


def _scope_candidates(graph, file: str, qualname: str, name: str) -> Iterator[str]:
    """`name` as seen from inside `qualname`, innermost scope first."""
    parts = qualname.split(".") if qualname else []
    for i in range(len(parts), -1, -1):
        prefix = ".".join(parts[:i])
        if i > 0:
            scope_id = f"{file}:{prefix}"
            if graph.has_node(scope_id) and _kind(graph, scope_id) == "class":
                continue
        yield f"{file}:{prefix}.{name}" if prefix else f"{file}:{name}"


def _same_scope_target(graph, edge: EdgeRecord) -> str | None:
    if edge.tier != 2:
        return None
    chain = edge.attrs.get("callee_chain")
    if not chain:
        return None
    qualname = _caller_qualname(edge)

    if len(chain) == 2 and chain[0] in _SELF_NAMES:
        cls = _enclosing_class(graph, edge.file, qualname)
        if cls is None and "." in qualname:
            # No class node in the graph (hand-built graphs): the caller's
            # outermost scope is the best statement of its class.
            cls = f"{edge.file}:{qualname.split('.')[0]}"
        if cls is None:
            return None
        candidate = f"{cls}.{chain[1]}"
        return candidate if graph.has_node(candidate) else None

    if len(chain) == 1 and chain[0] not in _SELF_NAMES:
        if edge.attrs.get("likely_import_alias"):
            return None
        for candidate in _scope_candidates(graph, edge.file, qualname, chain[0]):
            if graph.has_node(candidate):
                return candidate
    return None


def resolve_same_scope_calls(assembly: AssemblyResult) -> AssemblyResult:
    graph = assembly.graph
    still_dropped: list[EdgeRecord] = []

    for edge in assembly.dropped_edges:
        candidate = _same_scope_target(graph, edge) if graph.has_node(edge.src) else None
        if candidate is not None:
            graph.add_edge(edge.src, candidate, evidence=edge)
        else:
            still_dropped.append(edge)

    return AssemblyResult(graph=graph, dropped_edges=still_dropped)


# --- Identity resolution, step B1: cross-file resolution of bare calls
# through an import binding, e.g. `write_object(batch)` where
# `write_object` came from `from ingest.writer import put_object as
# write_object`. Tier 2 (see the extractor changes in python.py/
# typescript.py) now records `resolved_module`/`resolved_name` on such
# calls -- the module string as written in source, and the original
# (pre-alias) exported name. This pass turns that into a real file, then a
# real node, using only filesystem-relative math or exact suffix matching
# against files that were actually scanned -- never a guess.
#
# Two cases, by the importing file's language:
#   - TS/JS relative import (`./ingest/writer`): fully precise. Join the
#     importing file's directory with the relative path, try real
#     extensions and index files, and take the first that matches an
#     actually-scanned file.
#   - Python absolute dotted import (`ingest.writer`, no leading dot): we
#     don't have the package root threaded through, so instead suffix-match
#     the dotted path (as a file path) against scanned files. If more than
#     one scanned file has that suffix, it's ambiguous -- left unresolved,
#     never picked arbitrarily.
#
#   - Python attribute call through an imported name (`crud.create_user()`
#     after `from app.db import crud`, or `pkg.mod.f()` after `import
#     pkg.mod`): every split of the full dotted path into (module file,
#     qualname) is tried; it resolves only if exactly one split names both
#     a scanned file and an extracted node. Covers module attributes and
#     class attributes (`User.create()` after `from app.models import
#     User`) alike, and never resolves into an unscanned package.
#
# Left unresolved, deliberately: a bare TS/JS module specifier (e.g.
# "react") -- that's an external package, not something scanned; and a
# Python relative import with a leading dot (`from .writer import x`) --
# tree-sitter's exact shape for that case hasn't been checked against, so
# it's not handled rather than handled speculatively.

_TS_EXTS = (".ts", ".tsx", ".js", ".jsx")
_PY_EXT = ".py"


def _resolve_relative_module_file(
    importing_file: str, module: str, node_files: set[str]
) -> str | None:
    base = os.path.join(os.path.dirname(importing_file), module)
    candidates = [base + ext for ext in _TS_EXTS]
    candidates += [os.path.join(base, "index" + ext) for ext in _TS_EXTS]

    normalized_node_files = {os.path.normpath(f): f for f in node_files}
    for candidate in candidates:
        original = normalized_node_files.get(os.path.normpath(candidate))
        if original is not None:
            return original
    return None


class _FileIndex(frozenset):
    """The scanned file set, plus an index by file name so a dotted-module
    lookup checks only files with the right name instead of every file
    (it runs once per unresolved call; scanning all files each time was the
    resolver's biggest cost)."""

    def __new__(cls, files):
        self = super().__new__(cls, files)
        self.by_name = {}
        for f in self:
            normalized = os.sep + os.path.normpath(f)
            self.by_name.setdefault(os.path.basename(normalized), []).append((normalized, f))
        self.memo = {}
        return self


def _suffix_matches(module: str, node_files: set[str]) -> set[str]:
    index = node_files if isinstance(node_files, _FileIndex) else _FileIndex(node_files)
    if module in index.memo:
        return index.memo[module]
    parts = module.split(".")
    as_path = os.path.join(*parts)
    module_file = os.sep + os.path.normpath(as_path + ".py")
    package_init = os.sep + os.path.normpath(os.path.join(as_path, "__init__.py"))
    matches = {f for normalized, f in index.by_name.get(parts[-1] + ".py", []) if normalized.endswith(module_file)}
    matches |= {f for normalized, f in index.by_name.get("__init__.py", []) if normalized.endswith(package_init)}
    index.memo[module] = matches
    return matches


def _resolve_dotted_module_suffix(module: str, node_files: set[str]) -> str | None:
    matches = _suffix_matches(module, node_files)
    if len(matches) == 1:
        return next(iter(matches))
    return None


def _resolve_dotted_attribute_path(dotted: str, node_files: set[str], node_ids: set[str]) -> str | None:
    """`app.db.crud.create_user` -> `<.../app/db/crud.py>:create_user`.

    Tries every split of the path into (module, qualname). A split counts
    only if the module names exactly one scanned file *and* that file has
    a node with that qualname. Resolves only when exactly one split counts;
    zero (external package, attribute on an object) or several (genuinely
    ambiguous) leave the edge dropped."""
    parts = dotted.split(".")
    found = set()
    for k in range(1, len(parts)):
        target_file = _resolve_dotted_module_suffix(".".join(parts[:k]), node_files)
        if target_file is None:
            continue
        candidate = f"{target_file}:{'.'.join(parts[k:])}"
        if candidate in node_ids:
            found.add(candidate)
    return next(iter(found)) if len(found) == 1 else None


def _cross_file_candidate_identity(edge: EdgeRecord, node_files: set[str], node_ids: set[str]) -> str | None:
    if edge.tier != 2:
        return None
    dotted = edge.attrs.get("resolved_dotted_path")
    if dotted is not None and edge.file.endswith(_PY_EXT) and not dotted.startswith("."):
        return _resolve_dotted_attribute_path(dotted, node_files, node_ids)

    module = edge.attrs.get("resolved_module")
    name = edge.attrs.get("resolved_name")
    if module is None or name is None:
        return None

    if edge.file.endswith(_TS_EXTS):
        if not module.startswith("."):
            return None  # bare specifier -- external package, never scanned
        target_file = _resolve_relative_module_file(edge.file, module, node_files)
    elif edge.file.endswith(_PY_EXT):
        if module.startswith("."):
            return None  # leading-dot relative import -- not handled here
        target_file = _resolve_dotted_module_suffix(module, node_files)
    else:
        return None

    return f"{target_file}:{name}" if target_file is not None else None


def resolve_cross_file_calls(assembly: AssemblyResult) -> AssemblyResult:
    graph = assembly.graph
    node_files = _FileIndex(ev.file for _, data in graph.nodes(data=True) for ev in data["evidence"])
    node_ids = set(graph.nodes)

    still_dropped: list[EdgeRecord] = []
    for edge in assembly.dropped_edges:
        candidate = _cross_file_candidate_identity(edge, node_files, node_ids)
        if (
            candidate is not None
            and graph.has_node(candidate)
            and graph.has_node(edge.src)
        ):
            graph.add_edge(edge.src, candidate, evidence=edge)
        else:
            still_dropped.append(edge)

    return AssemblyResult(graph=graph, dropped_edges=still_dropped)


# --- Identity resolution, step B2.1: compose build-context containment.
#
# A compose service's `build: ./app` (or `build: {context: ./app}`) is a
# direct textual statement from the repo itself: "this service's code lives
# in this directory." That's a different, stronger kind of evidence than
# name-matching across IaC formats (e.g. guessing that `compose:api` and a
# k8s `Service/default/api` are "the same thing" just because both happen
# to be called "api") -- nothing textually states that second link, so it's
# deliberately not attempted here.
#
# This pass links a compose service node to every tier 1/2 code node whose
# file falls under that service's build-context directory, resolved
# relative to the compose file's own directory. Unlike the earlier passes,
# this doesn't recover a dropped edge -- no extractor ever emitted "service
# X owns file Y" as an edge attempt, since tier 0 and tiers 1/2 don't know
# about each other. It synthesizes a new edge, but only from a literal
# directory-containment fact, carrying the compose file's own file:line as
# its evidence citation -- not a fabricated or LLM-guessed claim.


def _is_under(file_path: str, base_dir: str) -> bool:
    file_norm = os.path.normpath(file_path)
    base_norm = os.path.normpath(base_dir)
    try:
        common = os.path.commonpath([file_norm, base_norm])
    except ValueError:
        return False  # e.g. different drives on Windows
    return common == base_norm


def resolve_build_context_containment(assembly: AssemblyResult) -> AssemblyResult:
    graph = assembly.graph

    for service_id, service_data in list(graph.nodes(data=True)):
        for service_ev in service_data["evidence"]:
            build_context = service_ev.attrs.get("build_context")
            if not build_context:
                continue

            base_dir = os.path.normpath(
                os.path.join(os.path.dirname(service_ev.file), build_context)
            )

            for code_id, code_data in list(graph.nodes(data=True)):
                if code_id == service_id:
                    continue
                for code_ev in code_data["evidence"]:
                    if code_ev.tier not in (1, 2):
                        continue
                    if not _is_under(code_ev.file, base_dir):
                        continue
                    graph.add_edge(
                        service_id,
                        code_id,
                        evidence=EdgeRecord(
                            src=service_id,
                            dst=code_id,
                            file=service_ev.file,
                            line=service_ev.line,
                            tier=0,
                            confidence=service_ev.confidence,
                            attrs={"relation": "build_context_contains", "build_context": build_context},
                        ),
                    )
                    break  # one edge per code node is enough, its own evidence has all its own file:line records

    return AssemblyResult(graph=graph, dropped_edges=assembly.dropped_edges)


# --- Identity resolution, step C: calls that need a class, resolved from
# types the source itself states (recorded by the tier 2 extractor).
#
#   - `x.m()` where the file says what x is: `x = Foo()`, a parameter
#     `x: Foo`, `x: Optional[Foo]` (`receiver_type`).
#   - `self.x.m()` where a method of the class did `self.x = Foo()`
#     (`attr_types` on the class node).
#   - `self.m()` where m is inherited from a base class.
#   - `class A(B)` -> an `inherits` edge to B.
#
# A type name resolves like any other name: through the file's import
# binding (`bound` dotted path, matched against scanned files) or to a class
# defined in the same file (`local`). It must land on a class node; a
# function of that name (`x = make_thing()`) proves nothing about x. A
# method is looked up on the class, then on its bases, left to right and
# depth first (close to Python's MRO for ordinary hierarchies). Anything
# that doesn't resolve stays dropped -- no guessing.

_MAX_BASE_DEPTH = 5


def _resolve_type_ref(ref: dict | None, file: str, graph, node_files: set[str], node_ids: set[str]) -> str | None:
    if not ref:
        return None
    if "bound" in ref:
        candidate = _resolve_dotted_attribute_path(ref["bound"], node_files, node_ids)
    elif "local" in ref:
        candidate = f"{file}:{ref['local']}"
    else:
        return None
    if candidate and graph.has_node(candidate) and _kind(graph, candidate) == "class":
        return candidate
    return None


def _class_evidence(graph, class_id: str):
    return [ev for ev in graph.nodes[class_id]["evidence"] if ev.kind == "class"]


def _bases(graph, class_id: str, node_files: set[str], node_ids: set[str]) -> list[str]:
    out = []
    for ev in _class_evidence(graph, class_id):
        for ref in ev.attrs.get("bases") or []:
            base = _resolve_type_ref(ref, ev.file, graph, node_files, node_ids)
            if base is not None and base not in out:
                out.append(base)
    return out


def _find_member(graph, class_id: str, member: list[str], node_files, node_ids, depth: int = 0,
                 seen: set[str] | None = None) -> str | None:
    candidate = f"{class_id}.{'.'.join(member)}"
    if graph.has_node(candidate):
        return candidate
    seen = (seen or set()) | {class_id}
    if depth >= _MAX_BASE_DEPTH:
        return None
    for base in _bases(graph, class_id, node_files, node_ids):
        if base in seen:
            continue
        found = _find_member(graph, base, member, node_files, node_ids, depth + 1, seen)
        if found is not None:
            return found
    return None


def _attr_type(graph, class_id: str, attr: str, node_files, node_ids, depth: int = 0) -> str | None:
    """The class of `self.<attr>`, from `self.<attr> = Foo()` in this class or a base."""
    for ev in _class_evidence(graph, class_id):
        ref = (ev.attrs.get("attr_types") or {}).get(attr)
        if ref is not None:
            return _resolve_type_ref(ref, ev.file, graph, node_files, node_ids)
    if depth >= _MAX_BASE_DEPTH:
        return None
    for base in _bases(graph, class_id, node_files, node_ids):
        found = _attr_type(graph, base, attr, node_files, node_ids, depth + 1)
        if found is not None:
            return found
    return None


def _typed_target(graph, edge: EdgeRecord, node_files: set[str], node_ids: set[str]) -> str | None:
    if edge.tier != 2:
        return None
    attrs = edge.attrs
    if attrs.get("relation") == "inherits":
        return _resolve_type_ref(attrs.get("type_ref"), edge.file, graph, node_files, node_ids)

    chain = attrs.get("callee_chain") or []
    if len(chain) >= 2 and chain[0] in _SELF_NAMES:
        cls = _enclosing_class(graph, edge.file, _caller_qualname(edge))
        if cls is None:
            return None
        if len(chain) == 2:
            return _find_member(graph, cls, [chain[1]], node_files, node_ids)
        owner = _attr_type(graph, cls, chain[1], node_files, node_ids)
        return _find_member(graph, owner, chain[2:], node_files, node_ids) if owner else None

    if attrs.get("receiver_type"):
        owner = _resolve_type_ref(attrs["receiver_type"], edge.file, graph, node_files, node_ids)
        rest = attrs.get("receiver_rest") or []
        return _find_member(graph, owner, rest, node_files, node_ids) if owner and rest else None
    return None


def resolve_typed_calls(assembly: AssemblyResult) -> AssemblyResult:
    graph = assembly.graph
    node_files = _FileIndex(ev.file for _, data in graph.nodes(data=True) for ev in data["evidence"])
    node_ids = set(graph.nodes)

    still_dropped: list[EdgeRecord] = []
    for edge in assembly.dropped_edges:
        target = _typed_target(graph, edge, node_files, node_ids) if graph.has_node(edge.src) else None
        if target is not None:
            graph.add_edge(edge.src, target, evidence=edge)
        else:
            still_dropped.append(edge)
    return AssemblyResult(graph=graph, dropped_edges=still_dropped)
