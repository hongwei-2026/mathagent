#!/usr/bin/env python
"""Download GSM8K / MATH snapshots into data/ for offline eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["gsm8k", "math", "both"], default="gsm8k")
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    from mathagent.data.loader import load_benchmark

    targets = ["gsm8k", "math"] if args.dataset == "both" else [args.dataset]
    for name in targets:
        rows = load_benchmark(name, split=args.split, limit=args.limit)
        out_dir = ROOT / "data" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{args.split}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Wrote {len(rows)} rows → {out}")


if __name__ == "__main__":
    main()
