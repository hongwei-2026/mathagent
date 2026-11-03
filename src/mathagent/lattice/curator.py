"""Curator: rank work by conceptual surprise×compression, not proof pass rate."""

from __future__ import annotations

from typing import Any

from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph


def rank_for_exploration(graph: ResearchGraph, limit: int = 5) -> list[Node]:
    """
    Priority:
      1) ACCEPTED concepts' predicted leaf checks (as synthetic conjectures already in meta)
      2) Concepts with high conceptual_value but still OPEN/HUMAN_REVIEW (need gate note)
      3) Ordinary conjectures with certify_hint (cheap leaves) — lower weight
    """
    ranked: list[tuple[float, Node]] = []
    for n in graph.nodes.values():
        if n.status in {NodeStatus.CERTIFIED, NodeStatus.REJECTED, NodeStatus.REFUTED}:
            continue
        scores = (n.meta or {}).get("scores") or {}
        v = float(scores.get("conceptual_value", 0.0))
        surprise = float(scores.get("surprise", 0.0))
        compression = float(scores.get("compression", 0.0))
        if n.kind == NodeKind.CONCEPT:
            # explore consequences of high-V concepts; gate-pending still listed but lower
            gate_pen = 0.15 if n.status == NodeStatus.HUMAN_REVIEW else 0.0
            ranked.append((0.7 * v + 0.2 * surprise + 0.1 * compression - gate_pen, n))
        elif n.kind == NodeKind.CONJECTURE:
            # cheap leaves get modest score unless tagged from_concept
            bonus = 0.25 if n.meta.get("from_concept") else 0.0
            ranked.append((0.35 * n.score + bonus + 0.1 * compression, n))
        elif n.kind == NodeKind.GAP:
            ranked.append((0.2 + 0.1 * surprise, n))
    ranked.sort(key=lambda x: -x[0])
    return [n for _, n in ranked[:limit]]


def spawn_leaf_conjectures_from_concepts(graph: ResearchGraph) -> list[Node]:
    """Materialize predicted_leaf_checks as Conjecture nodes linked to Concept."""
    spawned: list[Node] = []
    for c in graph.by_kind(NodeKind.CONCEPT):
        if c.status == NodeStatus.REJECTED:
            continue
        for leaf in c.meta.get("predicted_leaf_checks") or []:
            stmt = str(leaf.get("statement", "")).strip()
            if not stmt:
                continue
            if any(n.statement == stmt for n in graph.nodes.values()):
                continue
            node = Node.new(
                NodeKind.CONJECTURE,
                stmt,
                from_concept=c.id,
                certify_hint=leaf.get("certify_hint") or "sympy",
                sympy_hint=leaf.get("sympy_hint") or "",
                lean_stub=leaf.get("lean_stub") or "",
            )
            node.score = max(0.55, float((c.meta.get("scores") or {}).get("conceptual_value", 0.5)))
            graph.add(node)
            graph.link(c.id, node.id, "supports")
            spawned.append(node)
    return spawned


def curator_report(graph: ResearchGraph) -> dict[str, Any]:
    top = rank_for_exploration(graph, limit=5)
    return {
        "next": [
            {
                "id": n.id,
                "kind": n.kind.value,
                "status": n.status.value,
                "statement": n.statement[:160],
                "conceptual_value": (n.meta.get("scores") or {}).get("conceptual_value"),
            }
            for n in top
        ],
        "concepts": len(graph.by_kind(NodeKind.CONCEPT)),
        "human_review_queue": [
            n.id for n in graph.by_kind(NodeKind.CONCEPT) if n.status == NodeStatus.HUMAN_REVIEW
        ],
    }
