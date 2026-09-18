"""Directories that should never be treated as part of the scanned repo's
own code/infra: dependency trees, VCS metadata, build output, and test
suites. Every extractor across every tier must skip at least these -- a
tier may extend this set with its own additional skips (e.g. Terraform's
.terraform cache, k8s's Helm charts/templates dirs), but must never define
a narrower one. A narrower copy is exactly what let a third-party package's
own bundled docker-compose.yaml inside .venv get scanned as if it were the
repo's own infrastructure.

Test directories are skipped for the same reason as vendor/build output --
not because they're worthless, but because they aren't architecture. A
slice query for a widely-shared utility (e.g. one called from twenty
different test functions) would otherwise get its 60-node budget dominated
by test scaffolding instead of the actual production-code neighborhood
being asked about -- confirmed dogfooding this project's own slicer against
its own repo (see eval/cases.md, "test file exclusion"). This intentionally
does NOT catch test files that live alongside source with only a naming
convention (`foo.test.ts`, `test_foo.py` outside a dedicated directory) --
only directory names, matching every other entry in this set.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

COMMON_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "venv",
        ".venv",
        "__pycache__",
        "dist",
        "build",
        "tests",
        "test",
        "__tests__",
        "spec",
        "specs",
    }
)


def iter_files(repo_path: Path, skip_dirs: frozenset[str]) -> Iterator[Path]:
    """Walk repo_path yielding every file not under a skip_dirs directory,
    pruning the walk itself rather than filtering after the fact.

    Path.rglob() has no way to skip a directory before descending into it --
    every extractor that used `for p in repo_path.rglob(...): if any(part in
    skip_dirs...): continue` still paid the full filesystem-enumeration cost
    of walking into .venv/node_modules/etc. before discarding what it found
    there. A real .venv with a couple of heavy packages installed can hold
    tens of thousands of files; with every extractor across every tier doing
    its own unpruned rglob() over the whole repo, that cost is paid
    repeatedly, once per extractor, and was slow enough in practice to make
    a full scan of an ordinary small repo take minutes instead of seconds.
    os.walk()'s dirnames list can be pruned in place *before* it recurses,
    which is the fix.
    """
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for filename in filenames:
            yield Path(dirpath) / filename
