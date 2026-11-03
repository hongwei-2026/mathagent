"""Orchestrate the three think pillars after concept-value machinery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from mathagent.lattice.curator import spawn_leaf_conjectures_from_concepts
from mathagent.lattice.graph import ResearchGraph
from mathagent.lattice.mdl import graph_dl
from mathagent.lattice.think.arena import eliminate_losers
from mathagent.lattice.think.cheap_tests import run_cheap_discriminators
from mathagent.lattice.think.evidence import EvidenceLedger, apply_evidence_priors
from mathagent.lattice.think.executable import list_callable_concepts


@dataclass
class ThinkResult:
    priors_boosted: int = 0
    arena: list[dict[str, Any]] = field(default_factory=list)
    cheap_tests: list[dict[str, Any]] = field(default_factory=list)
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
    phase='start': snapshot graph_dl, evidence priors, spawn leaves
    phase='mid': cheap discriminators then arena elimination
    phase='end': commit evidence with Δgraph_dl + final arena
    """
    emit = on_event or (lambda _m: None)
    ledger = ledger or EvidenceLedger()
    result = ThinkResult()

    if phase == "start":
        if "graph_dl_start" not in graph.meta:
            graph.meta["graph_dl_start"] = graph_dl(graph)
        result.priors_boosted = apply_evidence_priors(graph, ledger)
        if result.priors_boosted:
            emit(f"[think/evidence] adjusted {result.priors_boosted} concepts from ledger")
        result.spawned_leaves = len(spawn_leaf_conjectures_from_concepts(graph))
        result.callable_ops = len(list_callable_concepts(graph))
        emit(f"[think/exec] callable_ops={result.callable_ops} leaves+={result.spawned_leaves}")

    elif phase == "mid":
        result.cheap_tests = run_cheap_discriminators(graph, on_event=emit)
        result.arena = eliminate_losers(graph, on_event=emit)
        result.callable_ops = len(list_callable_concepts(graph))

    elif phase == "end":
        dl0 = float(graph.meta.get("graph_dl_start", graph_dl(graph)))
        result.cheap_tests = run_cheap_discriminators(graph, on_event=emit)
        result.arena = eliminate_losers(graph, on_event=emit)
        recs = ledger.commit_graph(graph, graph_dl_before=dl0)
        result.evidence_records = len(recs)
        emit(f"[think/evidence] wrote {result.evidence_records} ledger rows Δdl={dl0 - graph_dl(graph):.1f}")

    return result
