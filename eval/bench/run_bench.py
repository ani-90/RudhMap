"""Step A/C benchmark: real Claude Code runs on hand-keyed repo questions.

    python eval/bench/run_bench.py run   --label stepA --models haiku,sonnet --arms none --reps 3
    python eval/bench/run_bench.py grade --label stepA
    python eval/bench/run_bench.py report --label stepA

`run`: for every (question, arm, model, rep) not already saved, starts a fresh
headless Claude Code session (`claude -p`) inside a clean export of the repo:

- the repo is exported from git at the pinned commit (`git archive`) into a temp
  folder outside the user's projects, with CLAUDE.md / AGENTS.md removed;
- tools are Read/Grep/Glob only (no shell, no edits, no web); arm `rudhmap` adds
  RudhMap's MCP server, arm `none` has no MCP servers at all;
- no user/project settings, no session persistence, so nothing carries over.

Each run is saved with the answer, Claude Code's own token usage, turns, and
every tool call with the size of what it returned.

`grade`: a separate Sonnet session grades each answer against the key without
being told which arm/model produced it. `report`: tables per arm x model.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
QUESTIONS = HERE / "questions.yaml"
RESULTS = ROOT / "eval" / "results" / "bench"
EXPORTS = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Temp" / "rudhmap_bench"
AGENT_FILES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules"}

PROMPT = (
    "Answer this question about the codebase in the current directory: {question}\n"
    "Cite file:line for the key claims. Keep the answer under 300 words."
)
BASE_TOOLS = "Read,Grep,Glob"

GRADER_PROMPT = """You are grading an answer to a question about a codebase against an answer key.

QUESTION:
{question}

ANSWER KEY (facts a correct answer must state; file references are for you, the answer does not need to cite them):
{facts}

ANSWER TO GRADE:
<<<
{answer}
>>>

For each fact, decide whether the answer states it (in any wording). For a fact with a MUST STATE line, judge only that line: the answer must clearly say it; the context is there to help you understand it, not extra requirements. Secondary details inside a fact (exact default values, the full list of fields, exception class names, line numbers) are not required unless the fact is only about that detail. A fact is not stated if the answer only hints at it, says it didn't check it, or gets its main point wrong.
Then list any claims in the answer that are false about the code as described by the key, and decide whether any of them is MAJOR (would mislead someone relying on the answer about the thing asked). Do not penalise extra true detail or claims the key doesn't cover unless they contradict it.

