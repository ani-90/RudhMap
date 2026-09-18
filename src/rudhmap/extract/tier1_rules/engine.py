"""Tier 1 extractor: declarative regex rules over application source code.

Scans source files for SDK/client-construction and framework patterns
declared in YAML rule files under rules/*.yaml. This is breadth-over-
precision by design: a regex has no notion of scope, so it can tell you
*that* a pattern matched somewhere in a file, never *which* function or
component that match belongs to. That's why this tier produces evidence
nodes only, never edges -- building a real caller-to-callee edge requires
actually parsing the language's structure, which is Tier 2 (tree-sitter
AST)'s job, not this one's. See spec Part II, Stage 1, Tier 1.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from rudhmap.cache import ExtractionCache
from rudhmap.extract import COMMON_SKIP_DIRS, iter_files
from rudhmap.extract.schema import EdgeRecord, EvidenceRecord

TIER = 1
_EXTRACTOR_NAME = "tier1"

_RULES_DIR = Path(__file__).parent / "rules"

_SKIP_DIRS = COMMON_SKIP_DIRS

# Extension -> language tag used to key rule patterns. "javascript" covers
# both JS and TS -- SDK client-construction syntax doesn't differ between
# them, so splitting the tag would just mean writing every rule twice.
LANGUAGE_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".go": "go",
    ".java": "java",
}


@dataclass
class _CompiledPattern:
    lang: str
    regex: re.Pattern


@dataclass
class _Rule:
    id: str
    kind: str
    confidence: float
    subtype: str | None
    capture_arg: str | None
    patterns: list[_CompiledPattern]


def _compile_rule(raw: dict) -> _Rule:
    """Validate + compile a single rule at load time. A broken rule file is
    a bug in the tool's own shipped rules, not untrusted repo content, so it
    fails loudly here rather than being silently skipped like a malformed
    file encountered mid-scan."""
    rule_id = raw.get("id")
    kind = raw.get("kind")
    confidence = raw.get("confidence")
    patterns_raw = raw.get("patterns")
    if not rule_id or not kind or confidence is None or not patterns_raw:
        raise ValueError(f"tier1 rule is missing a required field: {raw!r}")

    capture_arg = raw.get("capture_arg")
    patterns: list[_CompiledPattern] = []
    for entry in patterns_raw:
        lang = entry.get("lang")
        match = entry.get("match")
        if not lang or not match:
            raise ValueError(f"rule {rule_id!r} has a pattern missing lang/match: {entry!r}")
        regex = re.compile(match)
        if capture_arg and "value" not in regex.groupindex:
            raise ValueError(
                f"rule {rule_id!r} sets capture_arg={capture_arg!r} but its {lang!r} "
                f"pattern has no (?P<value>...) group: {match!r}"
            )
        patterns.append(_CompiledPattern(lang=lang, regex=regex))

    return _Rule(
        id=rule_id,
        kind=kind,
        confidence=float(confidence),
        subtype=raw.get("subtype"),
        capture_arg=capture_arg,
        patterns=patterns,
    )


def _load_rules(rules_dir: Path) -> list[_Rule]:
    rules: list[_Rule] = []
    for rule_file in sorted(rules_dir.glob("*.yaml")):
        raw_list = yaml.safe_load(rule_file.read_text(encoding="utf-8")) or []
        for raw in raw_list:
            rules.append(_compile_rule(raw))
    return rules


def _index_by_language(rules: list[_Rule]) -> dict[str, list[tuple[_Rule, _CompiledPattern]]]:
    index: dict[str, list[tuple[_Rule, _CompiledPattern]]] = {}
    for rule in rules:
        for pattern in rule.patterns:
            index.setdefault(pattern.lang, []).append((rule, pattern))
    return index


def _strip_python_comments(text: str) -> str:
    """Naive '#'-to-end-of-line stripper. Doesn't understand string
    literals, so a '#' inside a string still gets stripped -- an accepted
    tier1 tradeoff (breadth over precision); Tier 2 handles this correctly.
    Comment characters are replaced with spaces, not removed, so every
    surviving character keeps its original offset and line-number math
    downstream stays correct."""
    out_lines = []
    for line in text.split("\n"):
        idx = line.find("#")
        if idx == -1:
            out_lines.append(line)
        else:
            out_lines.append(line[:idx] + " " * (len(line) - idx))
    return "\n".join(out_lines)


_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _blank_out(match: re.Match) -> str:
    return "".join(ch if ch == "\n" else " " for ch in match.group(0))


def _strip_c_family_comments(text: str) -> str:
    """Blanks out // and /* */ comments, preserving newlines (and therefore
    every other character's offset) so line-number math on the stripped
    text still matches the original file."""
    text = _BLOCK_COMMENT_RE.sub(_blank_out, text)
    text = _LINE_COMMENT_RE.sub(_blank_out, text)
    return text


_STRIPPERS = {
    "python": _strip_python_comments,
    "javascript": _strip_c_family_comments,
    "go": _strip_c_family_comments,
    "java": _strip_c_family_comments,
}


def _iter_source_files(repo_path: Path, languages: set[str]):
    for path in iter_files(repo_path, _SKIP_DIRS):
        lang = LANGUAGE_BY_EXT.get(path.suffix.lower())
        if lang in languages:
            yield path, lang


def _hash_rules(rules_dir: Path) -> str:
    """A cached result is only valid for the exact rule set that produced
    it -- a custom rules_dir must never reuse a cache entry written under a
    different rule set for the same file content. Hashing the rule files'
    own content (not the directory path) means this is correct even if two
    different rules_dir paths happen to hold byte-identical rules."""
    digest = hashlib.sha256()
    for rule_file in sorted(rules_dir.glob("*.yaml")):
        digest.update(rule_file.read_bytes())
    return digest.hexdigest()


def parse_tier1_rules(
    repo_path: str | Path,
    rules_dir: str | Path | None = None,
    cache: ExtractionCache | None = None,
) -> tuple[list[EvidenceRecord], list[EdgeRecord]]:
    repo_path = Path(repo_path)
    resolved_rules_dir = Path(rules_dir) if rules_dir else _RULES_DIR
    rules = _load_rules(resolved_rules_dir)
    index = _index_by_language(rules)
    extractor_name = f"{_EXTRACTOR_NAME}:{_hash_rules(resolved_rules_dir)}"

    all_nodes: list[EvidenceRecord] = []
    all_edges: list[EdgeRecord] = []  # tier 1 never produces edges -- see module docstring

    for source_file, lang in _iter_source_files(repo_path, set(index)):
        def compute(source_file=source_file, lang=lang):
            try:
                raw = source_file.read_text(encoding="utf-8")
            except Exception:
                return [], []

            stripped = _STRIPPERS[lang](raw)
            file_str = str(source_file)
            file_nodes: list[EvidenceRecord] = []

            for rule, pattern in index[lang]:
                for match in pattern.regex.finditer(stripped):
                    line = stripped.count("\n", 0, match.start()) + 1
                    attrs = {"rule_id": rule.id}

                    if rule.capture_arg:
                        value = match.group("value")
                        identity = f"{rule.id}:{value}"
                        attrs[rule.capture_arg] = value
                    else:
                        identity = f"{rule.id}:{file_str}:{line}"

                    file_nodes.append(
                        EvidenceRecord(
                            kind=rule.kind,
                            identity=identity,
                            file=file_str,
                            line=line,
                            tier=TIER,
                            confidence=rule.confidence,
                            subtype=rule.subtype,
                            attrs=attrs,
                        )
                    )

            return file_nodes, []

        if cache is not None:
            nodes, edges = cache.get_or_compute(source_file, extractor_name, compute)
        else:
            nodes, edges = compute()

        all_nodes.extend(nodes)
        all_edges.extend(edges)

    return all_nodes, all_edges
