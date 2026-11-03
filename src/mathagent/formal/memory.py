"""Statement curriculum memory — store verified lemmas for reuse (OpenAI SCL)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MEMORY = ROOT / "data" / "curriculum" / "lemma_bank.jsonl"


@dataclass
class LemmaRecord:
    statement: str
    proof_sketch: str
    certificate_method: str
    certificate_detail: str
    parent_problem: str
    created_at: str

    @classmethod
    def create(cls, **kwargs) -> "LemmaRecord":
        kwargs.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        return cls(**kwargs)


class LemmaBank:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_MEMORY
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, record: LemmaRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def iter(self) -> Iterator[LemmaRecord]:
        if not self.path.exists():
            return
            yield  # pragma: no cover
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield LemmaRecord(**json.loads(line))

    def related(self, query: str, limit: int = 5) -> list[LemmaRecord]:
        tokens = {t.lower() for t in query.split() if len(t) > 3}
        scored: list[tuple[int, LemmaRecord]] = []
        for rec in self.iter():
            hay = (rec.statement + " " + rec.parent_problem).lower()
            score = sum(1 for t in tokens if t in hay)
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]
