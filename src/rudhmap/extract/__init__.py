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

Tool folders (`.claude`) are skipped too: Claude Code keeps git worktrees
under `.claude/worktrees/`, which are full copies of the repo. Scanning one
duplicated every node, and the duplicates made every Python import
ambiguous, so cross-file resolution silently dropped to zero.

When the scanned path is inside a git work tree, the file list comes from
git itself (tracked + untracked-but-not-ignored), so anything the repo's own
`.gitignore` excludes is never read either. Outside git, the pruned
os.walk() below is the fallback.
"""
from __future__ import annotations

import os
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# One build runs every extractor over the same tree; each used to ask git for
# the file list again (~60ms per call on Windows, 7 calls per build). Inside
# `shared_file_listing()` the first answer is reused for the rest of the build.
_listing = threading.local()


@contextmanager
def shared_file_listing():
    previous = getattr(_listing, "cache", None)
    _listing.cache = {}
    try:
        yield
    finally:
        _listing.cache = previous

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
        ".claude",
    }
)


def _git_listed_files(repo_path: Path) -> list[Path] | None:
    """Files git considers part of the work tree under repo_path, or None if
    repo_path isn't in a git work tree (or git isn't available). Nested
    repositories and worktrees show up as a single `dir/` entry, which is
    skipped, so their contents are never listed."""
    cache = getattr(_listing, "cache", None)
    key = str(repo_path)
    if cache is not None and key in cache:
        return cache[key]
    files = _run_git_ls_files(repo_path)
    if cache is not None:
        cache[key] = files
    return files


def _run_git_ls_files(repo_path: Path) -> list[Path] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    files = []
    for rel in proc.stdout.decode("utf-8", errors="replace").split("\0"):
        if not rel or rel.endswith("/"):
            continue
        files.append(Path(rel))
    return files


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
    repo_path = Path(repo_path)
    listed = _git_listed_files(repo_path)
    if listed is not None:
        for rel in sorted(listed):
            if any(part in skip_dirs for part in rel.parts[:-1]):
                continue
            path = repo_path / rel
            if path.is_file():  # tracked but deleted on disk -> skip
                yield path
        return

    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for filename in filenames:
            yield Path(dirpath) / filename
