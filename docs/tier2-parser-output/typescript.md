# `parse_typescript_ast` output reference

Extractor: [`src/rudhmap/extract/tier2_ast/typescript.py`](../../src/rudhmap/extract/tier2_ast/typescript.py)
Schema: [`docs/tier2_ast_schema.md`](../tier2_ast_schema.md)

Read-only reference, not a test suite — `tests/` is untouched. This shows
the actual `EvidenceRecord`/`EdgeRecord` output for the fixture repo used
in `tests/test_tier2_typescript.py`, so the shape of Tier 2's TypeScript
output is visible without running anything. It commits to the same
emission contract as `python.md` — same identity scheme, same import/call
edge shapes — so this doc only calls out where TS syntax differs.

---

## Fixture: `tests/fixtures/tier2_ast/app.ts`

```typescript
import * as boto3 from "boto3";
import { putObject as writeObject } from "./ingest/writer";

const s3 = boto3.client("s3");

class Handler {
  @Route("/telemetry")
  process(batch: any) {
    writeObject(batch);
    this.validate(batch);
  }

  validate(batch: any) {
    return batch.length > 0;
  }
}

function handlePost() {
  const result = doLocalWork();
  return result;
}

function doLocalWork() {
  return 1;
}
```

`boto3`, `./ingest/writer`, and `Route` are never actually defined or
resolvable anywhere on disk near this fixture — that's deliberate, same as
`python.md`'s fixture. Tier 2 never touches the filesystem, so it doesn't
matter whether any of them resolve to something real.

`.tsx` files are parsed with a separate grammar (`tree_sitter_typescript.language_tsx`)
selected purely by file extension — JSX syntax needs it, but the emission
shape is identical to `.ts`.

---

## Output

```json
{
  "nodes": [
    {
      "kind": "class",
      "identity": "tests\\fixtures\\tier2_ast\\app.ts:Handler",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 6,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "Handler", "qualname": "Handler" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.ts:Handler.process",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 8,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "process", "qualname": "Handler.process" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.ts:Handler.validate",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 13,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "validate", "qualname": "Handler.validate" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.ts:handlePost",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 18,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "handlePost", "qualname": "handlePost" }
    },
    {
      "kind": "function",
      "identity": "tests\\fixtures\\tier2_ast\\app.ts:doLocalWork",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 23,
      "tier": 2,
      "confidence": 1.0,
      "subtype": null,
      "attrs": { "name": "doLocalWork", "qualname": "doLocalWork" }
    }
  ],
  "edges": [
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts",
      "dst": "boto3",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 1,
      "tier": 2,
      "confidence": 1.0,
      "attrs": {
        "kind": "import",
        "module": "boto3",
        "names": ["*"],
        "raw": "import * as boto3 from \"boto3\";"
      }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts",
      "dst": "./ingest/writer",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 2,
      "tier": 2,
      "confidence": 1.0,
      "attrs": {
        "kind": "import",
        "module": "./ingest/writer",
        "names": ["putObject"],
        "raw": "import { putObject as writeObject } from \"./ingest/writer\";"
      }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts",
      "dst": "boto3.client",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 4,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["boto3", "client"], "likely_import_alias": true }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts:Handler",
      "dst": "Route",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 7,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["Route"], "likely_import_alias": false }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts:Handler.process",
      "dst": "writeObject",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 9,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["writeObject"], "likely_import_alias": true }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts:Handler.process",
      "dst": "this.validate",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 10,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["this", "validate"], "likely_import_alias": false }
    },
    {
      "src": "tests\\fixtures\\tier2_ast\\app.ts:handlePost",
      "dst": "doLocalWork",
      "file": "tests\\fixtures\\tier2_ast\\app.ts",
      "line": 19,
      "tier": 2,
      "confidence": 1.0,
      "attrs": { "callee_chain": ["doLocalWork"], "likely_import_alias": false }
    }
  ]
}
```

## Notes specific to TypeScript

- **Import shapes.** TS has three local-binding forms tier2 distinguishes
  in `import_table` (used only to compute `likely_import_alias`) while
  still emitting one `EdgeRecord` per statement, same as Python:
  - `import * as boto3 from "boto3"` → namespace import, `names: ["*"]`.
  - `import { putObject as writeObject } from "./x"` → named import,
    `names` holds the **original** exported name (`"putObject"`), not the
    local alias — mirrors Python's `from x import a as b` behavior in
    `python.md`, where `names` also records the pre-alias name.
  - `import Foo from "x"` (default import) → `names: ["default"]`, not
    demonstrated in this fixture.
  - `import "./polyfill"` (side-effect only, no bindings) → `names: []`,
    same shape as Python's `import x`.
- **Decorators are ordinary siblings, not a wrapper node.** Python's
  grammar wraps a decorated def in a `decorated_definition` node, so tier2
  has to unwrap it explicitly. TypeScript's grammar instead places
  `decorator` as a plain sibling immediately before the `method_definition`
  it decorates, inside the same `class_body`. A normal tree walk therefore
  visits the decorator's call (`Route("/telemetry")`) at the **enclosing
  class's scope** (`Handler`) automatically, without any special-casing —
  same *effective* behavior as Python (decorator call attributed to the
  enclosing scope, not the decorated function), reached by a different
  grammar shape.
- **`this` is a real chain link.** `this.validate(batch)` flattens to
  `["this", "validate"]`, exactly like Python's `self.validate(batch)` →
  `["self", "validate"]`. Neither `this` nor `self` is ever in
  `import_table`, so `likely_import_alias` is `false` for both.
- **`.ts` vs `.tsx`.** Selected purely by file extension against two
  separately compiled tree-sitter grammars
  (`tree_sitter_typescript.language_typescript` /
  `.language_tsx`); nothing else in the extractor branches on it.
