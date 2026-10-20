"""Build -> (slice) -> verify -> render -> write, shared by the CLI's
`diagram` command and the MCP `generate_diagram` tool so both always write
the same file for the same input."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rudhmap.paths import Relativizer
from rudhmap.pipeline import VerifiedView, build_view
from rudhmap.render.drawio import render_drawio


@dataclass
class DiagramResult:
    view: VerifiedView
    output_path: Path | None = None


def _slug(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    return slug[:40].rstrip("-") or "query"


def default_output_path(repo_root: Path, query: str | None) -> Path:
    name = "rudhmap.drawio" if query is None else f"rudhmap-{_slug(query)}.drawio"
    return repo_root / name


def generate_diagram(
    repo_root: Path,
    query: str | None = None,
    max_nodes: int = 60,
    output_path: Path | None = None,
) -> DiagramResult:
    """Write a .drawio file for the whole repo (`query=None`) or a slice.
    Nothing is written unless the view's status is "ok"."""
    if output_path is not None and output_path.suffix != ".drawio":
        raise ValueError(f"output path must end in .drawio, got {output_path}")

    view = build_view(repo_root, query, max_nodes)
    if view.status != "ok":
        return DiagramResult(view)

    title = f"{repo_root.name}: full structural graph" if query is None else f"{repo_root.name}: {query}"
    xml = render_drawio(view.verification.ir, title=title, rel=Relativizer(repo_root))
    path = output_path or default_output_path(repo_root, query)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-8", newline="\n")
    return DiagramResult(view, path)
