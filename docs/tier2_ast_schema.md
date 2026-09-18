# Tier 2 AST — evidence schema (write before code, per spec Stage 1/Stage 2 boundary)

Tier 2 parses one file's AST at a time. It has no filesystem view beyond
that file, so any reference to something outside the file it's currently
parsing — an imported module, a called symbol that might live elsewhere —
is emitted as a **dangling reference**: structurally complete, but not yet
resolved to another node's identity. Resolving those against the rest of
the repo's evidence is Stage 2 (Graph Assembly), not this tier. See
`rudhmap-final-spec_2.md` §Stage 1 (Tier 2) and §Stage 2 (identity
resolution) — this doc only pins down the emission shape tier2 commits to
on day one, so Stage 2 has a stable contract to consume later.

This applies to Python first; the same shape carries over to the
TypeScript visitor when it's built.

## Identity scheme (defs)

A function/class definition's `identity` is **local to its own file only**
— it is not a resolved cross-module symbol:

```
{file_path}:{qualname}
```

`qualname` is the dotted path of enclosing `class`/`def` names from the
file's top level down to this definition (e.g. `Handler.process`, or just
`process` for a top-level function). Nested functions stack the same way
(`outer.inner`). No attempt is made to disambiguate this against same-named
defs in other files — that collision is exactly what Stage 2's identity
resolution exists to sort out.

`kind` is `"function"` or `"class"`. `confidence` is always `1.0` — that a
def exists at this location is a structural fact, not an inference.

## Import edges

One `EdgeRecord` per import statement (not per imported name — all names
pulled in by one `from x import a, b` share a single record, matching
`names` being a list).

```python
EdgeRecord(
    src=<enclosing scope identity, or the bare file path if the import
         is at module level>,
    dst=<module string, unresolved — exactly what dst means for every
         dangling reference in this tier>,
    file=..., line=..., tier=2, confidence=1.0,
    attrs={
        "kind": "import",
        "module": "ingest.writer",       # module path exactly as written
        "names": ["put_object"],          # names pulled from it; [] for `import x` style
        "raw": "from ingest.writer import put_object",
    },
)
```

`attrs` is canonical. `dst` mirrors `attrs["module"]` so every `EdgeRecord`
has a usable flat string without a caller needing to branch on `attrs`
shape first — but Stage 2 must read `attrs`, not parse `dst`.

## Call edges

```python
EdgeRecord(
    src=<caller's def identity, or the bare file path if the call happens
         at module level, outside any function/class body>,
    dst=<".".join(callee_chain) — flattened, human-readable only>,
    file=..., line=..., tier=2, confidence=1.0,
    attrs={
        "callee_chain": ["writer", "put_object"],  # attribute chain as a list, NOT "writer.put_object"
        "likely_import_alias": True,  # True iff callee_chain[0] is a name bound
                                       # in *this file's* import table
    },
)
```

`likely_import_alias` is computed while walking this file only — the
import table (name → module string) is built during the same pass, before
or alongside the calls that might reference it. It is a hint for Stage 2,
not a resolution: `True` means "this call's root name came from an import
in this file," not "this call has been matched to a definition."

## What tier 2 does NOT do

- No filesystem walk to turn an import's module string into a file path.
- No matching a call's `callee_chain` against any def outside the current
  file (or even confirming a same-file match beyond what's structurally
  obvious from the identity string).
- No deduplication or merging of evidence across files or tiers.

Every dangling `dst`/`module`/`callee_chain` is exactly what the AST says,
nothing more — symmetric with how Tier 0's Terraform parser emits
unresolved `dst` refs like `module.foo` for anything it can't itself
confirm as a resource identity, and leaves reconciliation to a later stage.
