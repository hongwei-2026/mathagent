#!/usr/bin/env python
"""Run a short formal-pipeline demo against DeepSeek (requires .env)."""

from __future__ import annotations

import json
from pathlib import Path

from mathagent.config import reload_settings
from mathagent.formal.pipeline import FormalPipeline

PROBLEM = (
    "Prove that for all real x,y > 0, (x+y)/2 >= sqrt(xy), with equality iff x = y. "
    "Decompose into algebraic lemmas; certify what you can with SymPy identities."
)


def main() -> None:
    settings = reload_settings()
    print("model=", settings.model, "formal=", settings.resolved_formal_model)
    pipe = FormalPipeline(use_curriculum=True, on_event=print)
    result = pipe.run(PROBLEM)
    out = Path("outputs/formal_amgm.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "verdict": result.verdict,
        "certified": f"{result.proved_count}/{result.total_subgoals}",
        "insight": result.plan.get("key_insight"),
        "gaps": result.gaps,
        "lean_theorem_sketch": result.plan.get("lean_theorem_sketch"),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=== SUMMARY ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