Reply with ONLY a JSON object, no markdown:
{{"facts": {{"<fact id>": true|false, ...}}, "false_claims": ["..."], "major_false_claim": true|false}}"""


# ------------------------------------------------------------------ setup

def load_questions(path: str | None = None) -> dict:
    return yaml.safe_load((Path(path) if path else QUESTIONS).read_text(encoding="utf-8"))


def export_repo(name: str, spec: dict) -> Path:
    """Fresh copy of the repo at the pinned commit, without agent instruction files."""
    dest = EXPORTS / f"{name}-{spec['commit']}"
    marker = dest / ".rudhmap_bench_export"
    if marker.exists():
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "repo.tar"
        subprocess.run(
            ["git", "-C", spec["source"], "archive", "--format=tar", "-o", str(tar_path), spec["commit"]],
            check=True,
        )
        with tarfile.open(tar_path) as tar:
            tar.extractall(dest, filter="data")
    for path in list(dest.rglob("*")):
        if path.name in AGENT_FILES and path.is_file():
            path.unlink()
    marker.write_text(spec["commit"], encoding="utf-8")
    return dest


def mcp_config_path() -> Path:
    path = EXPORTS / "rudhmap_mcp.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": {"rudhmap": {
        "command": str(ROOT / ".venv" / "Scripts" / "python.exe") if os.name == "nt" else sys.executable,
        "args": ["-m", "rudhmap.server"],
        "env": {"PYTHONPATH": str(ROOT / "src")},
    }}}), encoding="utf-8")
    return path


# ------------------------------------------------------------------ one run

def claude_cmd(prompt: str, model: str, arm: str) -> list[str]:
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--model", model,
        "--tools", BASE_TOOLS,
        "--strict-mcp-config",
        "--no-session-persistence",
        "--setting-sources", "",
    ]
    if arm == "rudhmap":
        cmd += ["--mcp-config", str(mcp_config_path()),
                "--allowedTools", BASE_TOOLS + ",mcp__rudhmap"]
    else:
        cmd += ["--allowedTools", BASE_TOOLS]
    return cmd


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content)


def parse_stream(lines: list[str]) -> dict:
    calls: dict[str, dict] = {}
    order: list[str] = []
    message_ids: list[str] = []  # one per model call; parallel tool requests share one
    result: dict = {}
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "assistant":
            message_id = event.get("message", {}).get("id")
            if message_id and message_id not in message_ids:
                message_ids.append(message_id)
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls[block["id"]] = {"tool": block["name"], "input": block.get("input", {}), "result_chars": 0,
                                          "model_call": len(message_ids)}
                    order.append(block["id"])
        elif kind == "user":
            content = event.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        call = calls.get(block.get("tool_use_id"))
                        if call is not None:
                            text = _result_text(block.get("content"))
                            call["result_chars"] = len(text)
                            call["is_error"] = bool(block.get("is_error"))
        elif kind == "result":
            result = event
    usage = result.get("usage", {})
    tokens = {
        "input": usage.get("input_tokens", 0),
        "cache_write": usage.get("cache_creation_input_tokens", 0),
        "cache_read": usage.get("cache_read_input_tokens", 0),
        "output": usage.get("output_tokens", 0),
    }
    tokens["context"] = tokens["input"] + tokens["cache_write"]
    tokens["total"] = tokens["context"] + tokens["cache_read"] + tokens["output"]
    return {
        "answer": result.get("result", ""),
        "is_error": result.get("is_error", not result),
        "subtype": result.get("subtype"),
        "turns": result.get("num_turns", 0),  # Claude Code's count; not the number of model calls
        "model_calls": len(message_ids),
        "cost_usd": result.get("total_cost_usd", 0.0),
        "duration_ms": result.get("duration_ms"),
        "tokens": tokens,
        "tool_calls": [calls[i] for i in order],
    }


def run_one(q: dict, repo_dir: Path, arm: str, model: str, rep: int, out: Path) -> dict:
    cmd = claude_cmd(PROMPT.format(question=q["question"]), model, arm)
    started = time.time()
    proc = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, encoding="utf-8", timeout=1200)
    record = parse_stream(proc.stdout.splitlines())
    record.update({
        "question_id": q["id"], "repo": q["repo"], "arm": arm, "model": model, "rep": rep,
        "wall_s": round(time.time() - started, 1), "returncode": proc.returncode,
    })
    if not record["answer"]:
        record["stderr"] = proc.stderr[-2000:]
    if record["answer"] and not record["is_error"]:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def cmd_run(args) -> int:
    data = load_questions(args.questions)
    repos = {name: export_repo(name, spec) for name, spec in data["repos"].items()}
    questions = [q for q in data["questions"] if not args.only or q["id"] in args.only.split(",")]
    jobs = []
    for q in questions:
        for arm in args.arms.split(","):
            for model in args.models.split(","):
                for rep in range(1, args.reps + 1):
                    out = RESULTS / args.label / q["id"] / f"{arm}-{model}-r{rep}.json"
                    if not out.exists():
                        jobs.append((q, arm, model, rep, out))
    print(f"{len(jobs)} runs to do ({args.workers} at a time)", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, q, repos[q["repo"]], arm, model, rep, out): (q["id"], arm, model, rep)
                   for q, arm, model, rep, out in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            key = futures[future]
            try:
                r = future.result()
                ok = bool(r["answer"]) and not r["is_error"]
                failures += not ok
                print(f"[{done}/{len(jobs)}] {key} {'ok' if ok else 'FAILED ' + r.get('subtype', '') + r.get('stderr', '')[:300]}"
                      f" turns={r['turns']} total={r['tokens']['total']} {r['wall_s']}s", flush=True)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"[{done}/{len(jobs)}] {key} FAILED {exc}", flush=True)
    print(f"done, {failures} failed (failed runs are not saved; rerun to retry)")
    return 1 if failures else 0


# ------------------------------------------------------------------ grading

def _grade_once(prompt: str, model: str) -> dict:
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", "--model", model, "--tools", "",
         "--strict-mcp-config", "--no-session-persistence", "--setting-sources", ""],
        capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=tempfile.gettempdir(),
    )
    raw = json.loads(proc.stdout)["result"].strip()
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def grade_one(q: dict, path: Path, model: str, votes: int = 3) -> dict:
    """Majority of `votes` independent grader runs, per fact and for the false-claim flag."""
    record = json.loads(path.read_text(encoding="utf-8"))
    facts = "\n".join(
        f"- {f['id']} ({'critical' if f['critical'] else 'supporting'}): "
        + (f"MUST STATE: {f['must']}  (context: {' '.join(f.get('text', '').split()) or '-'})" if f.get("must")
           else " ".join(f["text"].split()))
        + f"  [{f['where']}]"
        for f in q["facts"]
    )
    prompt = GRADER_PROMPT.format(question=q["question"], facts=facts, answer=record["answer"])
    verdicts = [_grade_once(prompt, model) for _ in range(votes)]
    hit = {f["id"]: sum(bool(v["facts"].get(f["id"], False)) for v in verdicts) * 2 > votes for f in q["facts"]}
    major = sum(bool(v.get("major_false_claim")) for v in verdicts) * 2 > votes
    critical_ok = all(hit[f["id"]] for f in q["facts"] if f["critical"])
    record["grade"] = {
        "grader": f"{model} x{votes}",
        "facts": hit,
        "fact_score": round(sum(hit.values()) / len(hit), 3),
        "critical_ok": critical_ok,
        "false_claims": [c for v in verdicts for c in v.get("false_claims", [])],
        "major_false_claim": major,
        "correct": critical_ok and not major,
        "unanimous": len({(tuple(sorted(v["facts"].items())), bool(v.get("major_false_claim"))) for v in verdicts}) == 1,
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record["grade"]


def cmd_grade(args) -> int:
    data = load_questions(args.questions)
    by_id = {q["id"]: q for q in data["questions"]}
    todo = []
    for path in sorted((RESULTS / args.label).glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if args.regrade or "grade" not in record:
            todo.append((by_id[record["question_id"]], path))
    print(f"{len(todo)} answers to grade", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(grade_one, q, path, args.grader): path for q, path in todo}
        for future in as_completed(futures):
            path = futures[future]
            try:
                g = future.result()
                print(f"{path.parent.name}/{path.stem}: correct={g['correct']} score={g['fact_score']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"{path.parent.name}/{path.stem}: grading FAILED {exc}", flush=True)
    return 1 if failures else 0


# ------------------------------------------------------------------ report

def load_records(label: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RESULTS / label).glob("*/*.json"))]


def summarize(records: list[dict]) -> dict:
    """Per (arm, model): per-question medians, then across questions."""
    groups: dict[tuple, dict[str, list[dict]]] = {}
    for r in records:
        groups.setdefault((r["arm"], r["model"]), {}).setdefault(r["question_id"], []).append(r)
    out = {}
    for key, per_q in sorted(groups.items()):
        rows = {}
        for qid, runs in sorted(per_q.items()):
            graded = [r for r in runs if "grade" in r]
            rows[qid] = {
                "runs": len(runs),
                "correct_runs": sum(r["grade"]["correct"] for r in graded),
                "correct": sum(r["grade"]["correct"] for r in graded) >= 2 if len(graded) >= 3
                else (sum(r["grade"]["correct"] for r in graded) > len(graded) / 2 if graded else None),
                "fact_score": statistics.mean(r["grade"]["fact_score"] for r in graded) if graded else None,
                "total": statistics.median(r["tokens"]["total"] for r in runs),
                "context": statistics.median(r["tokens"]["context"] for r in runs),
                "turns": statistics.median(r["turns"] for r in runs),
                "model_calls": statistics.median(r["model_calls"] for r in runs) if all("model_calls" in r for r in runs) else None,
                "tool_calls": statistics.median(len(r["tool_calls"]) for r in runs),
                "result_chars": statistics.median(sum(c["result_chars"] for c in r["tool_calls"]) for r in runs),
                "cost": sum(r["cost_usd"] for r in runs),
                "total_spread": (min(r["tokens"]["total"] for r in runs), max(r["tokens"]["total"] for r in runs)),
            }
        out[key] = {
            "questions": rows,
            "correct": sum(1 for v in rows.values() if v["correct"]),
            "graded_questions": sum(1 for v in rows.values() if v["correct"] is not None),
            "fact_score": statistics.mean(v["fact_score"] for v in rows.values() if v["fact_score"] is not None)
            if any(v["fact_score"] is not None for v in rows.values()) else None,
            "median_total": statistics.median(v["total"] for v in rows.values()),
            "median_context": statistics.median(v["context"] for v in rows.values()),
            "median_turns": statistics.median(v["turns"] for v in rows.values()),
            "median_model_calls": statistics.median(v["model_calls"] for v in rows.values())
            if all(v["model_calls"] is not None for v in rows.values()) else None,
            "sum_total": sum(r["tokens"]["total"] for runs in per_q.values() for r in runs),
            "cost": sum(v["cost"] for v in rows.values()),
        }
    return out


def cmd_report(args) -> int:
    summary = summarize(load_records(args.label))
    print(f"{'arm/model':<18}{'correct':>9}{'facts':>7}{'med total':>11}{'med new':>9}{'med turns':>10}{'med calls':>10}{'sum total':>11}{'cost $':>8}")
    for (arm, model), s in summary.items():
        fs = f"{s['fact_score']:.2f}" if s["fact_score"] is not None else "-"
        print(f"{arm + '/' + model:<18}{str(s['correct']) + '/' + str(s['graded_questions']):>9}{fs:>7}"
              f"{s['median_total']:>11.0f}{s['median_context']:>9.0f}{s['median_turns']:>10.0f}"
              f"{(s['median_model_calls'] if s['median_model_calls'] is not None else float('nan')):>10.0f}"
              f"{s['sum_total']:>11}{s['cost']:>8.2f}")
    print()
    for (arm, model), s in summary.items():
        print(f"== {arm}/{model}")
        print(f"  {'question':<10}{'correct':>9}{'facts':>7}{'total':>9}{'spread':>18}{'ctx':>8}{'turns':>6}{'calls':>6}{'read chars':>11}")
        for qid, v in s["questions"].items():
            fs = f"{v['fact_score']:.2f}" if v["fact_score"] is not None else "-"
            print(f"  {qid:<10}{str(v['correct_runs']) + '/' + str(v['runs']):>9}{fs:>7}{v['total']:>9.0f}"
                  f"{str(v['total_spread']):>18}{v['context']:>8.0f}{v['turns']:>6.0f}{v['tool_calls']:>6.0f}{v['result_chars']:>11.0f}")
    out = RESULTS / args.label / "summary.json"
    out.write_text(json.dumps({f"{a}/{m}": s for (a, m), s in summary.items()}, indent=2, default=list), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--label", required=True)
    run.add_argument("--models", default="haiku")
    run.add_argument("--arms", default="none")
    run.add_argument("--reps", type=int, default=3)
    run.add_argument("--workers", type=int, default=3)
    run.add_argument("--only", default="", help="comma-separated question ids")
    run.add_argument("--questions", default=None, help="question file (default: questions.yaml)")
    grade = sub.add_parser("grade")
    grade.add_argument("--label", required=True)
    grade.add_argument("--grader", default="sonnet")
    grade.add_argument("--workers", type=int, default=4)
    grade.add_argument("--regrade", action="store_true")
    grade.add_argument("--questions", default=None, help="question file (default: questions.yaml)")
    report = sub.add_parser("report")
    report.add_argument("--label", required=True)
    args = parser.parse_args()
    return {"run": cmd_run, "grade": cmd_grade, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
