"""Conceptual-value rubrics (MDL compression / minimality / systematicity / surprise)."""

from __future__ import annotations

import math
from typing import Any

from mathagent.lattice.mdl import score_with_mdl


DEFAULT_WEIGHTS = {
    "compression": 0.35,
    "minimality": 0.25,
    "systematicity": 0.20,
    "surprise": 0.20,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def compression_score(gaps_closed: int, gaps_opened: int, edge_reduction: float = 0.0) -> float:
    """Legacy heuristic (gap counts). Prefer MDL blend via score_proposal."""
    return _clamp((gaps_closed + 0.5 * edge_reduction) / (1.0 + gaps_opened + 1e-6))


def minimality_score(axiom_asks: int, baseline_asks: int = 0, cap: int = 6) -> float:
    return _clamp(1.0 - (axiom_asks - baseline_asks) / (cap + 1e-6))


def systematicity_score(verified_maps: int, claimed_maps: int) -> float:
    return _clamp(verified_maps / (claimed_maps + 1e-6))


def surprise_score(p_before: float, p_after: float, max_delta: float = 6.0) -> float:
    def logit(p: float) -> float:
        p = _clamp(p, 1e-4, 1 - 1e-4)
        return math.log(p / (1 - p))

    delta = logit(p_after) - logit(p_before)
    return _clamp(delta / (max_delta + 1e-6))


def conceptual_value(scores: dict[str, float], weights: dict[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    return _clamp(sum(w[k] * float(scores.get(k, 0.0)) for k in w))


def score_proposal(raw: dict[str, Any]) -> dict[str, float]:
    """Fill rubric scores from an abduction/concept JSON blob (MDL-blended compression)."""
    closes = raw.get("closes_gap_ids") or raw.get("predicted_effects", {}).get("gaps_closed") or []
    opens = raw.get("opens_gap_ids") or []
    axioms = raw.get("axiom_ask") or []
    analogies = raw.get("analogies") or []
    verified = sum(
        1
        for a in analogies
        if str(a.get("check_status", "")).lower() in {"sympy", "lean", "ok", "verified"}
    )
    belief = raw.get("belief") or {}
    p0 = float(belief.get("p_before", 0.3))
    p1 = float(belief.get("p_after", belief.get("p_posterior", 0.5)))

    heur = compression_score(len(closes), len(opens))
    blended, mdl_meta = score_with_mdl(raw, heur)

    scores = {
        "compression": blended,
        "compression_heuristic": heur,
        "minimality": minimality_score(len(axioms), int(raw.get("baseline_asks", 0) or 0)),
        "systematicity": systematicity_score(verified, max(len(analogies), 1)),
        "surprise": surprise_score(p0, p1),
        "mdl_gain": float(mdl_meta["mdl_gain"]),
        "mdl_compression": float(mdl_meta["mdl_compression"]),
    }
    scores["conceptual_value"] = conceptual_value(scores)
    return scores


def needs_human_gate(scores: dict[str, float], axiom_asks: int = 0) -> bool:
    if scores.get("systematicity", 0) < 0.5:
        return True
    if axiom_asks > 2:
        return True
    # Negative MDL gain → always review (theory got longer)
    if scores.get("mdl_gain", 0) < 0:
        return True
    if scores.get("surprise", 0) > 0.7 and scores.get("compression", 0) < 0.4:
        return True
    return scores.get("conceptual_value", 0) >= 0.55
