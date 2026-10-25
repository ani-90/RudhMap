"""Real agent token spend, with and without RudhMap's `get_context`.

    python eval/agent_bench.py <repo_path> "<question>" [--model sonnet] [--out eval/agent_runs]

Runs Claude Code headless (`claude -p`) twice inside `repo_path` on the same
question:

  without -- built-in Read/Grep/Glob only, no MCP servers at all
  with    -- the same, plus RudhMap's `get_context`, and told to call it first

Neither run can use a shell or edit files. Token counts are the ones Claude
Code itself reports (`usage` in `--output-format json`), so they include
everything the agent actually spent: its own system prompt on every turn
(mostly cache reads), every tool result it read, and its output. Both answers
are saved as markdown so the token numbers can be read next to whether the
answer was right -- a cheaper wrong answer isn't a saving.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RUDHMAP_SRC = Path(__file__).resolve().parent.parent / "src"
PROMPT = (
    "Answer this question about the codebase in the current directory: {question}\n"
    "Cite file:line for the key claims. Keep the answer under 250 words."
)
USE_TOOL = (
    "An MCP tool `get_context` is available. Call it first with repo_path={repo} and the "
    "question as `query`; read files yourself only if its result doesn't cover the question."
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def _run(repo: Path, question: str, model: str, with_tool: bool, mcp_config: Path) -> dict:
    cmd = [
        "claude", "-p", PROMPT.format(question=question),
        "--output-format", "json",
        "--model", model,
        "--tools", "Read,Grep,Glob",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    if with_tool:
        cmd += [
            "--mcp-config", str(mcp_config),
            "--allowedTools", "Read,Grep,Glob,mcp__rudhmap__get_context",
            "--append-system-prompt", USE_TOOL.format(repo=repo),
        ]
    else:
        cmd += ["--allowedTools", "Read,Grep,Glob"]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, encoding="utf-8", timeout=900)
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(f"claude failed ({proc.returncode}): {proc.stderr.strip()[:500]}")
    return json.loads(proc.stdout)


def _totals(result: dict) -> dict:
    usage = result.get("usage", {})
    fresh = usage.get("input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    output = usage.get("output_tokens", 0)
    return {
        "turns": result.get("num_turns", 0),
        "input_fresh": fresh,
        "cache_write": cache_write,
        "cache_read": cache_read,
        "output": output,
        "total": fresh + cache_write + cache_read + output,
        "cost_usd": result.get("total_cost_usd", 0.0),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path")
    parser.add_argument("question")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "agent_runs"))
    args = parser.parse_args()

    repo = Path(args.repo_path).resolve()
    out = Path(args.out) / _slug(args.question)
    out.mkdir(parents=True, exist_ok=True)
    mcp_config = out / "mcp.json"
    mcp_config.write_text(json.dumps({"mcpServers": {"rudhmap": {
        "command": sys.executable,
        "args": ["-m", "rudhmap.server"],
        "env": {"PYTHONPATH": str(RUDHMAP_SRC)},
    }}}, indent=2), encoding="utf-8")

    rows = {}
    for label, with_tool in (("without", False), ("with", True)):
        result = _run(repo, args.question, args.model, with_tool, mcp_config)
        rows[label] = _totals(result)
        (out / f"{label}.md").write_text(
            f"# {label} get_context: {args.question}\n\n{result.get('result', '')}\n", encoding="utf-8"
        )
        (out / f"{label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"question: {args.question}  (model: {args.model})")
    print(f"{'':<9}{'turns':>6}{'fresh in':>10}{'cache wr':>10}{'cache rd':>10}{'output':>8}{'TOTAL':>9}{'cost $':>9}")
    for label, r in rows.items():
        print(
            f"{label:<9}{r['turns']:>6}{r['input_fresh']:>10}{r['cache_write']:>10}"
            f"{r['cache_read']:>10}{r['output']:>8}{r['total']:>9}{r['cost_usd']:>9.4f}"
        )
    print(f"answers: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
