"""Engine evaluation suite: how complete and correct is RudhMap's code graph?

    python eval/engine_eval.py --label before
    python eval/engine_eval.py --label after

Runs five checks and writes `eval/results/engine/<label>.json` plus a
markdown summary to stdout:

  1. Ground truth (Knowledge-News-App @ pinned commit): every connection
     between the repo's own definitions, hand-labelled in
     eval/ground_truth/knowledge_news_app_calls.yaml. Reports recall and
     precision per connection kind, at call-site level (each line counts),
     and lists every miss and every extra edge with its source line so each
     one can be root-caused.
  2. Unresolved-call audit: calls the engine dropped whose last name matches
     a definition in the repo, bucketed by likely cause. Runs on the test
     repo and on RudhMap's own src/ (no ground truth there, so this is the
     only completeness signal for it).
  3. File discovery: scanning RudhMap's own repo root must not pick up
     nested worktrees / tool folders (.claude/), i.e. it must give the same
     graph as scanning src/ alone.
  4. Determinism: two builds of the same tree give byte-identical edges.
  5. Speed: cold (no cache) and warm builds of the test repo.

The test repo is exported fresh from git at the pinned commit for every run
(`git archive`), so local junk files and stale caches never affect results.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rudhmap.paths import Relativizer  # noqa: E402
from rudhmap.pipeline import build_assembly  # noqa: E402

GT_FILE = ROOT / "eval" / "ground_truth" / "knowledge_news_app_calls.yaml"
RESULTS_DIR = ROOT / "eval" / "results" / "engine"
KINDS = ("call", "reference", "param_reference", "inherits")


def export_repo(repo: Path, commit: str, dest: Path) -> Path:
    data = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", commit],
        check=True, capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest)
    return dest


def edge_kind(evidence) -> str | None:
    """Map a graph edge to a ground-truth kind; None = not a code connection
    (imports, infra relations)."""
    attrs = evidence.attrs
    if attrs.get("kind") == "import":
        return None
    relation = attrs.get("relation")
    if relation is None:
        return "call"
    if relation == "references":
        return "param_reference" if attrs.get("via") == "param_default" else "reference"
    if relation == "inherits":
        return "inherits"
    return None


def node_name(node_id: str, rel: Relativizer, files: set[str]) -> str:
    rel_id = rel(node_id)
    # A module node's id is its file path; ground truth spells it file:<module>.
    return f"{rel_id}:<module>" if node_id in files else rel_id


def graph_sites(assembly, root: Path) -> set[tuple[str, str, str, int]]:
    rel = Relativizer(root)
    graph = assembly.graph
    files = {ev.file for _, d in graph.nodes(data=True) for ev in d["evidence"]}
    sites = set()
    for u, v, data in graph.edges(data=True):
        ev = data["evidence"]
        kind = edge_kind(ev)
        if kind is None or ev.tier != 2:
            continue
        sites.add((node_name(u, rel, files), node_name(v, rel, files), kind, ev.line))
    return sites


def line_text(root: Path, rel_file: str, line: int) -> str:
    try:
        return (root / rel_file).read_text(encoding="utf-8").splitlines()[line - 1].strip()[:100]
    except Exception:
        return "?"


def ground_truth_check(assembly, root: Path) -> dict:
    gt = yaml.safe_load(GT_FILE.read_text(encoding="utf-8"))
    expected: dict[tuple, dict] = {}
    for e in gt["edges"]:
        for line in e["lines"]:
            expected[(e["src"], e["dst"], e["kind"], line)] = e
    found = graph_sites(assembly, root)
    in_scope = {s for s in found if s[0].endswith(".py") or ".py:" in s[0]}

    per_kind = {}
    for kind in KINDS:
        exp = {k for k in expected if k[2] == kind}
        exp_easy = {k for k in exp if not expected[k].get("hard")}
        got = {s for s in in_scope if s[2] == kind}
        tp = exp & got
        per_kind[kind] = {
            "expected": len(exp),
            "found": len(tp),
            "recall": round(len(tp) / len(exp), 3) if exp else None,
            "recall_excl_hard": round(len(exp_easy & got) / len(exp_easy), 3) if exp_easy else None,
            "extra": len(got - set(expected)),
        }
    all_exp = set(expected)
    tp = all_exp & in_scope
    extra = sorted(in_scope - all_exp)
    misses = sorted(all_exp - in_scope)
    return {
        "commit": gt["commit"],
        "sites_expected": len(all_exp),
        "sites_found": len(tp),
        "recall": round(len(tp) / len(all_exp), 3),
        "precision": round(len(tp) / len(in_scope), 3) if in_scope else None,
        "per_kind": per_kind,
        "misses": [
            {"src": s, "dst": d, "kind": k, "line": ln, "hard": bool(expected[(s, d, k, ln)].get("hard")),
             "code": line_text(root, s.split(":")[0], ln)}
            for s, d, k, ln in misses
        ],
        "extra": [
            {"src": s, "dst": d, "kind": k, "line": ln, "code": line_text(root, s.split(":")[0], ln)}
            for s, d, k, ln in extra
        ],
    }


def unresolved_audit(assembly, root: Path) -> dict:
    """Dropped call edges whose last name matches a definition in the repo,
    bucketed by likely cause. A heuristic, for repos without ground truth."""
    graph = assembly.graph
    rel = Relativizer(root)
    defs_by_last = defaultdict(list)
    for n, data in graph.nodes(data=True):
        for ev in data["evidence"]:
            qual = ev.attrs.get("qualname")
            if ev.tier == 2 and qual:
                defs_by_last[qual.split(".")[-1]].append(n)

    buckets: Counter = Counter()
    examples = defaultdict(list)
    for e in assembly.dropped_edges:
        if e.tier != 2 or e.attrs.get("kind") == "import" or e.attrs.get("relation"):
            continue
        chain = e.attrs.get("callee_chain") or []
        if not chain or chain[-1] not in defs_by_last:
            continue
        if not graph.has_node(e.src):
            cause = "caller_is_module_level"
        elif chain[0] in ("self", "this"):
            cause = "self_attribute_or_inherited"
        elif len(chain) == 1 and e.attrs.get("likely_import_alias"):
            cause = "imported_name"
        elif len(chain) == 1:
            nested = any(d.startswith(e.src + ".") or d.rsplit(".", 1)[0] in e.src for d in defs_by_last[chain[0]])
            cause = "nested_or_enclosing_scope" if nested else "bare_name_other"
        elif e.attrs.get("likely_import_alias"):
            cause = "through_import_unresolved (often an external library)"
        else:
            cause = "method_on_variable"
        buckets[cause] += 1
        if len(examples[cause]) < 6:
            examples[cause].append(f"{rel(e.file)}:{e.line}  {'.'.join(chain)}")
    return {"total": sum(buckets.values()), "by_cause": dict(buckets.most_common()), "examples": dict(examples)}


def fingerprint(assembly, root: Path) -> str:
    rel = Relativizer(root)
    items = sorted(
        f"{rel(u)}|{rel(v)}|{d['evidence'].line}|{edge_kind(d['evidence'])}" for u, v, d in assembly.graph.edges(data=True)
    ) + sorted(rel(n) for n in assembly.graph.nodes)
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:16]


def discovery_check() -> dict:
    whole = build_assembly(str(ROOT), verbose=False).result
    src_only = build_assembly(str(ROOT / "src"), verbose=False).result
    stray = [n for n in whole.graph.nodes if ".claude" in Path(n).parts or "worktrees" in Path(n).parts]
    return {
        "repo_root_nodes": whole.graph.number_of_nodes(),
        "src_only_nodes": src_only.graph.number_of_nodes(),
        "nodes_from_tool_folders": len(stray),
        "repo_root_edges": whole.graph.number_of_edges(),
        "src_only_edges": src_only.graph.number_of_edges(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--kna", default=str(ROOT.parent / "Knowledge-News-App"))
    args = ap.parse_args()

    gt_commit = yaml.safe_load(GT_FILE.read_text(encoding="utf-8"))["commit"]
    with tempfile.TemporaryDirectory(prefix="rudhmap-eval-") as tmp:
        kna = export_repo(Path(args.kna), gt_commit, Path(tmp) / "kna")

        t0 = time.perf_counter()
        cold = build_assembly(str(kna), verbose=False).result
        t_cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        warm = build_assembly(str(kna), verbose=False).result
        t_warm = time.perf_counter() - t0

        results = {
            "label": args.label,
            "git_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                       capture_output=True, text=True).stdout.strip(),
            "ground_truth": ground_truth_check(warm, kna),
            "unresolved_test_repo": unresolved_audit(warm, kna),
            "determinism": {"identical": fingerprint(cold, kna) == fingerprint(warm, kna)},
            "speed_s": {"test_repo_cold": round(t_cold, 2), "test_repo_warm": round(t_warm, 2)},
            "graph_test_repo": {"nodes": warm.graph.number_of_nodes(), "edges": warm.graph.number_of_edges()},
        }

    src_assembly = build_assembly(str(ROOT / "src"), verbose=False).result
    results["unresolved_rudhmap_src"] = unresolved_audit(src_assembly, ROOT / "src")
    results["graph_rudhmap_src"] = {"nodes": src_assembly.graph.number_of_nodes(),
                                    "edges": src_assembly.graph.number_of_edges()}
    results["discovery"] = discovery_check()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{args.label}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print_summary(results)
    print(f"\nfull results: {out.relative_to(ROOT)}")
    return 0


def print_summary(r: dict) -> None:
    gt = r["ground_truth"]
    print(f"## Engine eval: {r['label']} (RudhMap {r['git_head']}, test repo @ {gt['commit']})\n")
    print(f"Ground truth: {gt['sites_found']}/{gt['sites_expected']} sites found, "
          f"recall {gt['recall']}, precision {gt['precision']}\n")
    print("| kind | expected | found | recall | recall excl. hard | extra |")
    print("|---|---|---|---|---|---|")
    for kind, k in gt["per_kind"].items():
        print(f"| {kind} | {k['expected']} | {k['found']} | {k['recall']} | {k['recall_excl_hard']} | {k['extra']} |")
    print(f"\nMisses ({len(gt['misses'])}):")
    for m in gt["misses"]:
        print(f"  - [{m['kind']}{', hard' if m['hard'] else ''}] {m['src']} -> {m['dst']} @{m['line']}  `{m['code']}`")
    print(f"\nExtra edges not in ground truth ({len(gt['extra'])}):")
    for x in gt["extra"]:
        print(f"  - [{x['kind']}] {x['src']} -> {x['dst']} @{x['line']}  `{x['code']}`")
    for key in ("unresolved_test_repo", "unresolved_rudhmap_src"):
        u = r[key]
        print(f"\n{key}: {u['total']} unconnected calls naming a repo definition: {u['by_cause']}")
    d = r["discovery"]
    print(f"\nDiscovery: repo root {d['repo_root_nodes']} nodes / {d['repo_root_edges']} edges vs src only "
          f"{d['src_only_nodes']} / {d['src_only_edges']}; nodes from tool folders: {d['nodes_from_tool_folders']}")
    print(f"Determinism: identical = {r['determinism']['identical']}")
    print(f"Speed: cold {r['speed_s']['test_repo_cold']}s, warm {r['speed_s']['test_repo_warm']}s "
          f"(test repo graph: {r['graph_test_repo']})")


if __name__ == "__main__":
    raise SystemExit(main())
