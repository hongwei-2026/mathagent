"""Curator: rank work by conceptual surprise×compression, not proof pass rate."""

from __future__ import annotations

from typing import Any

from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph


def rank_for_exploration(graph: ResearchGraph, limit: int = 5) -> list[Node]:
    """
    Rank OPEN conjectures for wake (concept leaves first), with concepts listed
    for reporting. HUMAN_REVIEW concepts are deprioritized; their leaves are not
    spawned until ACCEPTED (see spawn_leaf_conjectures_from_concepts).
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
            if n.status == NodeStatus.HUMAN_REVIEW:
                gate_pen = 0.25
            elif n.status == NodeStatus.ACCEPTED:
                gate_pen = -0.1
            else:
                gate_pen = 0.0
            ranked.append((0.7 * v + 0.2 * surprise + 0.1 * compression - gate_pen, n))
        elif n.kind == NodeKind.CONJECTURE and n.status == NodeStatus.OPEN:
            parent = graph.nodes.get(str(n.meta.get("from_concept") or ""))
            if parent and parent.status == NodeStatus.HUMAN_REVIEW:
                continue  # do not explore leaves of ungated concepts
            bonus = 0.35 if n.meta.get("from_concept") else 0.0
            ranked.append((0.35 * n.score + bonus + 0.1 * compression + 0.15 * surprise, n))
        elif n.kind == NodeKind.GAP:
            ranked.append((0.2 + 0.1 * surprise, n))
    ranked.sort(key=lambda x: -x[0])
    return [n for _, n in ranked[:limit]]


def wake_frontier(graph: ResearchGraph, limit: int = 5) -> list[Node]:
    """Curator-driven wake picker: OPEN conjectures only, ranked."""
    out: list[Node] = []
    for n in rank_for_exploration(graph, limit=limit * 3):
        if n.kind == NodeKind.CONJECTURE and n.status == NodeStatus.OPEN:
            out.append(n)
        if len(out) >= limit:
            break
    return out


def spawn_leaf_conjectures_from_concepts(graph: ResearchGraph) -> list[Node]:
    """Materialize predicted_leaf_checks only for ACCEPTED or ungated OPEN concepts."""
    spawned: list[Node] = []
    for c in graph.by_kind(NodeKind.CONCEPT):
        if c.status == NodeStatus.REJECTED:
            continue
        if c.status == NodeStatus.HUMAN_REVIEW:
            continue
        if c.status not in {NodeStatus.ACCEPTED, NodeStatus.OPEN}:
            continue
        for leaf in c.meta.get("predicted_leaf_checks") or []:
            stmt = str(leaf.get("statement", "")).strip()
            if not stmt:
                continue
            if any(n.statement == stmt for n in graph.nodes.values()):
                continue
            hint = str(leaf.get("sympy_hint") or "").strip()
            certify = leaf.get("certify_hint") or ("sympy" if hint else "manual")
            node = Node.new(
                NodeKind.CONJECTURE,
                stmt,
                from_concept=c.id,
                certify_hint=certify,
                sympy_hint=hint,
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
