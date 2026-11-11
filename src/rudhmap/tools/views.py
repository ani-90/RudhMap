"""The four step B tools, as plain functions returning compact text:
`find_symbol`, `show`, `trace`, `repo_map`. The MCP server and the CLI both
call these, so their output is identical.

Design rules (eval/reports/stepA-baseline.md, step B constraints):
- answer in one call what a model would otherwise need 2-3 Grep/Read rounds
  for: `show` includes what a function calls, one line each, and inlines tiny
  callee bodies, so the model doesn't stop one file short;
- stay compact: every output has a token budget (chars/4), and anything cut
  says so and how to get it;
- cite `file:line` everywhere, so the model can answer with citations
  without opening files.
"""
from __future__ import annotations

import re
from collections import deque

from rudhmap.tools.index import Link, RepoIndex, Symbol

SHOW_BUDGET = 2000
MAP_BUDGET = 1500
FIND_BUDGET = 400
TRACE_BUDGET = 800
TINY_BODY_LINES = 3
MAX_CALLERS = 12
MAX_CALLEES = 30

_KIND_ORDER = {"function": 0, "class": 1, "module": 2}
# Method names so common on builtins (dict.get, list.append, Path.resolve)
# that an unresolved `x.get()` says nothing about this repo's own `get`.
_COMMON_METHODS = frozenset("""get set items keys values append extend insert pop remove update clear copy
add discard join split strip lstrip rstrip replace format startswith endswith lower upper encode decode
read write close open flush seek resolve exists is_file is_dir mkdir glob rglob iterdir sort sorted index
count find search match group sub send run start stop wait result done cancel put""".split())


def tokens(text: str) -> int:
    return (len(text) + 3) // 4


def _clean_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


# ---------------------------------------------------------------- naming

