"""
Pillar 3 — Cross-project evidence ledger (CoEvo / lifelong style).

Append-only JSONL: which concepts/ops actually compressed theory or certified.
Future runs boost historically successful library names.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from mathagent.lattice.causal import leaf_outcomes_for_concept
from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.mdl import graph_dl


@dataclass
class EvidenceRecord:
    ts: str
    project_id: str
    concept_id: str
    name: str
    origin: str
    status: str
    mdl_gain: float
    conceptual_value: float
    p_empirical: float | None
    n_certified: int
    n_blocked: int
    graph_dl: float
    arena_win: bool = False
    library_calls_ok: int = 0
    tags: dict[str, Any] = field(default_factory=dict)


class EvidenceLedger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/lattice/evidence.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, rec: EvidenceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    def iter_records(self) -> Iterator[EvidenceRecord]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                yield EvidenceRecord(**{k: raw[k] for k in EvidenceRecord.__dataclass_fields__ if k in raw})

    def name_stats(self) -> dict[str, dict[str, float]]:
        """Aggregate historical success by concept/library name."""
        agg: dict[str, dict[str, float]] = {}
        for r in self.iter_records() or []:
            a = agg.setdefault(
                r.name,
                {"n": 0, "wins": 0, "sum_mdl": 0.0, "sum_p": 0.0, "p_n": 0, "cert": 0},
            )
            a["n"] += 1
            a["sum_mdl"] += r.mdl_gain
            a["cert"] += r.n_certified
            if r.arena_win or r.status == "accepted":
                a["wins"] += 1
            if r.p_empirical is not None:
                a["sum_p"] += r.p_empirical
                a["p_n"] += 1
        for a in agg.values():
            a["mean_mdl"] = a["sum_mdl"] / max(a["n"], 1)
            a["mean_p"] = a["sum_p"] / max(a["p_n"], 1)
            a["win_rate"] = a["wins"] / max(a["n"], 1)
        return agg

    def prior_boost(self, name: str) -> float:
        """[0, 0.25] additive boost to conceptual_value from history."""
        stats = self.name_stats().get(name)
        if not stats or stats["n"] < 1:
            return 0.0
        return min(0.25, 0.1 * stats["win_rate"] + 0.1 * stats["mean_p"] + 0.05 * (1 if stats["mean_mdl"] > 0 else 0))

    def commit_graph(self, graph: ResearchGraph) -> list[EvidenceRecord]:
        dl = graph_dl(graph)
        now = datetime.now(timezone.utc).isoformat()
        out: list[EvidenceRecord] = []
        for c in graph.by_kind(NodeKind.CONCEPT):
            scores = c.meta.get("scores") or {}
            stats = leaf_outcomes_for_concept(graph, c.id)
            calls = 0
            for n in graph.nodes.values():
                if n.meta.get("from_concept") == c.id and n.meta.get("library_call"):
                    calls += 1
            rec = EvidenceRecord(
                ts=now,
                project_id=graph.project_id,
                concept_id=c.id,
                name=str(c.meta.get("name") or c.id),
                origin=str(c.meta.get("origin") or ""),
                status=c.status.value,
                mdl_gain=float(scores.get("mdl_gain", 0.0)),
                conceptual_value=float(scores.get("conceptual_value", c.score)),
                p_empirical=stats["p_empirical"],
                n_certified=stats["n_certified"],
                n_blocked=stats["n_blocked"],
                graph_dl=dl,
                arena_win=bool(c.meta.get("arena_win")),
                library_calls_ok=calls,
            )
            self.append(rec)
            out.append(rec)
        return out


def apply_evidence_priors(graph: ResearchGraph, ledger: EvidenceLedger | None = None) -> int:
    """Boost conceptual_value of concepts whose names won historically."""
    ledger = ledger or EvidenceLedger()
    n = 0
    for c in graph.by_kind(NodeKind.CONCEPT):
        if c.status == NodeStatus.REJECTED:
            continue
        name = str(c.meta.get("name") or "")
        boost = ledger.prior_boost(name)
        if boost <= 0:
            continue
        scores = dict(c.meta.get("scores") or {})
        v = float(scores.get("conceptual_value", c.score))
        scores["conceptual_value"] = min(1.0, v + boost)
        scores["evidence_boost"] = boost
        c.meta["scores"] = scores
        c.score = scores["conceptual_value"]
        n += 1
    return n
