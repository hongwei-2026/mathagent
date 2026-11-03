"""MDL-style description length for research graphs (laptop-scale bits proxy)."""

from __future__ import annotations

import math
from typing import Any

from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph

KIND_BITS: dict[NodeKind, float] = {
    NodeKind.TARGET: 6.0,
    NodeKind.PLAN: 5.0,
    NodeKind.LEMMA: 4.0,
    NodeKind.CONJECTURE: 10.0,
    NodeKind.GAP: 14.0,
    NodeKind.COUNTEREXAMPLE: 8.0,
    NodeKind.CONCEPT: 12.0,
    NodeKind.ABDUCTION: 11.0,
}
EDGE_BITS = 2.5
AXIOM_BITS = 9.0
GAP_OBLIGATION = 16.0  # active unexplained gap surcharge
STMT_CAP = 512


def statement_bits(text: str, cap: int = STMT_CAP) -> float:
    raw = (text or "").encode("utf-8")
    return float(8 * min(len(raw), cap))


def _active_gap(node) -> bool:
    return node.kind == NodeKind.GAP and node.status in {
        NodeStatus.OPEN,
        NodeStatus.BLOCKED,
    }


def graph_dl(
    graph: ResearchGraph,
    *,
    include_conjectures: bool = False,
    stmt_cap: int = STMT_CAP,
) -> float:
    """Description length: nodes + edges + active gap obligations."""
    n = max(len(graph.nodes), 2)
    edge_cost = 2.0 * math.log2(n) + math.log2(5)
    total = 0.0
    for v in graph.nodes.values():
        total += KIND_BITS.get(v.kind, 8.0) + statement_bits(v.statement, stmt_cap)
        if v.kind == NodeKind.LEMMA and v.status == NodeStatus.CERTIFIED:
            total -= 2.0
        if _active_gap(v):
            total += GAP_OBLIGATION + statement_bits(v.statement, stmt_cap)
        elif (
            include_conjectures
            and v.kind in {NodeKind.TARGET, NodeKind.CONJECTURE}
            and v.status == NodeStatus.OPEN
        ):
            total += 8.0 + 0.5 * statement_bits(v.statement, stmt_cap)
    valid_edges = sum(
        1 for e in graph.edges if e.src in graph.nodes and e.dst in graph.nodes
    )
    total += valid_edges * edge_cost
    return max(0.0, total)


def _dedupe(ids: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(x) for x in ids if x is not None and str(x).strip()))


def concept_mdl_gain(
    *,
    gaps_closed: int | None = None,
    gaps_opened: int | None = None,
    axiom_asks: int = 0,
    concept_statement: str = "",
    baseline_asks: int = 0,
    graph: ResearchGraph | None = None,
    closes_gap_ids: list[str] | None = None,
    opens_gap_ids: list[str] | None = None,
    axiom_ask: list[dict[str, Any]] | None = None,
    lemmas_replaced: int = 0,
) -> float:
    """
    Δbits ≈ credit(active closed gaps) - price(concept + edges + opens + axioms).
    Positive ⇒ net compression.
    """
    closes = _dedupe(closes_gap_ids or [])
    opens = _dedupe(opens_gap_ids or [])
    axioms = axiom_ask or []

    credit = 0.0
    k_eff = 0
    if graph is not None and closes:
        for gid in closes:
            nd = graph.nodes.get(gid)
            if nd is not None and _active_gap(nd):
                credit += GAP_OBLIGATION + statement_bits(nd.statement)
                k_eff += 1
    else:
        # Count-only: assume each closed gap is at least as costly as the concept text
        k = gaps_closed if gaps_closed is not None else len(closes)
        stub = max(statement_bits(concept_statement), statement_bits("research gap"))
        credit = k * (GAP_OBLIGATION + stub)
        k_eff = k

    m = gaps_opened if gaps_opened is not None else len(opens)
    a = len(axioms) if axioms else axiom_asks
    n = max(len(graph.nodes) + 1, 2) if graph is not None else 2
    edge_cost = 2.0 * math.log2(n) + math.log2(5)

    cost = (
        KIND_BITS[NodeKind.CONCEPT]
        + statement_bits(concept_statement)
        + k_eff * edge_cost
        + m * (GAP_OBLIGATION + statement_bits(""))
        + max(0, a - baseline_asks) * AXIOM_BITS
    )
    # DreamCoder-ish: multi-lemma reuse shrinks theory
    credit += max(0, lemmas_replaced) * 6.0
    return credit - cost


def mdl_compression_score(gain: float, scale: float = 24.0) -> float:
    return 1.0 / (1.0 + math.exp(-gain / (scale + 1e-6)))


def blend_compression(heuristic: float, mdl: float, w_mdl: float = 0.65) -> float:
    return max(0.0, min(1.0, (1.0 - w_mdl) * heuristic + w_mdl * mdl))


def score_with_mdl(
    raw: dict[str, Any],
    heuristic_compression: float,
    graph: ResearchGraph | None = None,
) -> tuple[float, dict[str, float]]:
    closes = _dedupe(raw.get("closes_gap_ids") or [])
    opens = _dedupe(raw.get("opens_gap_ids") or [])
    axioms = raw.get("axiom_ask") or []
    comp = raw.get("compression") or {}
    lemmas_replaced = int(comp.get("lemmas_replaced") or len(raw.get("from") or []) or 0)
    gain = concept_mdl_gain(
        graph=graph,
        closes_gap_ids=closes,
        opens_gap_ids=opens,
        axiom_ask=axioms,
        concept_statement=str(raw.get("statement") or raw.get("name") or ""),
        baseline_asks=int(raw.get("baseline_asks", 0) or 0),
        lemmas_replaced=lemmas_replaced,
    )
    mdl = mdl_compression_score(gain)
    return blend_compression(heuristic_compression, mdl), {
        "mdl_gain": gain,
        "mdl_compression": mdl,
        "graph_dl_hint": graph_dl(graph) if graph is not None else 0.0,
    }
