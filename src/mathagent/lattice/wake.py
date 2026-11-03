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

    # Think pillar 1: concept-linked leaves must go through executable library when present
    from mathagent.lattice.think.executable import wake_via_library

    lib = wake_via_library(graph, node, on_event=emit)
    if lib is not None:
        if lib.ok:
            return WakeOutcome(node.id, True, f"lib:{lib.method}", lib.detail)
        # Library call failed — still try leaf sympy_hint below; record failure
        detail = lib.detail
    else:
        detail = ""

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
        detail = detail or result.verdict

    # SymPy / finite soft certificate — only with a real witness (no empty "proved")
    hint = str(node.meta.get("sympy_hint") or "").strip()
    certify = str(node.meta.get("certify_hint") or ("sympy" if hint else "manual")).lower()
    lean_stub = str(node.meta.get("lean_stub") or "").strip()
    sg = {
        "statement": node.statement,
        "certify": certify,
        "sympy_hint": hint,
        "lean_sketch": lean_stub,
    }
    has_witness = bool(hint) or (certify == "finite_check" and hint) or (
        certify == "lean" and lean_stub
    )
    if has_witness:
        cert = certify_subgoal(
            sg,
            {"certificate": {"type": certify, "payload": hint or lean_stub}},
        )
        if cert.ok:
            graph.admit_lemma(node.statement, certificate=cert.method, parent_id=node.id)
            node.status = NodeStatus.CERTIFIED
            node.certificate = cert.method
            return WakeOutcome(node.id, True, cert.method, cert.detail)
        detail = detail or cert.detail
    elif certify in {"sympy", "finite_check", "lean"}:
        detail = detail or "missing sympy_hint/lean_stub for cheap certificate"

    # Blocked → Gap
    reason = detail or "unproved within wake budget"
    graph.add_gap(node.statement, parent_id=node.id, reason=reason)
    node.status = NodeStatus.BLOCKED
    return WakeOutcome(node.id, False, "gap", reason)
