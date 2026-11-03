"""Structure-mapping style analogy checks (cheap witnesses via SymPy when possible)."""

from __future__ import annotations

from typing import Any

from mathagent.formal.certify import certify_algebraic_claim
from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.value import conceptual_value, needs_human_gate, systematicity_score


def _hint_for_map(m: dict[str, Any]) -> str:
    return str(m.get("sympy_hint") or m.get("preserves_hint") or "").strip()


def verify_analogy_maps(
    analogies: list[dict[str, Any]], *, statement: str = ""
) -> tuple[int, int]:
    """
    Per-map verification when sympy_hint present; otherwise unchecked.
    Returns (verified_maps, claimed_maps).
    """
    claimed = 0
    verified = 0
    for a in analogies or []:
        maps = a.get("maps") or []
        if not maps:
            claimed += 1
            hint = str(a.get("sympy_hint") or a.get("preserves_hint") or "").strip()
            if hint:
                res = certify_algebraic_claim(hint, statement=statement)
                if res.ok:
                    verified += 1
                    a["check_status"] = "sympy"
                else:
                    a["check_status"] = "failed"
            else:
                a["check_status"] = a.get("check_status") or "unchecked"
            continue

        map_statuses: list[str] = []
        for m in maps:
            claimed += 1
            hint = _hint_for_map(m) or str(a.get("sympy_hint") or "").strip()
            if not hint:
                m["check_status"] = "unchecked"
                map_statuses.append("unchecked")
                continue
            res = certify_algebraic_claim(hint, statement=statement)
            if res.ok:
                verified += 1
                m["check_status"] = "sympy"
                map_statuses.append("sympy")
            else:
                m["check_status"] = "failed"
                map_statuses.append("failed")

        if map_statuses and all(s == "sympy" for s in map_statuses):
            a["check_status"] = "sympy"
        elif "failed" in map_statuses:
            a["check_status"] = "failed"
        else:
            a["check_status"] = "unchecked"
    return verified, claimed


def enrich_concepts_with_analogy_checks(graph: ResearchGraph) -> None:
    """Update systematicity from SymPy map checks and refresh human-gate status."""
    for n in graph.by_kind(NodeKind.CONCEPT):
        analogies = list(n.meta.get("analogies") or [])
        if analogies:
            verified, claimed = verify_analogy_maps(analogies, statement=n.statement)
            n.meta["analogies"] = analogies
            scores = dict(n.meta.get("scores") or {})
            scores["systematicity"] = systematicity_score(verified, claimed)
            scores["conceptual_value"] = conceptual_value(scores)
            n.meta["scores"] = scores
            n.score = float(scores["conceptual_value"])
        else:
            scores = dict(n.meta.get("scores") or {})

        if n.status in {NodeStatus.REJECTED, NodeStatus.ACCEPTED}:
            continue
        axioms = n.meta.get("axiom_ask") or []
        gate = needs_human_gate(scores, len(axioms))
        hg = dict(n.meta.get("human_gate") or {})
        hg["required"] = gate
        n.meta["human_gate"] = hg
        if gate:
            n.status = NodeStatus.HUMAN_REVIEW
        elif n.status == NodeStatus.HUMAN_REVIEW:
            # Analogy evidence cleared the gate heuristic
            n.status = NodeStatus.OPEN


def top_concepts(graph: ResearchGraph, limit: int = 3) -> list[Node]:
    return graph.conceptual_frontier(limit=limit)