def _split_words(text: str) -> list[str]:
    """`refreshFeed`, `refresh_feed`, `RefreshFeed` -> ["refresh", "feed"]."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return [w for w in re.split(r"[^A-Za-z0-9]+", text.lower()) if w]


def _short_sig(symbol: Symbol, width: int = 110) -> str:
    sig = symbol.signature or symbol.label
    sig = re.sub(r"^(async\s+)?def\s+", r"\1", sig)
    sig = sig.replace("(self, ", "(").replace("(self)", "()").replace("(cls, ", "(").replace("(cls)", "()")
    if symbol.qualname and "." in symbol.qualname and not sig.startswith(("class ", "const ", "let ", "function ")):
        head = symbol.qualname.rsplit(".", 1)[0]
        if not sig.startswith(head):
            sig = f"{head}.{sig}"
    return sig if len(sig) <= width else sig[: width - 3] + "..."


def _loc(symbol: Symbol) -> str:
    return f"{symbol.file}:{symbol.line}"


def _tag(symbol: Symbol) -> str:
    route = symbol.route
    return f"  [{route}]" if route else ""


# ---------------------------------------------------------------- find

def _score(symbol: Symbol, query_words: list[str], query_compact: str) -> float:
    name_words = _split_words(symbol.name)
    qual_words = _split_words(symbol.qualname)
    file_words = _split_words(symbol.file.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    dir_words = _split_words(symbol.file.rsplit("/", 1)[0]) if "/" in symbol.file else []
    doc_words = _split_words(symbol.doc)
    route_words = _split_words(symbol.route or "")
    score = 0.0
    matched = 0
    for word in query_words:
        best = 0.0
        for words, weight in ((name_words, 3.0), (qual_words, 2.0), (route_words, 2.0), (file_words, 1.5),
                              (doc_words, 1.0), (dir_words, 0.5)):
            if word in words:
                best = max(best, weight)
            elif len(word) >= 3 and any(w.startswith(word) or (len(w) >= 4 and word.startswith(w)) for w in words):
                best = max(best, weight * 0.6)
        if best:
            matched += 1
        score += best
    if not matched:
        return 0.0
    name_compact = "".join(name_words)
    if name_compact == query_compact:
        score += 6
    elif query_compact and name_compact.startswith(query_compact):
        score += 2
    elif len(name_words) == 1 and name_words[0] in query_words and len(name_words[0]) >= 5:
        score += 3  # `authenticate` for "authenticate user password"
    score *= matched / len(query_words)
    if symbol.kind == "module":
        score *= 0.8
    return score


def search(index: RepoIndex, query: str, kind: str | None = None, limit: int = 10) -> list[tuple[float, Symbol]]:
    query_words = _split_words(query)
    if not query_words:
        return []
    compact = "".join(query_words)
    scored = []
    for symbol in index.symbols.values():
        if kind and symbol.kind != kind:
            continue
        s = _score(symbol, query_words, compact)
        if s > 0:
            scored.append((s, symbol))
    scored.sort(key=lambda p: (-p[0], _KIND_ORDER.get(p[1].kind, 3), -index.degree(p[1]), len(p[1].id), p[1].id))
    return scored[:limit]


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
MAX_USAGES = 15


def enclosing(index: RepoIndex, file: str, line: int) -> Symbol | None:
    """Innermost function/class containing a line."""
    best = None
    for symbol in index.by_file.get(file, []):
        if symbol.line <= line <= symbol.end_line and (best is None or symbol.line >= best.line):
            best = symbol
    return best


def usages(index: RepoIndex, name: str, limit: int = MAX_USAGES) -> tuple[list[str], int]:
    """Lines where an identifier (e.g. a config field like SECRET_KEY, which is
    no function or class) appears, each with its enclosing definition."""
    pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
    hits, total = [], 0
    for file in index.files:
        for n, text in enumerate(index.lines(file), 1):
            if pattern.search(text):
                total += 1
                if len(hits) < limit:
                    owner = enclosing(index, file, n)
                    where = owner.label if owner is not None else "module level"
                    snippet = " ".join(text.split())
                    snippet = snippet if len(snippet) <= 70 else snippet[:67] + "..."
                    hits.append(f"  {file}:{n}  [{where}]  {snippet}")
    return hits, total


def find_symbol(index: RepoIndex, query: str, kind: str | None = None, limit: int = 10) -> str:
    results = search(index, query, kind, limit)
    word = query.strip()
    exact = any(s.name == word or s.qualname == word for _, s in results)
    if _IDENTIFIER.match(word) and not exact:
        hits, total = usages(index, word.rsplit(".", 1)[-1])
        if hits:
            head = [f'"{word}" is not a function/class name; it appears on {total} lines:']
            similar = ("symbols with similar names: " + ", ".join(f"{s.label} ({_loc(s)})" for _, s in results[:3])
                       if results else "")
            while True:
                shown = len(hits)
                note = [f"  (+{total - shown} more lines; Grep for the rest)"] if total > shown else []
                text = "\n".join(head + hits + note + ([similar] if similar else []))
                if tokens(text) <= FIND_BUDGET or len(hits) <= 3:
                    break
                hits.pop()
            if tokens(text) > FIND_BUDGET and similar:
                text = "\n".join(head + hits + note)
            return text
    if not results:
        return f'No symbols match "{query}". Try fewer or different words, or repo_map to browse.'
    lines = [f'{len(results)} matches for "{query}" (best first):']
    width = max(len(_loc(s)) for _, s in results)
    for _, symbol in results:
        doc = f"  -- {symbol.doc}" if symbol.doc and len(symbol.doc) < 70 else ""
        what = symbol.file if symbol.kind == "module" else _short_sig(symbol, 90)
        lines.append(f"  {symbol.kind:<8} {_loc(symbol):<{width}}  {what}{_tag(symbol)}{doc}")
    text = "\n".join(lines)
    while tokens(text) > FIND_BUDGET and len(lines) > 2:
        lines.pop()
        text = "\n".join(lines) + "\n  (more matches cut; refine the query)"
    return text


# ---------------------------------------------------------------- resolving a symbol argument

def resolve(index: RepoIndex, ref: str) -> tuple[Symbol | None, list[Symbol]]:
    """A symbol argument -> (the symbol, []) or (None, candidates).
    Accepts a repo-relative id (`app/db/crud.py:get_article`), a file path
    (`app/db/crud.py`), `file:name` with a partial path, a qualname
    (`Console.print`), or a bare name. Falls back to fuzzy search."""
    ref = _clean_path(ref)
    if not ref:
        return None, []
    # Absolute paths (copied from Grep/Read output) -> repo-relative.
    # Windows drive letters make `C:/x/a.py:func` contain two colons.
    root = str(index.root).replace("\\", "/")
    if ref.lower().startswith(root.lower() + "/"):
        ref = ref[len(root) + 1:]
    exact = index.by_id.get(ref)
    if exact is not None:
        return exact, []
    candidates: list[Symbol] = []
    if ":" in ref:
        path, _, qual = ref.rpartition(":")
        path = _clean_path(path)
        candidates = [s for s in index.symbols.values() if s.qualname == qual
                      and (s.file == path or s.file.endswith("/" + path) or s.file.endswith(path))]
    elif "/" in ref or ref.endswith((".py", ".ts", ".tsx")):
        candidates = [s for s in index.symbols.values() if s.kind == "module"
                      and (s.file == ref or s.file.endswith("/" + ref))]
    else:
        candidates = [s for s in index.symbols.values() if s.qualname == ref]
        if not candidates:
            candidates = [s for s in index.symbols.values() if s.name == ref and s.kind != "module"]
        if not candidates and "." in ref:
            # `crud.get_article`: module stem + name
            head, _, tail = ref.rpartition(".")
            candidates = [s for s in index.symbols.values() if s.qualname == tail
                          and s.file.rsplit("/", 1)[-1].rsplit(".", 1)[0] == head.rsplit(".", 1)[-1]]
        if not candidates:
            lowered = ref.lower()
            candidates = [s for s in index.symbols.values() if s.qualname.lower() == lowered]
    if len(candidates) == 1:
        return candidates[0], []
    if len(candidates) > 1:
        candidates.sort(key=lambda s: (-index.degree(s), s.id))
        return None, candidates
    results = search(index, ref, limit=8)
    if results and (len(results) == 1 or results[0][0] >= 1.5 * results[1][0]):
        return results[0][1], []
    return None, [s for _, s in results]


def _ambiguous(ref: str, candidates: list[Symbol]) -> str:
    if not candidates:
        return f'No symbol matches "{ref}". Use find_symbol to search, or repo_map to browse.'
    lines = [f'"{ref}" matches {len(candidates)} symbols; call again with one of these ids:']
    for symbol in candidates[:10]:
        lines.append(f"  {symbol.id:<56} {symbol.kind:<8} {_short_sig(symbol, 70)}")
    if len(candidates) > 10:
        lines.append(f"  (+{len(candidates) - 10} more)")
    return "\n".join(lines)


# ---------------------------------------------------------------- show

def _body(index: RepoIndex, symbol: Symbol, start: int | None = None, end: int | None = None,
          indent: str = "") -> list[str]:
    lines = index.lines(symbol.file)
    start = start or symbol.line
    end = min(end or symbol.end_line, len(lines))
    width = len(str(end))
    return [f"{indent}{n:>{width}}  {lines[n - 1]}".rstrip() for n in range(start, end + 1)]


def _decorator_start(index: RepoIndex, symbol: Symbol) -> int:
    """First line of the decorators above a def/class (decorators can span
    several lines), so the body listing includes them."""
    if not symbol.decorators:
        return symbol.line
    lines = index.lines(symbol.file)
    start = symbol.line
    n = symbol.line - 1
    while n >= 1 and symbol.line - n <= 15:
        text = lines[n - 1].strip()
        if not text or text.startswith(("def ", "class ", "async def ")):
            break
        if text.startswith("@"):
            start = n
        n -= 1
    return start


def _relation_note(link: Link) -> str:
    return {"reference": "  [passed as value]", "jsx": "  [renders]", "inherits": "  [base class]",
            "built_by": "  [uses the module value it builds]"}.get(link.relation, "")


def _callee_lines(index: RepoIndex, symbol: Symbol, budget_chars: int) -> list[str]:
    # One entry per target: a class both passed as a value and called is listed once.
    merged: dict[str, Link] = {}
    for l in index.out.get(symbol.node, []):
        if l.relation == "inherits":
            continue
        if l.other in merged:
            first = merged[l.other]
            merged[l.other] = Link(first.other, first.relation if first.relation != "call" else l.relation,
                                   min(first.line, l.line), first.file, first.count + l.count)
        else:
            merged[l.other] = Link(l.other, l.relation, l.line, l.file, l.count)
    links = sorted(merged.values(), key=lambda l: (l.line, l.other))
    if not links:
        return []
    out = ["calls (in order of first use):"]
    used = 0
    shown = 0
    for link in links:
        target = index.symbols[link.other]
        times = f" x{link.count}" if link.count > 1 else ""
        entry = [f"  L{link.line:<5} {_short_sig(target)}{_tag(target)}  -> {_loc(target)}{_relation_note(link)}{times}"]
        if target.doc:
            entry.append(f"           \"{target.doc}\"")
        body_len = target.end_line - target.line
        if target.kind == "function" and 0 < body_len <= TINY_BODY_LINES:
            entry += _body(index, target, target.line + 1, target.end_line, indent="           ")
        elif target.kind == "function" and (
                link.relation in ("reference", "built_by")
                or (link.relation == "call" and (body_len <= 12
                                                 or (target.file == symbol.file and target.name.startswith("_"))))):
            # One hop further through callbacks / thin wrappers: name what they call.
            nested = [index.symbols[l.other] for l in index.out.get(target.node, []) if l.relation != "inherits"]
            if nested:
                names = ", ".join(f"{n.label} ({_loc(n)})" for n in nested[:5])
                more = f", +{len(nested) - 5} more" if len(nested) > 5 else ""
                entry.append(f"           which calls: {names}{more}")
        size = sum(len(e) + 1 for e in entry)
        if (used + size > budget_chars or shown >= MAX_CALLEES) and shown:
            out.append(f"  (+{len(links) - shown} more callees not shown; use trace {symbol.id})")
            break
        out += entry
        used += size
        shown += 1
    return out


def _caller_lines(index: RepoIndex, symbol: Symbol) -> list[str]:
    links = index.into.get(symbol.node, [])
    if not links:
        if symbol.route:
            return [f"called by: HTTP clients ({symbol.route}); no callers in the code"]
        return ["called by: nothing in this repo (entry point, or used dynamically)"]
    out = ["called by:"]
    for link in links[:MAX_CALLERS]:
        caller = index.symbols[link.other]
        note = {"reference": " (passes it as a value)", "jsx": " (renders it)", "inherits": " (subclass)",
                "built_by": " (uses the value it builds)"}.get(link.relation, "")
        out.append(f"  {caller.label or caller.file:<40} {link.file}:{link.line}{note}")
    if len(links) > MAX_CALLERS:
        out.append(f"  (+{len(links) - MAX_CALLERS} more callers; use trace {symbol.id} direction=up)")
    return out


def _unresolved_lines(index: RepoIndex, symbol: Symbol) -> list[str]:
    chains = index.unresolved.get(symbol.node, [])
    if not chains:
        return []
    maybe_internal = []
    seen = set()
    for chain in chains:
        label = ".".join(chain)
        if label in seen:
            continue
        seen.add(label)
        if chain[-1] in index.names and (len(chain) == 1 or chain[-1] not in _COMMON_METHODS):
            maybe_internal.append(label)
    other = len(seen) - len(maybe_internal)
    parts = []
    if maybe_internal:
        parts.append("could not resolve (may be in this repo): " + ", ".join(maybe_internal[:6]))
    if other:
        parts.append(f"{other} other calls go to libraries/builtins (not shown)")
    return ["; ".join(parts)]


def _subclasses(index: RepoIndex, cls: Symbol, depth: int = 0) -> list[Symbol]:
    out = []
    for link in index.into.get(cls.node, []):
        if link.relation == "inherits" and depth < 4:
            sub = index.symbols[link.other]
            out.append(sub)
            out += _subclasses(index, sub, depth + 1)
    return out


def _bases_of(index: RepoIndex, cls: Symbol, depth: int = 0) -> list[Symbol]:
    out = []
    for link in index.out.get(cls.node, []):
        if link.relation == "inherits" and depth < 4:
            base = index.symbols[link.other]
            out.append(base)
            out += _bases_of(index, base, depth + 1)
    return out


def _override_lines(index: RepoIndex, symbol: Symbol, parent: Symbol | None) -> list[str]:
    """For a method: which base method it overrides and which subclass
    methods override it (implementations of an interface method)."""
    if parent is None or parent.kind != "class" or symbol.kind != "function":
        return []
    out = []
    for base in _bases_of(index, parent):
        over = index.by_id.get(f"{base.file}:{base.qualname}.{symbol.name}")
        if over is not None:
            out.append(f"  overrides {over.label} ({_loc(over)})")
            break
    implementations = []
    for sub in _subclasses(index, parent):
        impl = index.by_id.get(f"{sub.file}:{sub.qualname}.{symbol.name}")
        if impl is not None and impl not in implementations:
            implementations.append(impl)
    if implementations:
        out.append("  overridden by: " + ", ".join(f"{i.label} ({_loc(i)})" for i in implementations[:10])
                   + (f" (+{len(implementations) - 10} more)" if len(implementations) > 10 else ""))
    return out


def _member_lines(index: RepoIndex, symbol: Symbol) -> list[str]:
    out = []
    for member in index.children_of(symbol):
        doc = f"  -- {member.doc}" if member.doc else ""
        out.append(f"  {member.file}:{member.line}-{member.end_line}  {_short_sig(member, 100)}{_tag(member)}{doc}")
    return out


def _show_module(index: RepoIndex, module: Symbol, detail: str) -> str:
    lines = [f"{module.file}  ({module.end_line} lines)"]
    if module.doc:
        lines.append(f'  "{module.doc}"')
    top = [s for s in index.by_file.get(module.file, []) if "." not in s.qualname]
    lines.append("defines:")
    for symbol in top:
        doc = f"  -- {symbol.doc}" if symbol.doc else ""
        lines.append(f"  {symbol.line}-{symbol.end_line}  {_short_sig(symbol, 100)}{_tag(symbol)}{doc}")
        if symbol.kind == "class":
            for member in index.children_of(symbol):
                mdoc = f"  -- {member.doc}" if member.doc and len(member.doc) < 60 else ""
                lines.append(f"      {member.line}-{member.end_line}  {_short_sig(member, 90)}{mdoc}")
    callers = {index.symbols[l.other].file for s in top for l in index.into.get(s.node, [])} - {module.file}
    if callers:
        lines.append(f"used by {len(callers)} other files: " + ", ".join(sorted(callers)[:8])
                     + (" ..." if len(callers) > 8 else ""))
    module_level = [l for l in index.out.get(module.node, [])]
    if module_level:
        lines.append("top-level code calls: " + ", ".join(
            f"{index.symbols[l.other].label} (L{l.line})" for l in module_level[:8]))
    text = "\n".join(lines)
    if tokens(text) > SHOW_BUDGET:
        keep = []
        for line in lines:
            if tokens("\n".join(keep + [line])) > SHOW_BUDGET - 30:
                keep.append(f"(cut: {len(lines) - len(keep)} more lines; show a class or function for detail)")
                break
            keep.append(line)
        text = "\n".join(keep)
    return text


def show(index: RepoIndex, ref: str, detail: str | None = None) -> str:
    symbol, candidates = resolve(index, ref)
    if symbol is None:
        return _ambiguous(ref, candidates)
    detail = (detail or "").lower() or None
    if symbol.kind == "module":
        return _show_module(index, symbol, detail or "outline")
    if detail is None:
        detail = "outline" if symbol.kind == "class" else "full"
    if detail not in ("signature", "outline", "full"):
        detail = "full"

    header = f"{symbol.file}:{symbol.line}-{symbol.end_line}  {symbol.signature or symbol.label}"
    lines = [header]
    if detail != "full":  # in full mode the decorators are part of the body listing
        for deco in symbol.decorators:
            lines.append(f"  {deco}")
    if symbol.route:
        lines.append(f"  HTTP route: {symbol.route}")
    parent = index.parent_of(symbol)
    if parent is not None:
        lines.append(f"  in {parent.kind} {parent.label} ({_loc(parent)})")
    if symbol.doc:
        lines.append(f'  "{symbol.doc}"')
    lines += _override_lines(index, symbol, parent)
    if detail == "signature":
        return "\n".join(lines)

    budget_chars = SHOW_BUDGET * 4
    tail: list[str] = []
    if symbol.kind == "class":
        bases = [l for l in index.out.get(symbol.node, []) if l.relation == "inherits"]
        if bases:
            tail.append("bases: " + ", ".join(f"{index.symbols[l.other].label} ({_loc(index.symbols[l.other])})" for l in bases))
        subclasses = [l for l in index.into.get(symbol.node, []) if l.relation == "inherits"]
        if subclasses:
            tail.append("subclasses: " + ", ".join(index.symbols[l.other].label for l in subclasses[:12])
                        + (f" (+{len(subclasses) - 12} more)" if len(subclasses) > 12 else ""))
        members = _member_lines(index, symbol)
        if members:
            tail.append("members:")
            tail += members
        users = [l for l in index.into.get(symbol.node, []) if l.relation != "inherits"]
        if users:
            tail.append("used by: " + ", ".join(f"{index.symbols[l.other].label or l.file} ({l.file}:{l.line})"
                                                 for l in users[:10]) + (f" (+{len(users) - 10} more)" if len(users) > 10 else ""))
    else:
        tail += _caller_lines(index, symbol)
        tail += _unresolved_lines(index, symbol)

    callee_budget = budget_chars // 3
    callees = _callee_lines(index, symbol, callee_budget) if symbol.kind != "class" else []
    fixed = "\n".join(lines + callees + tail)
    body: list[str] = []
    if detail == "full":
        start = _decorator_start(index, symbol)
        full_body = _body(index, symbol, start)
        room = budget_chars - len(fixed) - 120
        if room <= 0:
            body = [f"(body {symbol.length} lines not shown to stay within budget; Read {symbol.file}:{symbol.line}-{symbol.end_line})"]
        else:
            used = 0
            for i, line in enumerate(full_body):
                if used + len(line) + 1 > room:
                    last = start + i - 1
                    body.append(f"   ... body cut at line {last} of {symbol.end_line} to stay within budget; "
                                f"Read {symbol.file}:{last + 1}-{symbol.end_line} for the rest")
                    break
                body.append(line)
                used += len(line) + 1
    elif symbol.kind == "class" and detail == "outline":
        pass
    sections = lines + ([""] + body if body else []) + ([""] + callees if callees else []) + ([""] + tail if tail else [])
    return "\n".join(sections).rstrip()


# ---------------------------------------------------------------- trace

def _down_links(index: RepoIndex, node: str, keep: str | None = None) -> list[Link]:
    """Execution flow only: classes (types passed around, constructors) are
    left out of traces unless they are the requested end."""
    return [l for l in index.out.get(node, []) if l.relation != "inherits"
            and (index.symbols[l.other].kind != "class" or l.other == keep)]


def _up_links(index: RepoIndex, node: str, keep: str | None = None) -> list[Link]:
    return [l for l in index.into.get(node, []) if l.relation != "inherits"]


def _hop_label(index: RepoIndex, link: Link) -> str:
    target = index.symbols[link.other]
    note = {"reference": " [passed as value]", "jsx": " [renders]", "built_by": " [uses value it builds]"}.get(link.relation, "")
    return f"{target.label or target.file}{note}  (L{link.line} -> {_loc(target)})"


def trace(index: RepoIndex, start: str, end: str | None = None, direction: str = "down", depth: int = 3) -> str:
    source, candidates = resolve(index, start)
    if source is None:
        return _ambiguous(start, candidates)
    direction = "up" if (direction or "").lower() in ("up", "callers", "in") else "down"
    neighbours = _down_links if direction == "down" else _up_links
    depth = max(1, min(int(depth or 3), 6))

    if end:
        target, candidates = resolve(index, end)
        if target is None:
            return _ambiguous(end, candidates)
        # BFS for up to 3 shortest paths (by hops) from source to target.
        paths: list[list[Link]] = []
        queue = deque([(source.node, [])])
        best = None
        visited_at: dict[str, int] = {source.node: 0}
        while queue and len(paths) < 3:
            node, path = queue.popleft()
            if best is not None and len(path) > best:
                break
            for link in neighbours(index, node, target.node):
                if any(l.other == link.other for l in path) or link.other == source.node:
                    continue
                new_path = path + [link]
                if link.other == target.node:
                    paths.append(new_path)
                    best = len(new_path)
                    continue
                if len(new_path) < 8 and visited_at.get(link.other, 99) >= len(new_path):
                    visited_at[link.other] = len(new_path)
                    queue.append((link.other, new_path))
        if not paths:
            other = "callers" if direction == "down" else "callees"
            return (f"No call path from {source.label} to {target.label} in the graph ({direction}). "
                    f"It may go through dynamic dispatch or code RudhMap couldn't resolve; try direction="
                    f"{'up' if direction == 'down' else 'down'} or show either symbol to see its {other}.")
        lines = []
        for i, path in enumerate(paths, 1):
            lines.append(f"path {i} ({len(path)} hops):" if len(paths) > 1 else f"{len(path)} hops:")
            lines.append(f"  {source.label}  ({_loc(source)})")
            for k, link in enumerate(path, 1):
                lines.append(f"  {'  ' * k}-> {_hop_label(index, link)}")
        return "\n".join(lines)

    # Tree of everything reachable (down) or every caller (up), to `depth`.
    lines = [f"{source.label}  ({_loc(source)})  {'calls' if direction == 'down' else 'is called by'}:"]
    seen = {source.node}
    budget_chars = TRACE_BUDGET * 4
    truncated = 0

    footer_room = 120  # the "+N more branches cut" line must fit too

    def walk(node: str, level: int, used_depth: int) -> None:
        nonlocal truncated
        for link in neighbours(index, node):
            text = f"{'  ' * level}- {_hop_label(index, link)}"
            if link.other in seen:
                text += "  (see above)"
            if sum(len(l) + 1 for l in lines) + len(text) > budget_chars - footer_room:
                truncated += 1
                continue
            lines.append(text)
            if link.other not in seen:
                seen.add(link.other)
                # Handing a function over as a value / using the value it builds
                # is an indirection, not a level of the call tree: it doesn't
                # use up depth (the budget still bounds the output).
                cost = 0 if link.relation in ("reference", "built_by") else 1
                if used_depth + cost <= depth and level < depth + 4:
                    walk(link.other, level + 1, used_depth + cost)

    walk(source.node, 1, 1)
    if len(lines) == 1:
        lines.append("  (nothing in this repo)" if direction == "down" else "  (no callers in this repo)")
    if truncated:
        lines.append(f"(+{truncated} more branches cut to stay within budget; trace a deeper symbol or pass end=...)")
    return "\n".join(lines)


# ---------------------------------------------------------------- repo_map

def repo_map(index: RepoIndex, path: str | None = None, budget: int = MAP_BUDGET) -> str:
    prefix = _clean_path(path or "").rstrip("/")
    files = [f for f in index.files if not prefix or f == prefix or f.startswith(prefix + "/")]
    if not files:
        return f'No source files under "{path}". Known top-level folders: ' + ", ".join(
            sorted({f.split("/", 1)[0] for f in index.files if "/" in f})[:20])
    total_symbols = sum(len(index.by_file.get(f, [])) for f in files)
    routes = [s for f in files for s in index.by_file.get(f, []) if s.route]
    header = f"{prefix or index.root.name}: {len(files)} source files, {total_symbols} functions/classes"
    if routes:
        header += f", {len(routes)} HTTP routes"

    def ranked(f: str) -> list[Symbol]:
        members = [s for s in index.by_file.get(f, []) if s.qualname.count(".") <= 1]
        return sorted(members, key=lambda s: (-(index.degree(s) + (5 if s.route else 0) + (2 if s.doc else 0)), s.line))

    def file_score(f: str) -> int:
        return sum(index.degree(s) for s in index.by_file.get(f, []))

    def render(per_file: int, max_files_per_dir: int) -> str:
        out = [header]
        dirs: dict[str, list[str]] = {}
        for f in files:
            dirs.setdefault(f.rsplit("/", 1)[0] if "/" in f else ".", []).append(f)
        for d in sorted(dirs):
            members = sorted(dirs[d], key=lambda f: (-file_score(f), f))
            module_doc = ""
            out.append(f"{d}/")
            for f in members[:max_files_per_dir]:
                top = ranked(f)
                names = []
                for s in top[:per_file]:
                    label = s.label + (f" [{s.route}]" if s.route else "")
                    names.append(label)
                extra = f", +{len(top) - per_file}" if len(top) > per_file else ""
                module = index.by_id.get(f)
                module_doc = f"  -- {module.doc}" if module is not None and module.doc and len(module.doc) < 80 else ""
                out.append(f"  {f.rsplit('/', 1)[-1]}: {', '.join(names)}{extra}{module_doc}" if names
                           else f"  {f.rsplit('/', 1)[-1]}{module_doc}")
            if len(members) > max_files_per_dir:
                out.append(f"  (+{len(members) - max_files_per_dir} more files)")
        return "\n".join(out)

    for per_file, max_files in ((8, 40), (6, 25), (5, 15), (4, 10), (3, 8), (2, 6), (1, 4), (0, 3)):
        text = render(per_file, max_files)
        if tokens(text) <= budget:
            return text
    # Still too big: list folders only.
    dirs: dict[str, int] = {}
    for f in files:
        top = f[len(prefix) + 1:] if prefix else f
        key = top.split("/", 1)[0] if "/" in top else "."
        dirs[key] = dirs.get(key, 0) + 1
    out = [header, "too large to list files; folders (files):"]
    for d, n in sorted(dirs.items(), key=lambda p: -p[1]):
        out.append(f"  {(prefix + '/' if prefix else '')}{d}/ ({n})")
        if tokens("\n".join(out)) > budget - 20:
            out.append("  ...")
            break
    out.append("(call repo_map with path=<folder> to zoom in)")
    return "\n".join(out)
