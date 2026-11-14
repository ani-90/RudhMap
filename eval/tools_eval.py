"""Step B evaluation: the four tools, measured without an LLM.

    python eval/tools_eval.py --label <name>     # writes eval/results/tools/<name>.json

Repos are the clean git exports the benchmark uses (eval/bench/run_bench.py
export_repo), plus Textualize/rich for size and latency (no rich questions are
used here; its held-out questions stay untouched). Checks, matching the pass
criteria in docs/plan.md step B:

1. size sweep: every tool on a deterministic sample of symbols in each repo;
   max tokens per tool vs budget, and every over-budget or cut output listed;
2. find_symbol top-3 accuracy on eval/ground_truth/step_b_tools.yaml;
3. coverage: for each tuning question, do the planned 1-2 calls contain every
   required string;
4. determinism: each sweep call twice, and against a freshly built index;
5. latency on rich: cold (empty cache), warm call, after editing one file.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE / "bench"))

from run_bench import export_repo, load_questions  # noqa: E402

from rudhmap.tools import views  # noqa: E402
from rudhmap.tools.index import RepoIndex  # noqa: E402

BUDGETS = {"show": views.SHOW_BUDGET, "repo_map": views.MAP_BUDGET, "find_symbol": views.FIND_BUDGET + views.SHOW_BUDGET,
           "trace": views.TRACE_BUDGET}
DATA = HERE / "ground_truth" / "step_b_tools.yaml"
RICH = {"source": "D:/ani_codes/AGENTICAI/rich", "commit": "3a109ccd"}
SAMPLE_PER_REPO = 50


def call(index, tool: str, args: list) -> str:
    if tool == "show":
        return views.show(index, *args)
    if tool == "trace":
        return views.trace(index, *args)
    if tool == "find_symbol":
        return views.find_symbol(index, *args)
    if tool == "repo_map":
        return views.repo_map(index, *args)
    raise ValueError(tool)


def sweep_calls(index, seed: int) -> list[tuple[str, list]]:
    rng = random.Random(seed)
    symbols = sorted((s for s in index.symbols.values() if s.kind in ("function", "class")), key=lambda s: s.id)
    sample = rng.sample(symbols, min(SAMPLE_PER_REPO, len(symbols)))
    calls: list[tuple[str, list]] = [("repo_map", [None])]
    folders = sorted({f.rsplit("/", 1)[0] for f in index.files if "/" in f})
    calls += [("repo_map", [f]) for f in rng.sample(folders, min(5, len(folders)))]
    modules = sorted(s.id for s in index.symbols.values() if s.kind == "module")
    calls += [("show", [m, None]) for m in rng.sample(modules, min(10, len(modules)))]
    for s in sample:
        calls.append(("show", [s.id, None]))
        calls.append(("show", [s.id, "outline"]))
        calls.append(("trace", [s.id, None, "down", 3]))
        calls.append(("trace", [s.id, None, "up", 3]))
        calls.append(("find_symbol", [" ".join(views._split_words(s.name)) or s.name]))
    for a, b in zip(sample[::2], sample[1::2]):
        calls.append(("trace", [a.id, b.id, "down", 3]))
    return calls


def size_sweep(name: str, index) -> dict:
    calls = sweep_calls(index, seed=len(name))
    per_tool: dict[str, list[int]] = {}
    over, cut = [], 0
    outputs = []
    for tool, args in calls:
        out = call(index, tool, args)
        outputs.append(out)
        size = views.tokens(out)
        per_tool.setdefault(tool, []).append(size)
        if size > BUDGETS[tool]:
            over.append({"tool": tool, "args": args, "tokens": size})
        if " cut" in out or "not shown" in out or "+" in out and "more" in out:
            cut += 1
    return {
        "calls": len(calls),
        "per_tool": {t: {"n": len(v), "max": max(v), "median": statistics.median(v), "budget": BUDGETS[t]}
                     for t, v in per_tool.items()},
        "over_budget": over,
        "outputs_with_a_stated_cut": cut,
        "_outputs": outputs,
        "_calls": calls,
    }


def find_accuracy(indexes: dict) -> dict:
    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    rows = []
    for item in data["find"]:
        index = indexes[item["repo"]]
        results = [s.id for _, s in views.search(index, item["query"], limit=10)]
        rank = next((i + 1 for i, sid in enumerate(results) if sid in item["expect"]), None)
        rows.append({"repo": item["repo"], "query": item["query"], "rank": rank, "top3": results[:3]})
    hits = sum(1 for r in rows if r["rank"] is not None and r["rank"] <= 3)
    return {"top3": hits, "total": len(rows), "accuracy": round(hits / len(rows), 3),
            "misses": [r for r in rows if r["rank"] is None or r["rank"] > 3], "rows": rows}


def coverage(indexes: dict) -> dict:
    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in load_questions()["questions"]}
    rows = []
    for qid, plan in data["coverage"].items():
        index = indexes[questions[qid]["repo"]]
        outputs = []
        for tool, *args in plan["calls"]:
            if tool == "show":
                args = [args[0], None]
            elif tool == "trace":
                args = [args[0], None, "down", 3]
            outputs.append(call(index, tool, args))
        text = "\n".join(outputs)
        missing = [r for r in plan["require"] if str(r) not in text]
        rows.append({"question": qid, "calls": plan["calls"], "covered": not missing, "missing": missing,
                     "tokens": views.tokens(text)})
    return {"covered": sum(r["covered"] for r in rows), "total": len(rows), "rows": rows}


def determinism(name: str, root: Path, sweep: dict) -> dict:
    index = RepoIndex.get(root)
    again = [call(index, t, a) for t, a in sweep["_calls"]]
    fresh = RepoIndex(root)
    rebuilt = [call(fresh, t, a) for t, a in sweep["_calls"]]
    same_twice = sum(a == b for a, b in zip(sweep["_outputs"], again))
    same_fresh = sum(a == b for a, b in zip(sweep["_outputs"], rebuilt))
    return {"calls": len(again), "identical_twice": same_twice, "identical_fresh_index": same_fresh}


def latency(rich_export: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "rich"
        shutil.copytree(rich_export, work)
        os.environ["RUDHMAP_CACHE_DIR"] = str(Path(tmp) / "cache")  # empty cache: a true cold start
        RepoIndex._instances.clear()
        t0 = time.perf_counter()
        index = RepoIndex.get(work)
        first = views.show(index, "Console.print")
        cold = time.perf_counter() - t0
        warm_times = []
        for symbol in ("Console.print", "Live.refresh", "Progress.advance", "Text.wrap", "Segment.split_and_crop_lines"):
            time.sleep(0.6)  # past the freshness window, so each call also runs the changed-file check
            t1 = time.perf_counter()
            views.show(RepoIndex.get(work), symbol)
            warm_times.append(time.perf_counter() - t1)
        target = work / "rich" / "live.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n\ndef _added_for_latency_check():\n    return 1\n",
                          encoding="utf-8")
        time.sleep(0.6)
        t2 = time.perf_counter()
        index = RepoIndex.get(work)
        after = views.show(index, "_added_for_latency_check")
        edited = time.perf_counter() - t2
        os.environ.pop("RUDHMAP_CACHE_DIR", None)
        RepoIndex._instances.clear()
        return {
            "files": len(index.files), "symbols": len(index.symbols),
            "cold_s": round(cold, 2), "warm_s_max": round(max(warm_times), 3),
            "warm_s_median": round(statistics.median(warm_times), 3), "after_edit_s": round(edited, 2),
            "edit_visible": "_added_for_latency_check" in after and "No symbol" not in after,
            "cold_output_ok": "def print" in first,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    repos = {name: export_repo(name, spec) for name, spec in load_questions()["repos"].items()}
    repos["rich"] = export_repo("rich", RICH)
    indexes = {name: RepoIndex.get(root) for name, root in repos.items()}

    report: dict = {"repos": {n: {"files": len(i.files), "symbols": len(i.symbols),
                                  "build_s": round(i.build_seconds, 2)} for n, i in indexes.items()}}
    sweeps = {name: size_sweep(name, index) for name, index in indexes.items()}
    report["size"] = {n: {k: v for k, v in s.items() if not k.startswith("_")} for n, s in sweeps.items()}
    report["find"] = find_accuracy(indexes)
    report["coverage"] = coverage(indexes)
    report["determinism"] = {n: determinism(n, repos[n], sweeps[n]) for n in repos}
    report["latency_rich"] = latency(repos["rich"])

    out = HERE / "results" / "tools" / f"{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("repos:", json.dumps(report["repos"]))
    total_calls = sum(s["calls"] for s in report["size"].values())
    total_over = sum(len(s["over_budget"]) for s in report["size"].values())
    print(f"size: {total_calls} calls, {total_over} over budget")
    for name, s in report["size"].items():
        print(f"  {name}: " + ", ".join(f"{t} max {v['max']}/{v['budget']} (median {v['median']})"
                                        for t, v in sorted(s["per_tool"].items())))
        for o in s["over_budget"][:5]:
            print(f"    OVER {o['tool']} {o['args']} {o['tokens']}")
    f = report["find"]
    print(f"find_symbol top-3: {f['top3']}/{f['total']} ({f['accuracy']:.0%})")
    for m in f["misses"]:
        print(f"  MISS [{m['repo']}] {m['query']!r}: rank {m['rank']}, top3 {m['top3']}")
    c = report["coverage"]
    print(f"coverage: {c['covered']}/{c['total']}")
    for r in c["rows"]:
        print(f"  {r['question']:<8} {'ok' if r['covered'] else 'MISSING ' + str(r['missing'])}  ({r['tokens']} tokens)")
    print("determinism:", json.dumps(report["determinism"]))
    print("latency (rich):", json.dumps(report["latency_rich"]))
    print(f"full results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
