"""Causalized surprise: do(concept) → leaf certify distribution vs prior belief."""

from __future__ import annotations

from typing import Any

from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.value import conceptual_value, surprise_score


def leaf_outcomes_for_concept(graph: ResearchGraph, concept_id: str) -> dict[str, Any]:
    leaves = [
        n
        for n in graph.nodes.values()
        if n.kind == NodeKind.CONJECTURE and n.meta.get("from_concept") == concept_id
    ]
    certified = [n for n in leaves if n.status == NodeStatus.CERTIFIED]
    blocked = [n for n in leaves if n.status in {NodeStatus.BLOCKED, NodeStatus.REFUTED}]
    open_ = [n for n in leaves if n.status == NodeStatus.OPEN]
    decided = len(certified) + len(blocked)
    p_emp = (len(certified) / decided) if decided else None
    return {
        "n_leaves": len(leaves),
        "n_certified": len(certified),
        "n_blocked": len(blocked),
        "n_open": len(open_),
        "p_empirical": p_emp,
        "leaf_ids": [n.id for n in leaves],
    }


def apply_causal_surprise(graph: ResearchGraph) -> list[dict[str, Any]]:
    """
    Intervention view: treating Concept as do(C), update surprise from empirical
    leaf success rate vs LLM p_before (and blend with self-reported p_after).
    """
    reports: list[dict[str, Any]] = []
    for c in graph.by_kind(NodeKind.CONCEPT):
        stats = leaf_outcomes_for_concept(graph, c.id)
        p_emp = stats["p_empirical"]
        if p_emp is None:
            continue
        belief = dict(c.meta.get("belief") or {})
        p0 = float(belief.get("p_before", 0.3))
        p_llm = float(belief.get("p_after", p_emp))
        # Causal posterior: empirical dominates; shrink toward LLM when few samples
        n = stats["n_certified"] + stats["n_blocked"]
        w = n / (n + 2.0)
        p_post = w * p_emp + (1.0 - w) * p_llm
        belief["p_empirical"] = p_emp
        belief["p_posterior"] = p_post
        belief["intervention"] = "do(concept)"
        c.meta["belief"] = belief
        c.meta["do_intervention"] = {
            "applied": True,
            "stats": stats,
        }

        scores = dict(c.meta.get("scores") or {})
        causal_s = surprise_score(p0, p_post)
        llm_s = float(scores.get("surprise", surprise_score(p0, p_llm)))
        # Prefer causal signal
        scores["surprise_llm"] = llm_s
        scores["surprise"] = 0.7 * causal_s + 0.3 * llm_s
        scores["conceptual_value"] = conceptual_value(scores)
        c.meta["scores"] = scores
        c.score = float(scores["conceptual_value"])
        reports.append({"concept_id": c.id, "p_emp": p_emp, "surprise": scores["surprise"]})
    return reports
