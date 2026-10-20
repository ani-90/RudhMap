"""Repo-relative naming for anything that leaves the process (MCP results,
rendered diagrams). Extractors emit paths and node ids rooted at whatever
`repo_path` they were given; stripping that root and normalizing to forward
slashes makes output identical across checkout locations and OSes (spec
invariant 4) -- the same class of leak the slicer's basename-only indexing
fixed.
"""
from __future__ import annotations

import os
from pathlib import Path


class Relativizer:
    def __init__(self, root: Path):
        self._prefix = str(root) + os.sep

    def __call__(self, value: str) -> str:
        if value.startswith(self._prefix):
            value = value[len(self._prefix) :]
        return value.replace("\\", "/")
