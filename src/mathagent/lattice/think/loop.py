"""Orchestrate the three think pillars after concept-value machinery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from mathagent.lattice.curator import spawn_leaf_conjectures_from_concepts
from mathagent.lattice.graph import ResearchGraph
from mathagent.lattice.think.arena import eliminate_losers
from mathagent.lattice.think.evidence import EvidenceLedger, apply_evidence_priors
from mathagent.lattice.think.executable import list_callable_concepts


@dataclass
class ThinkResult:
    priors_boosted: int = 0
    arena: list[dict[str, Any]] = field(default_factory=list)
    evidence_records: int = 0
    callable_ops: int = 0
    spawned_leaves: int = 0


def run_think_cycle(
    graph: ResearchGraph,
    *,
    phase: str = "mid",
    ledger: EvidenceLedger | None = None,
    on_event: Callable[[str], None] | None = None,
) -> ThinkResult:
    """
    phase='start': apply evidence priors, spawn leaves for callable concepts
    phase='mid': arena elimination after some wake outcomes
    phase='end': commit evidence ledger
    """
    emit = on_event or (lambda _m: None)
    ledger = ledger or EvidenceLedger()
    result = ThinkResult()

    if phase == "start":
        result.priors_boosted = apply_evidence_priors(graph, ledger)
        if result.priors_boosted:
            emit(f"[think/evidence] boosted {result.priors_boosted} concepts from ledger")
        result.spawned_leaves = len(spawn_leaf_conjectures_from_concepts(graph))
        result.callable_ops = len(list_callable_concepts(graph))
        emit(f"[think/exec] callable_ops={result.callable_ops} leaves+={result.spawned_leaves}")

    elif phase == "mid":
        result.arena = eliminate_losers(graph, on_event=emit)
        result.callable_ops = len(list_callable_concepts(graph))

    elif phase == "end":
        recs = ledger.commit_graph(graph)
        result.evidence_records = len(recs)
        result.arena = eliminate_losers(graph, on_event=emit)
        emit(f"[think/evidence] wrote {result.evidence_records} ledger rows")

    return result
