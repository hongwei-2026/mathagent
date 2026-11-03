"""WAKE phase: attempt to certify frontier conjectures cheaply."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from mathagent.formal.budget import Budget
from mathagent.formal.certify import certify_subgoal
from mathagent.formal.econ import EconEngine
from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph


@dataclass
class WakeOutcome:
    node_id: str
    ok: bool
    method: str
    detail: str
    code: str = ""


def wake_attempt(
    graph: ResearchGraph,
    node: Node,
    *,
    econ: EconEngine,
    budget: Budget,
    on_event: Callable[[str], None] | None = None,
) -> WakeOutcome:
    emit = on_event or (lambda _m: None)
    emit(f"[lattice/wake] {node.id}: {node.statement[:120]}")

    # Prefer Lean/econ if it looks formalizable
    leanish = "theorem" in node.statement or node.meta.get("lean_stub")
    if leanish and budget.can_call():
        goal = str(node.meta.get("lean_stub") or node.statement)
        result = econ.run(goal)
        if result.ok:
            graph.admit_lemma(
                node.statement,
                certificate=f"econ:{result.verdict}",
                parent_id=node.id,
            )
            node.status = NodeStatus.CERTIFIED
            node.certificate = result.verdict
            return WakeOutcome(node.id, True, "econ", result.verdict, result.final_code)
        detail = result.verdict
    else:
        detail = ""

    # SymPy / finite soft certificate via existing certify layer
    sg = {
        "statement": node.statement,
        "certify": node.meta.get("certify_hint") or "sympy",
        "sympy_hint": node.meta.get("sympy_hint") or "",
        "lean_sketch": node.meta.get("lean_stub") or "",
    }
    if sg["sympy_hint"] or sg["certify"] in {"sympy", "finite_check"}:
        cert = certify_subgoal(
            sg,
            {
                "status": "proved",
                "certificate": {"type": sg["certify"], "payload": sg["sympy_hint"]},
            },
        )
        if cert.ok:
            graph.admit_lemma(node.statement, certificate=cert.method, parent_id=node.id)
            node.status = NodeStatus.CERTIFIED
            node.certificate = cert.method
            return WakeOutcome(node.id, True, cert.method, cert.detail)

    # Blocked → Gap
    reason = detail or "unproved within wake budget"
    graph.add_gap(node.statement, parent_id=node.id, reason=reason)
    node.status = NodeStatus.BLOCKED
    return WakeOutcome(node.id, False, "gap", reason)
