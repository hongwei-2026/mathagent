from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from mathagent import __version__
from mathagent.agent import MathAgent
from mathagent.config import get_settings
from mathagent.data.loader import load_benchmark, load_local_samples
from mathagent.eval.grader import math_equal

app = typer.Typer(add_completion=False, no_args_is_help=True, help="MathAgent CLI")
console = Console()


@app.command()
def version() -> None:
    """Print version."""
    console.print(f"mathagent {__version__}")


@app.command()
def solve(
    problem: str = typer.Argument(..., help="Math problem text"),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Solve a single math problem with tool-integrated reasoning."""
    agent = MathAgent()
    result = agent.solve(problem)
    if json_out:
        console.print_json(
            data={
                "answer": result.answer,
                "turns": result.turns,
                "tools": [
                    {"name": e.name, "arguments": e.arguments, "result": e.result}
                    for e in result.tool_events
                ],
            }
        )
        return
    console.print(Panel(problem, title="Problem", border_style="cyan"))
    for event in result.tool_events:
        console.print(f"[yellow]→ {event.name}[/yellow] {event.arguments}")
        console.print(event.result[:400])
    console.print(Panel(result.answer or result.final_message, title="Answer", border_style="green"))


@app.command("eval")
def eval_cmd(
    dataset: str = typer.Option("samples", help="samples | gsm8k | math"),
    limit: Optional[int] = typer.Option(5, help="Number of problems"),
    split: str = typer.Option("test", help="HF split"),
    out: Optional[Path] = typer.Option(None, help="Write JSONL predictions"),
) -> None:
    """Evaluate on bundled samples or HuggingFace benchmarks."""
    if dataset == "samples":
        rows = load_local_samples()
        if limit is not None:
            rows = rows[:limit]
    else:
        rows = load_benchmark(dataset, split=split, limit=limit)

    agent = MathAgent()
    correct = 0
    outputs = []
    for i, row in enumerate(rows, 1):
        problem = row["problem"]
        gold = str(row.get("answer", "")).strip()
        console.rule(f"[{i}/{len(rows)}] {row.get('id', i)}")
        result = agent.solve(problem)
        ok = math_equal(result.answer, gold) if gold else False
        correct += int(ok)
        mark = "✓" if ok else "✗"
        console.print(f"{mark} pred={result.answer!r} gold={gold!r}")
        outputs.append(
            {
                "id": row.get("id"),
                "problem": problem,
                "gold": gold,
                "pred": result.answer,
                "correct": ok,
                "turns": result.turns,
            }
        )

    acc = correct / max(len(rows), 1)
    console.print(Panel(f"{correct}/{len(rows)} = {acc:.1%}", title="Accuracy"))
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for row in outputs:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        console.print(f"Wrote {out}")


@app.command()
def doctor() -> None:
    """Show resolved settings (secrets redacted)."""
    s = get_settings()
    key = s.api_key
    redacted = (key[:4] + "…" + key[-4:]) if len(key) > 8 else ("(empty)" if not key else "****")
    console.print(
        {
            "model": s.model,
            "base_url": s.base_url,
            "api_key": redacted,
            "max_turns": s.max_turns,
            "temperature": s.temperature,
        }
    )


if __name__ == "__main__":
    app()
