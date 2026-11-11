"""Step B TypeScript/React extraction, end to end through `build_assembly`:
arrow-function components are definitions, JSX use and default imports are
connections, tsconfig path aliases and barrel re-exports resolve. Each test
also checks what must NOT be connected."""
from __future__ import annotations

from pathlib import Path

from rudhmap.paths import Relativizer
from rudhmap.pipeline import build_assembly


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _graph(root: Path):
    graph = build_assembly(str(root), verbose=False).result.graph
    rel = Relativizer(root)
    edges = {
        (rel(u), rel(v))
        for u, v, d in graph.edges(data=True)
        if d["evidence"].attrs.get("kind") != "import"
    }
    nodes = {rel(n): graph.nodes[n]["evidence"][0] for n in graph.nodes}
    return nodes, edges


def test_arrow_function_component_is_a_definition_with_signature(tmp_path):
    _write(tmp_path, {"src/Card.tsx": "/** Shows one card. */\nconst Card = ({ title }: Props) => {\n  return <div>{title}</div>\n}\nexport default Card\n"})
    nodes, _ = _graph(tmp_path)
    card = nodes["src/Card.tsx:Card"]
    assert card.kind == "function"
    assert card.attrs["signature"] == "const Card = ({ title }: Props)"
    assert card.attrs["doc"] == "Shows one card."
    assert nodes["src/Card.tsx"].attrs["default_export"] == "Card"


def test_jsx_use_of_default_import_connects_and_html_tags_do_not(tmp_path):
    _write(tmp_path, {
        "src/Card.tsx": "const Card = () => <span />\nexport default Card\n",
        "src/Page.tsx": "import Card from './Card'\nexport function Page() {\n  return <div><Card /></div>\n}\n",
    })
    _, edges = _graph(tmp_path)
    assert ("src/Page.tsx:Page", "src/Card.tsx:Card") in edges
    assert not any(dst.endswith(":div") or dst.endswith(":span") for _, dst in edges)


def test_tsconfig_path_alias_and_barrel_reexport_resolve(tmp_path):
    _write(tmp_path, {
        "tsconfig.json": '{\n  // comment\n  "compilerOptions": { /* x */ "paths": { "@/*": ["./src/*"] }, },\n}\n',
        "src/client/sdk.gen.ts": "export class ItemsService {\n  public static deleteItem(id: string) { return id }\n}\n",
        "src/client/index.ts": "export { ItemsService } from './sdk.gen';\n",
        "src/components/Delete.tsx": "import { ItemsService } from '@/client'\nexport const Delete = () => {\n  ItemsService.deleteItem('1')\n  return null\n}\n",
    })
    _, edges = _graph(tmp_path)
    assert ("src/components/Delete.tsx:Delete", "src/client/sdk.gen.ts:ItemsService.deleteItem") in edges


def test_star_reexport_resolves_but_an_unexported_name_does_not(tmp_path):
    _write(tmp_path, {
        "src/lib/a.ts": "export function helper() { return 1 }\n",
        "src/lib/index.ts": "export * from './a'\n",
        "src/use.ts": "import { helper, missing } from './lib'\nexport function run() {\n  helper()\n  missing()\n}\n",
    })
    _, edges = _graph(tmp_path)
    assert ("src/use.ts:run", "src/lib/a.ts:helper") in edges
    assert not any(dst.endswith(":missing") for _, dst in edges)


def test_bind_counts_as_use_of_the_function(tmp_path):
    _write(tmp_path, {
        "src/utils.ts": "export const handleError = function (this: any, err: Error) { this(err) }\n",
        "src/Form.tsx": "import { handleError } from './utils'\nexport const Form = () => {\n  const cb = handleError.bind(console.log)\n  return null\n}\n",
    })
    _, edges = _graph(tmp_path)
    assert ("src/Form.tsx:Form", "src/utils.ts:handleError") in edges


def test_bare_package_import_stays_unresolved(tmp_path):
    _write(tmp_path, {
        "tsconfig.json": '{"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}',
        "src/App.tsx": "import { useState } from 'react'\nexport const App = () => {\n  useState(0)\n  return null\n}\n",
    })
    _, edges = _graph(tmp_path)
    assert not any(src == "src/App.tsx:App" for src, _ in edges)
