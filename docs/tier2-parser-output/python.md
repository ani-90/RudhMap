# `parse_python_ast` output reference

Extractor: [`src/rudhmap/extract/tier2_ast/python.py`](../../src/rudhmap/extract/tier2_ast/python.py)
Schema: [`docs/tier2_ast_schema.md`](../tier2_ast_schema.md)

Read-only reference, not a test suite — `tests/` is untouched. This shows
the actual `EvidenceRecord`/`EdgeRecord` output for the fixture repo used
in `tests/test_tier2_python.py`, so the shape of Tier 2's output is
visible without running anything.

---

## Fixture: `tests/fixtures/tier2_ast/app.py`

```python
import boto3
from ingest.writer import put_object as write_object

s3 = boto3.client("s3")


class Handler:
    def process(self, batch):
        write_object(batch)
        self.validate(batch)

    def validate(self, batch):
        return len(batch) > 0


@app.route("/telemetry")
def handle_post():
    result = do_local_work()
    return result


def do_local_work():
    return 1
```

`ingest.writer` and `app` are never actually defined or imported anywhere
on disk near this fixture — that's deliberate. Tier 2 never touches the
filesystem, so it doesn't matter whether either resolves to a real module;
the output below is identical either way.

---

## Output

```json
{
  "nodes": [
    {
      "kind": "class",
      "identity": "tests\\fixtures\\tier2_ast\\app.py:Handler",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 7,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "Handler", "qualname": "Handler" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.py:Handler.process",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 8,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "process", "qualname": "Handler.process" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.py:Handler.validate",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 12,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "validate", "qualname": "Handler.validate" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.py:handle_post",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 17,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "handle_post", "qualname": "handle_post" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.py:do_local_work",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 22,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "do_local_work", "qualname": "do_local_work" }
    }
  ],
  "edges": [
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py",
      "dst": "boto3",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 1,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "kind": "import", "module": "boto3", "names": [], "raw": "import boto3" }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py",
      "dst": "ingest.writer",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 2,
      "tier": 2,
      "confidence": 1.0,
      "attrs": {
        "kind": "import",
        "module": "ingest.writer",
        "names": ["put_object"],
        "raw": "from ingest.writer import put_object as write_object"
      }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py",
      "dst": "boto3.client",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 4,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["boto3", "client"], "likely_import_alias": true }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py:Handler.process",
      "dst": "write_object",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 9,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["write_object"], "likely_import_alias": true }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py:Handler.process",
      "dst": "self.validate",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 10,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["self", "validate"], "likely_import_alias": false }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py:Handler.validate",
      "dst": "len",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 13,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["len"], "likely_import_alias": false }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py",
      "dst": "app.route",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 16,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["app", "route"], "likely_import_alias": false }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.py:handle_post",
      "dst": "do_local_work",
      "file": "tests\\fixtures\\tier2_ast\\app.py",
      "line": 18,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["do_local_work"], "likely_import_alias": false }
    }
  ]
}
```

5 nodes, 8 edges (2 import, 6 call).

---

## Reading the identity scheme

Every def's `identity` is `{file}:{qualname}`, where `qualname` stacks
enclosing `class`/`def` names top to bottom:

- `Handler` — top-level class, `qualname` is just its own name.
- `Handler.process` / `Handler.validate` — methods, `qualname` prefixes
  the enclosing class.
- `handle_post`, `do_local_work` — top-level functions, no prefix.

This identity is **only unique within this one file**. Nothing here checks
whether some other file in the repo also defines a `Handler.process` —
that collision, and folding two same-named defs from different files into
one corroborated node (or correctly keeping them separate), is Stage 2's
job, not Tier 2's.

## `src` on edges: file path vs. `file:qualname`

Compare the `boto3.client(...)` call (line 4, `src` is the bare file path)
against the `write_object(batch)` call (line 9, `src` is
`...app.py:Handler.process`). The bare path means the statement is at
module level — `s3 = boto3.client("s3")` runs when the module is imported,
outside any function body. Once a statement is inside a `def`, `src`
carries that def's full qualname.

## The decorator is a call too

`@app.route("/telemetry")` on line 16 produces its own call edge —
`callee_chain: ["app", "route"]` — with `src` at **module scope**, not
`handle_post`'s scope, even though the decorator sits directly above the
function it decorates. That's correct: a decorator expression evaluates in
the enclosing scope at class/module-definition time, before the function
object it wraps even exists yet.

## Why every edge is dangling

- **Import edges** — `dst` is `boto3` and `ingest.writer` verbatim. Neither
  is checked against any file on disk; `ingest/writer.py` doesn't even
  exist in this fixture. That's fine — resolving an import string to the
  file that actually defines it is explicitly out of scope for this tier
  (see `docs/tier2_ast_schema.md`, "What tier 2 does NOT do").
- **Call edges** — `callee_chain` is the attribute chain exactly as
  written, never checked against any known definition, even within the
  *same* file. `self.validate` (line 10) happens to be resolvable by eye —
  `Handler.validate` is defined two lines below — but Tier 2 makes no such
  connection itself; it just records `["self", "validate"]` and leaves the
  match to Stage 2, symmetric with `app.route` where no local candidate
  exists at all.

## `likely_import_alias`: a hint, not a resolution

Three calls have `likely_import_alias: true`: `boto3.client(...)` (`boto3`
was bound by `import boto3` on line 1) and `write_object(...)` (bound by
the `as write_object` alias on line 2). Everything else — `self.validate`,
`len`, `app.route`, `do_local_work` — is `false`, because `self`, `len`,
`app`, and `do_local_work` are not names this file's own import table
binds. Note `do_local_work` is `false` even though it's a real, resolvable
local function defined two lines later — `likely_import_alias` only
answers "did an import bind this name," never "does this name resolve to
something." A local def match is exactly the kind of same-file lookup
Tier 2 deliberately leaves to Stage 2.
