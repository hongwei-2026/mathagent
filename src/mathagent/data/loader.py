from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
SAMPLES_PATH = ROOT / "data" / "samples" / "problems.jsonl"


def load_local_samples(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or SAMPLES_PATH
    rows: list[dict[str, Any]] = []
    with target.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_benchmark(
    name: str,
    split: str = "test",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Load GSM8K or MATH via HuggingFace `datasets`.

    name: 'gsm8k' | 'math' | 'hendrycks_math'
    """
    from datasets import load_dataset

    key = name.lower()
    if key == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split=split)
        rows = [
            {
                "id": f"gsm8k-{i}",
                "problem": row["question"],
                "answer": row["answer"].split("####")[-1].strip(),
                "source": "gsm8k",
            }
            for i, row in enumerate(ds)
        ]
    elif key in {"math", "hendrycks_math"}:
        # Official MATH often needs gated access; fall back to competition_math mirror naming
        try:
            ds = load_dataset("hendrycks/competition_math", split=split)
        except Exception:
            ds = load_dataset("lighteval/MATH", split=split)
        rows = [
            {
                "id": f"math-{i}",
                "problem": row["problem"],
                "answer": row.get("solution", row.get("answer", "")),
                "level": row.get("level"),
                "type": row.get("type"),
                "source": "math",
            }
            for i, row in enumerate(ds)
        ]
        # Prefer \boxed{} extraction for MATH solutions when present
        from mathagent.eval.grader import extract_final_answer

        for row in rows:
            boxed = extract_final_answer(str(row["answer"]))
            if boxed:
                row["answer"] = boxed
    else:
        raise ValueError(f"Unknown benchmark: {name}")

    if limit is not None:
        rows = rows[:limit]
    return rows
