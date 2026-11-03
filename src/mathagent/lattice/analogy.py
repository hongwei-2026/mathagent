"""Structure-mapping style analogy checks (cheap witnesses via SymPy when possible)."""

from __future__ import annotations

from typing import Any

from mathagent.formal.certify import certify_algebraic_claim
from mathagent.lattice.graph import Node, NodeKind, ResearchGraph
from mathagent.lattice.value import conceptual_value, systematicity_score


def verify_analogy_maps(analogies: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Best-effort: if an analogy carries a sympy_hint / preserves identity, try certify.
    Returns (verified, claimed).
    """
    claimed = 0
    verified = 0
    for a in analogies or []:
        maps = a.get("maps") or []
        claimed += max(len(maps), 1)
        hint = a.get("sympy_hint") or a.get("preserves_hint") or ""
        if not hint:
            for m in maps:
                if m.get("sympy_hint"):
                    hint = m["sympy_hint"]
                    break
        if hint:
            res = certify_algebraic_claim(str(hint))
            if res.ok:
                verified += 1
                a["check_status"] = "sympy"
            else:
                a["check_status"] = "failed"
        else:
            a["check_status"] = a.get("check_status") or "unchecked"
    return verified, claimed


def enrich_concepts_with_analogy_checks(graph: ResearchGraph) -> None:
    for n in graph.by_kind(NodeKind.CONCEPT):
        analogies = list(n.meta.get("analogies") or [])
        if not analogies:
            continue
        verified, claimed = verify_analogy_maps(analogies)
        n.meta["analogies"] = analogies
        scores = dict(n.meta.get("scores") or {})
        scores["systematicity"] = systematicity_score(verified, claimed)
        scores["conceptual_value"] = conceptual_value(scores)
        n.meta["scores"] = scores
        n.score = float(scores["conceptual_value"])


def top_concepts(graph: ResearchGraph, limit: int = 3) -> list[Node]:
    return graph.conceptual_frontier(limit=limit)
