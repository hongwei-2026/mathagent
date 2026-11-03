"""MDL-style description length for research graphs (laptop-scale bits proxy)."""

from __future__ import annotations

import math
from typing import Any

from mathagent.lattice.graph import NodeKind, ResearchGraph

# Rough coding costs (nats→bits via /ln2 not needed; relative bits OK)
KIND_BITS: dict[NodeKind, float] = {
    NodeKind.TARGET: 6.0,
    NodeKind.PLAN: 5.0,
    NodeKind.LEMMA: 4.0,  # certified fact — cheap once admitted
    NodeKind.CONJECTURE: 10.0,  # open obligation
    NodeKind.GAP: 14.0,  # expensive unexplained debt
    NodeKind.COUNTEREXAMPLE: 8.0,
    NodeKind.CONCEPT: 12.0,  # new language has upfront cost
    NodeKind.ABDUCTION: 11.0,
}
EDGE_BITS = 2.5
AXIOM_BITS = 9.0
GAP_VIRTUAL = 14.0  # used in counterfactual gain when gaps not deleted


def statement_bits(text: str) -> float:
    # UTF-ish proxy: longer statements cost more to store/maintain
    n = len((text or "").strip())
    return 4.0 + 0.08 * n


def graph_dl(graph: ResearchGraph) -> float:
    """Total description length of the typed research memory."""
    total = 0.0
    for n in graph.nodes.values():
        total += KIND_BITS.get(n.kind, 8.0) + statement_bits(n.statement)
        # certified lemmas get a small rebate (already compressed knowledge)
        if n.kind == NodeKind.LEMMA:
            total -= 2.0
    total += EDGE_BITS * len(graph.edges)
    return max(0.0, total)


def concept_mdl_gain(
    *,
    gaps_closed: int,
    gaps_opened: int,
    axiom_asks: int,
    concept_statement: str = "",
    baseline_asks: int = 0,
) -> float:
    """
    Counterfactual bits saved by introducing a concept:
      gain ≈ closed_gaps * GAP_VIRTUAL
            - DL(concept text)
            - opened_gaps * GAP_VIRTUAL
            - extra axioms * AXIOM_BITS
    Positive gain ⇒ theory got shorter.
    """
    saved = gaps_closed * GAP_VIRTUAL
    cost = (
        KIND_BITS[NodeKind.CONCEPT]
        + statement_bits(concept_statement)
        + gaps_opened * GAP_VIRTUAL
        + max(0, axiom_asks - baseline_asks) * AXIOM_BITS
    )
    return saved - cost


def mdl_compression_score(gain: float, scale: float = 24.0) -> float:
    """Map bit-gain to [0,1] via logistic (0 gain → ~0.5)."""
    return 1.0 / (1.0 + math.exp(-gain / (scale + 1e-6)))


def blend_compression(heuristic: float, mdl: float, w_mdl: float = 0.65) -> float:
    return max(0.0, min(1.0, (1.0 - w_mdl) * heuristic + w_mdl * mdl))


def score_with_mdl(raw: dict[str, Any], heuristic_compression: float) -> tuple[float, dict[str, float]]:
    closes = raw.get("closes_gap_ids") or []
    opens = raw.get("opens_gap_ids") or []
    axioms = raw.get("axiom_ask") or []
    gain = concept_mdl_gain(
        gaps_closed=len(closes),
        gaps_opened=len(opens),
        axiom_asks=len(axioms),
        concept_statement=str(raw.get("statement") or raw.get("name") or ""),
        baseline_asks=int(raw.get("baseline_asks", 0) or 0),
    )
    mdl = mdl_compression_score(gain)
    return blend_compression(heuristic_compression, mdl), {
        "mdl_gain": gain,
        "mdl_compression": mdl,
        "graph_dl_hint": None,
    }
