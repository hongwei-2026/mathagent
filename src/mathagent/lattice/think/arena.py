"""
Pillar 2 — Hypothesis arena (Lakatos / IBE inspired).

Multiple Concepts that claim the same gaps compete. Losers are REJECTED
using leaf certify rate + MDL gain — not LLM eloquence.
"""

from __future__ import annotations

from typing import Any

from mathagent.lattice.causal import leaf_outcomes_for_concept
from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph


def _gap_key(concept: Node) -> str:
    closes = concept.meta.get("closes_gap_ids") or []
    if closes:
        return "|".join(sorted(str(x) for x in closes))
    # Fall back: concepts with no closes compete in a global bucket only if same name prefix
    return f"__open__:{concept.meta.get('name', concept.id)[:20]}"


def fitness(concept: Node, graph: ResearchGraph) -> float:
    """Higher is better. Uses empirical leaves + mdl_gain + conceptual_value."""
    scores = concept.meta.get("scores") or {}
    v = float(scores.get("conceptual_value", concept.score))
    mdl = float(scores.get("mdl_gain", 0.0))
    mdl_term = max(0.0, min(1.0, (mdl + 40.0) / 80.0))
    stats = leaf_outcomes_for_concept(graph, concept.id)
    p = stats["p_empirical"]
    emp = 0.35 if p is None else float(p)  # neutral prior if no leaves yet
    n = stats["n_certified"] + stats["n_blocked"]
    return 0.5 * emp + 0.3 * mdl_term + 0.15 * v + 0.05 * min(n, 5) / 5.0


def arenas(graph: ResearchGraph) -> dict[str, list[Node]]:
    groups: dict[str, list[Node]] = {}
    for c in graph.by_kind(NodeKind.CONCEPT):
        if c.status == NodeStatus.REJECTED:
            continue
        groups.setdefault(_gap_key(c), []).append(c)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def eliminate_losers(
    graph: ResearchGraph,
    *,
    min_decided_leaves: int = 1,
    on_event: Any = None,
) -> list[dict[str, Any]]:
    """
    In each competing arena, keep the best fitness concept; REJECTED the rest
    when at least one has decided leaves (or always by MDL/V if no leaves yet
    and all are past HUMAN_REVIEW).
    """
    emit = on_event or (lambda _m: None)
    reports: list[dict[str, Any]] = []
    for key, members in arenas(graph).items():
        scored = []
        for c in members:
            if c.status == NodeStatus.HUMAN_REVIEW:
                continue  # don't kill until gated
            stats = leaf_outcomes_for_concept(graph, c.id)
            decided = stats["n_certified"] + stats["n_blocked"]
            scored.append((fitness(c, graph), decided, c))
        if len(scored) < 2:
            continue
        # Need evidence: at least one concept has decided leaves, or all ACCEPTED/OPEN
        if not any(d >= min_decided_leaves for _, d, _ in scored):
            if not all(c.status in {NodeStatus.ACCEPTED, NodeStatus.OPEN} for _, _, c in scored):
                continue
        scored.sort(key=lambda t: (-t[0], -t[1]))
        winner = scored[0][2]
        killed = []
        for fit, _d, c in scored[1:]:
            if c.id == winner.id:
                continue
            c.status = NodeStatus.REJECTED
            gate = dict(c.meta.get("human_gate") or {})
            gate["decision"] = "arena_reject"
            gate["notes"] = f"lost arena {key} to {winner.id} (fitness={fit:.3f})"
            c.meta["human_gate"] = gate
            c.meta["arena_loss"] = {"winner": winner.id, "arena": key, "fitness": fit}
            killed.append(c.id)
            emit(f"[think/arena] REJECTED {c.id} (lost to {winner.id})")
        winner.meta["arena_win"] = {"arena": key, "killed": killed}
        if winner.status == NodeStatus.OPEN:
            winner.status = NodeStatus.ACCEPTED
        reports.append(
            {
                "arena": key,
                "winner": winner.id,
                "killed": killed,
                "fitness": scored[0][0],
            }
        )
    return reports
