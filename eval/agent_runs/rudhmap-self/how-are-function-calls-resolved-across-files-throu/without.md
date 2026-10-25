# without get_context: how are function calls resolved across files through imports

Cross-file call resolution happens in two stages. The extractor records what each call is bound to. A later graph pass turns that into a real node.

**1. Extraction (tier 2).** In `src/rudhmap/extract/tier2_ast/python.py:141-157`, each call's first name is looked up in the file's import table.
- A bare call of a `from m import name` binding gets `resolved_module` and `resolved_name` (`python.py:149-151`).
- An attribute call such as `crud.create_user()` gets `resolved_dotted_path`. It is built from what the local name is bound to, plus the rest of the chain (`python.py:156-157`).
- The TypeScript extractor sets `resolved_name` the same way (`typescript.py:167,170`).

**2. Resolution.** `resolve_cross_file_calls` (`src/rudhmap/graph/resolve.py:190-207`) takes the edges that were dropped as dangling. For each, `_cross_file_candidate_identity` (`resolve.py:164-187`) builds a candidate node id of the form `file:name`. The edge is re-added only if both endpoints exist as nodes (`resolve.py:198-203`).

How the target file is found:
- **Python dotted path:** `_resolve_dotted_attribute_path` (`resolve.py:144-161`) tries every split into (module, qualname). It succeeds only if exactly one split names both a scanned file and an existing node. Class attributes like `User.create()` resolve the same way.
- **Python module:** `_suffix_matches` (`resolve.py:128-134`) matches the dotted module against scanned file paths, as either `x.py` or `x/__init__.py`. More than one match leaves it unresolved.
- **TS/JS relative imports:** `_resolve_relative_module_file` (`resolve.py:113-125`) joins the importing file's directory with the path. It then tries the known extensions and `index.*` files.

**Deliberately unresolved** (`resolve.py:103-107`, `176-178`, `181-182`):
- bare TS specifiers (external packages)
- Python leading-dot relative imports
- ambiguous matches
