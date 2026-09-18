"""Identity resolution, step A: same-file/same-scope call resolution.

Tier 2's call edges record the callee exactly as written in source (e.g.
`this.validate`, `doLocalWork`) because the AST parser has no notion of
which name resolves to which declaration -- that's not its job. assemble_graph
correctly drops these as dangling, since the raw text doesn't match any
node's qualified identity.

This pass recovers the subset that's resolvable with zero ambiguity, using
only information already present on the edge and in the graph:

  - `self.foo` / `this.foo` (chain starts with self/this, length >= 2):
    the caller's own src identity tells us the enclosing class, so the
    target must be `{file}:{enclosing_class}.{foo}`.
  - bare calls (chain length 1, not flagged likely_import_alias): the
    target must be a module-level declaration in the same file,
    `{file}:{name}`.

Anything else (an import-aliased call like `write_object`, a call through a
non-self/this receiver like `obj.method()`) requires cross-file resolution
or type information this pass doesn't have, and is deliberately left
dropped rather than guessed at -- that's step B.
"""
from __future__ import annotations

import os

from rudhmap.extract.schema import EdgeRecord
from rudhmap.graph.assemble import AssemblyResult


def _candidate_identity(edge: EdgeRecord) -> str | None:
    if edge.tier != 2:
        return None
    chain = edge.attrs.get("callee_chain")
    if not chain:
        return None

    file = edge.file
    qualname = edge.src[len(file) + 1 :] if edge.src.startswith(file + ":") else ""

    if len(chain) >= 2 and chain[0] in ("self", "this"):
        enclosing_class = qualname.split(".")[0] if qualname else None
        if enclosing_class is None:
            return None
        return f"{file}:{enclosing_class}.{'.'.join(chain[1:])}"

    if len(chain) == 1 and chain[0] not in ("self", "this"):
        if edge.attrs.get("likely_import_alias"):
            return None
        return f"{file}:{chain[0]}"

    return None


def resolve_same_scope_calls(assembly: AssemblyResult) -> AssemblyResult:
    graph = assembly.graph
    still_dropped: list[EdgeRecord] = []

    for edge in assembly.dropped_edges:
        candidate = _candidate_identity(edge)
        if (
            candidate is not None
            and graph.has_node(candidate)
            and graph.has_node(edge.src)
        ):
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


def _resolve_dotted_module_suffix(module: str, node_files: set[str]) -> str | None:
    suffix = os.path.normpath(os.path.join(*module.split(".")) + ".py")
    matches = {f for f in node_files if os.path.normpath(f).endswith(suffix)}
    if len(matches) == 1:
        return next(iter(matches))
    return None


def _cross_file_candidate_identity(edge: EdgeRecord, node_files: set[str]) -> str | None:
    if edge.tier != 2:
        return None
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
    node_files = {ev.file for _, data in graph.nodes(data=True) for ev in data["evidence"]}

    still_dropped: list[EdgeRecord] = []
    for edge in assembly.dropped_edges:
        candidate = _cross_file_candidate_identity(edge, node_files)
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
