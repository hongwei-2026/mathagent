"""
Pillar 2 — Cheap discriminating tests (Robot Scientist / Eve style).

Before MDL fitness wars: run each competing concept's predicted sympy leaves.
A hypothesis that fails all of its own certifiable predictions is eliminated.
"""

from __future__ import annotations

from typing import Any

from mathagent.formal.certify import certify_algebraic_claim
from mathagent.lattice.graph import NodeStatus, ResearchGraph
from mathagent.lattice.think.arena import arenas
from mathagent.lattice.think.executable import call_op, extract_executable


def _run_concept_leaves(concept) -> dict[str, Any]:
    ok = fail = 0
    details: list[str] = []
    for leaf in concept.meta.get("predicted_leaf_checks") or []:
        hint = str(leaf.get("sympy_hint") or "").strip()
        if not hint:
            continue
        res = certify_algebraic_claim(hint, statement=str(leaf.get("statement") or ""))
        if res.ok:
            ok += 1
            details.append(f"pass:{hint[:60]}")
        else:
            fail += 1
            details.append(f"fail:{hint[:40]}|{res.detail[:40]}")
    if extract_executable(concept) is not None:
        # Default binding / leaf_bundle path
        cres = call_op(concept)
        if cres.ok:
            ok += 1
            details.append(f"call_op:pass:{cres.op_name}")
        elif cres.method != "no_exec":
            fail += 1
            details.append(f"call_op:fail:{cres.detail[:60]}")
    total = ok + fail
    return {
        "ok": ok,
        "fail": fail,
        "rate": (ok / total) if total else None,
        "details": details[:8],
    }


def run_cheap_discriminators(
    graph: ResearchGraph,
    *,
    on_event: Any = None,
) -> list[dict[str, Any]]:
    """
    In each arena: score cheap tests; eliminate concepts with rate==0 when a
    rival has rate>0. Does not touch HUMAN_REVIEW.
    """
    emit = on_event or (lambda _m: None)
    reports: list[dict[str, Any]] = []
    for key, members in arenas(graph).items():
        active = [c for c in members if c.status not in {NodeStatus.REJECTED, NodeStatus.HUMAN_REVIEW}]
        if len(active) < 2:
            continue
        scored = []
        for c in active:
            stats = _run_concept_leaves(c)
            c.meta["cheap_test"] = stats
            scored.append((c, stats))
            emit(
                f"[think/cheap] {c.meta.get('name') or c.id} "
                f"ok={stats['ok']} fail={stats['fail']}"
            )

        rates = [(c, s) for c, s in scored if s["rate"] is not None]
        if not rates:
            continue
        best_rate = max(s["rate"] for _, s in rates)
        if best_rate <= 0:
            continue
        killed = []
        for c, s in rates:
            if s["rate"] == 0.0 and s["fail"] > 0:
                c.status = NodeStatus.REJECTED
                gate = dict(c.meta.get("human_gate") or {})
                gate["decision"] = "cheap_test_reject"
                gate["notes"] = f"arena {key}: all cheap predictions failed"
                c.meta["human_gate"] = gate
                c.meta["elimination_reason"] = "cheap_test_all_failed"
                killed.append(c.id)
                emit(f"[think/cheap] REJECTED {c.id} (failed discriminators)")
        if killed:
            survivors = [c for c, s in rates if c.id not in killed]
            if len(survivors) == 1:
                survivors[0].meta["arena_win"] = {
                    "arena": key,
                    "killed": killed,
                    "via": "cheap_test",
                }
                if survivors[0].status == NodeStatus.OPEN:
                    survivors[0].status = NodeStatus.ACCEPTED
            reports.append({"arena": key, "killed": killed, "via": "cheap_test"})
    return reports
