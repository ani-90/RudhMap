"""The in-memory code index the step B tools read from.

`RepoIndex.get(root)` returns one index per repo, built on first use and
kept in memory for the life of the process (the MCP server). Each call
checks, at most every `_FRESHNESS_SECONDS`, whether any source file was
added, removed or modified (path + size + mtime); if so the graph is
rebuilt. Unchanged files come from the extraction cache, so a rebuild after
editing one file costs mostly the resolver passes, not re-parsing.

Everything an index hands out uses repo-relative, forward-slash paths.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.paths import Relativizer
from rudhmap.pipeline import build_assembly

_SOURCE_SUFFIXES = {".py", ".ts", ".tsx"}
_FRESHNESS_SECONDS = 0.5
_ROUTE_RE = re.compile(r"^@(\w+)\.(get|post|put|patch|delete|head|options|api_route|route|websocket)\(\s*['\"]([^'\"]*)")
# `router = APIRouter(prefix="/api/feed", ...)` / `bp = Blueprint("x", __name__, url_prefix="/x")`
_ROUTER_PREFIX_RE = re.compile(r"^(\w+)\s*=\s*\w*(?:Router|Blueprint)\((.*)$", re.M)
_PREFIX_ARG_RE = re.compile(r"(?:url_)?prefix\s*=\s*['\"]([^'\"]*)['\"]")


@dataclass
class Symbol:
    id: str          # repo-relative node id, e.g. "app/api/feed.py:refresh_feed"; a module's id is its path
    node: str        # the graph's (absolute) node id
    kind: str        # function | class | module | ...
    name: str
    qualname: str
    file: str        # repo-relative path
    line: int
    end_line: int
    signature: str = ""
    doc: str = ""
    decorators: list[str] = field(default_factory=list)
    route_prefixes: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def label(self) -> str:
        return self.qualname or self.file

    @property
    def length(self) -> int:
        return self.end_line - self.line + 1

    @property
    def route(self) -> str | None:
        """`POST /api/feed/refresh` for a decorated route handler."""
        for deco in self.decorators:
            match = _ROUTE_RE.match(deco)
            if match:
                method = match.group(2).upper()
                method = "ANY" if method in ("API_ROUTE", "ROUTE") else method
                path = self.route_prefixes.get(match.group(1), "") + match.group(3)
                return f"{method} {path or '/'}"
        return None


@dataclass
class Link:
    other: str       # graph node id of the other end
    relation: str    # call | reference | inherits | jsx | built_by
    line: int        # call-site line (in the caller's file)
    file: str        # repo-relative file of the call site
    count: int = 1   # number of sites between the same pair with the same relation


def _relation(attrs: dict) -> str:
    relation = attrs.get("relation")
    if relation == "references":
        return "reference"
    if relation == "inherits":
        return "inherits"
    if relation == "built_by":
        return "built_by"
    if attrs.get("via") == "jsx":
        return "jsx"
    return "call"


class RepoIndex:
    _instances: dict[str, "RepoIndex"] = {}
    _lock = threading.Lock()

    def __init__(self, root: Path):
        self.root = root
        self.rel = Relativizer(root)
        self._snapshot: dict[str, tuple[int, int]] = {}
        self._checked_at = 0.0
        self._build_lock = threading.Lock()
        self.build_seconds = 0.0
        self.builds = 0
        self._build()

    @classmethod
    def get(cls, root: str | Path) -> "RepoIndex":
        root = Path(root).expanduser().resolve()
        key = str(root)
        with cls._lock:
            index = cls._instances.get(key)
            if index is None:
                index = cls._instances[key] = RepoIndex(root)
                return index
        index.refresh()
        return index

    # ------------------------------------------------------------ freshness

    def _take_snapshot(self) -> dict[str, tuple[int, int]]:
        snapshot = {}
        for path in iter_files(self.root, COMMON_SKIP_DIRS):
            if path.suffix.lower() not in _SOURCE_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            snapshot[str(path)] = (stat.st_size, stat.st_mtime_ns)
        return snapshot

    def refresh(self) -> bool:
        """Rebuild if any source file changed since the last build. Returns
        True when a rebuild happened."""
        now = time.monotonic()
        if now - self._checked_at < _FRESHNESS_SECONDS:
            return False
        with self._build_lock:
            self._checked_at = time.monotonic()
            snapshot = self._take_snapshot()
            if snapshot == self._snapshot:
                return False
            self._build(snapshot)
            return True

    # ------------------------------------------------------------ build

    def _build(self, snapshot: dict[str, tuple[int, int]] | None = None) -> None:
        started = time.perf_counter()
        self._snapshot = snapshot if snapshot is not None else self._take_snapshot()
        self._checked_at = time.monotonic()
        assembly = build_assembly(str(self.root), verbose=False).result
        graph = assembly.graph
        rel = self.rel

        symbols: dict[str, Symbol] = {}
        for node_id, data in graph.nodes(data=True):
            evidence = data["evidence"][0]
            if evidence.tier != 2:
                continue
            attrs = evidence.attrs
            symbols[node_id] = Symbol(
                id=rel(node_id),
                node=node_id,
                kind=evidence.kind,
                name=attrs.get("name", ""),
                qualname=attrs.get("qualname", ""),
                file=rel(evidence.file),
                line=evidence.line or 1,
                end_line=attrs.get("end_line") or evidence.line or 1,
                signature=attrs.get("signature", ""),
                doc=attrs.get("doc", ""),
                decorators=list(attrs.get("decorators", [])),
            )

        out: dict[str, dict[tuple[str, str], Link]] = {}
        into: dict[str, dict[tuple[str, str], Link]] = {}
        for src, dst, data in graph.edges(data=True):
            evidence = data["evidence"]
            if evidence.attrs.get("kind") == "import" or src not in symbols or dst not in symbols or src == dst:
                continue
            relation = _relation(evidence.attrs)
            line = evidence.line or 0
            for table, a, b in ((out, src, dst), (into, dst, src)):
                links = table.setdefault(a, {})
                existing = links.get((b, relation))
                if existing is None:
                    links[(b, relation)] = Link(b, relation, line, rel(evidence.file))
                else:
                    existing.count += 1
                    if line and (not existing.line or line < existing.line):
                        existing.line = line

        unresolved: dict[str, list[list[str]]] = {}
        for edge in assembly.dropped_edges:
            chain = edge.attrs.get("callee_chain")
            if edge.tier == 2 and chain and edge.src in symbols:
                unresolved.setdefault(edge.src, []).append(list(chain))

        prefixes_by_file: dict[str, dict[str, str]] = {}
        for symbol in symbols.values():
            if symbol.decorators and symbol.file not in prefixes_by_file:
                prefixes = {}
                try:
                    text = (self.root / symbol.file).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
                for match in _ROUTER_PREFIX_RE.finditer(text):
                    arg = _PREFIX_ARG_RE.search(match.group(2))
                    if arg:
                        prefixes[match.group(1)] = arg.group(1)
                prefixes_by_file[symbol.file] = prefixes
            if symbol.decorators:
                symbol.route_prefixes = prefixes_by_file[symbol.file]

        by_file: dict[str, list[Symbol]] = {}
        for symbol in symbols.values():
            if symbol.kind != "module":
                by_file.setdefault(symbol.file, []).append(symbol)
        for members in by_file.values():
            members.sort(key=lambda s: (s.line, s.qualname))

        self.symbols = symbols
        self.by_id = {s.id: s for s in symbols.values()}
        self.out = {k: sorted(v.values(), key=lambda l: (l.line, l.other)) for k, v in out.items()}
        self.into = {k: sorted(v.values(), key=lambda l: (l.file, l.line, l.other)) for k, v in into.items()}
        self.unresolved = unresolved
        self.by_file = by_file
        self.files = sorted({s.file for s in symbols.values()})
        self.names = {s.name for s in symbols.values() if s.name}
        self._lines_cache: dict[str, list[str]] = {}
        self.build_seconds = time.perf_counter() - started
        self.builds += 1

    # ------------------------------------------------------------ source

    def lines(self, rel_file: str) -> list[str]:
        cached = self._lines_cache.get(rel_file)
        if cached is None:
            try:
                text = (self.root / rel_file).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            cached = self._lines_cache[rel_file] = text.splitlines()
        return cached

    def degree(self, symbol: Symbol) -> int:
        return len(self.out.get(symbol.node, ())) + len(self.into.get(symbol.node, ()))

    def module_of(self, symbol: Symbol) -> Symbol | None:
        return self.by_id.get(symbol.file)

    def parent_of(self, symbol: Symbol) -> Symbol | None:
        if "." not in symbol.qualname:
            return None
        return self.by_id.get(f"{symbol.file}:{symbol.qualname.rsplit('.', 1)[0]}")

    def children_of(self, symbol: Symbol) -> list[Symbol]:
        prefix = symbol.qualname + "."
        return [s for s in self.by_file.get(symbol.file, []) if s.qualname.startswith(prefix)
                and "." not in s.qualname[len(prefix):]]


__all__ = ["RepoIndex", "Symbol", "Link"]
