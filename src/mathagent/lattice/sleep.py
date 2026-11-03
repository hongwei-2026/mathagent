"""SLEEP phase: DreamCoder-style library learning (definitions / ops), not fake lemmas."""

from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.mdl import graph_dl
from mathagent.lattice.prompts import SLEEP_SYSTEM
from mathagent.lattice.value import needs_human_gate, score_proposal


def sleep_consolidate(
    graph: ResearchGraph,
    *,
    client: OpenAI,
    settings: Settings,
    on_event: Callable[[str], None] | None = None,
    library_learning: bool = True,
) -> dict[str, Any]:
    emit = on_event or (lambda _m: None)
    lemmas = [
        n.statement
        for n in graph.by_kind(NodeKind.LEMMA)
        if n.status == NodeStatus.CERTIFIED
    ]
    blocked = [n.statement for n in graph.by_kind(NodeKind.GAP)][:12]
    if not lemmas and not blocked:
        return {"keep_lemmas": [], "library_ops": [], "lessons": ["empty graph"], "graph_dl": graph_dl(graph)}

    emit("[lattice/sleep] library consolidating" if library_learning else "[lattice/sleep] consolidating")
    model = settings.model
    raw = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SLEEP_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Certified lemmas:\n- "
                    + "\n- ".join(lemmas[:20] or ["(none yet)"])
                    + "\n\nGaps/failures:\n- "
                    + "\n- ".join(blocked[:12] or ["(none)"])
                    + f"\n\nCurrent graph_dl≈{graph_dl(graph):.1f} bits (prefer ops that shrink this)."
                ),
            },
        ],
    )
    content = raw.choices[0].message.content or "{}"
    emit(content[:800])
    try:
        data = extract_json(content)
    except Exception:
        data = {"keep_lemmas": lemmas, "library_ops": [], "abstract_lemmas": [], "lessons": []}

    admitted = []
    ops = list(data.get("library_ops") or [])
    # Back-compat: promote old abstract_lemmas into library-shaped ops
    for abs_lem in data.get("abstract_lemmas") or []:
        ops.append(
            {
                "name": str(abs_lem.get("statement", ""))[:48],
                "statement": abs_lem.get("statement", ""),
                "kind": "def",
                "why_transferable": abs_lem.get("why_transferable", ""),
                "from": abs_lem.get("from") or [],
                "predicted_leaf_checks": [],
            }
        )

    if library_learning:
        for op in ops:
            stmt = str(op.get("statement", "")).strip()
            if not stmt:
                continue
            if any(
                n.kind == NodeKind.CONCEPT and n.statement == stmt for n in graph.nodes.values()
            ):
                continue
            prop = {
                "name": op.get("name") or stmt[:48],
                "statement": stmt,
                "closes_gap_ids": op.get("closes_gap_ids") or [],
                "opens_gap_ids": op.get("opens_gap_ids") or [],
                "axiom_ask": op.get("axiom_ask") or [],
                "analogies": [],
                "belief": {"p_before": 0.35, "p_after": 0.55},
                "predicted_leaf_checks": op.get("predicted_leaf_checks") or [],
            }
            scores = score_proposal(prop)
            # Library ops always co-abduction-gated (never auto-wake as lemmas)
            _ = needs_human_gate(scores, len(prop["axiom_ask"]))
            node = graph.admit_concept(
                stmt,
                name=str(prop["name"]),
                closes_gap_ids=prop["closes_gap_ids"],
                scores=scores,
                human_gate=True,
            )
            node.meta["from_sleep"] = True
            node.meta["library_op"] = {
                "kind": op.get("kind") or "def",
                "template": op.get("template") or "",
                "why_transferable": op.get("why_transferable") or "",
                "from": op.get("from") or [],
            }
            node.meta["predicted_leaf_checks"] = prop["predicted_leaf_checks"]
            node.meta["belief"] = prop["belief"]
            # Never put uncertified abstractions on the wake conjecture frontier
            admitted.append(node.id)
            emit(f"[library] {node.meta.get('name')} V={scores['conceptual_value']:.2f}")
    else:
        # Classic fallback: low-priority conjectures only (no 0.8 leapfrog)
        for op in ops:
            stmt = str(op.get("statement", "")).strip()
            if not stmt:
                continue
            from mathagent.lattice.graph import Node

            node = Node.new(
                NodeKind.CONJECTURE,
                stmt,
                transferable=True,
                from_sleep=True,
                why=op.get("why_transferable", ""),
            )
            node.score = 0.45
            node.status = NodeStatus.OPEN
            graph.add(node)

    for i, stmt in enumerate(data.get("next_frontier") or []):
        for n in graph.nodes.values():
            if n.kind == NodeKind.CONJECTURE and stmt[:40] in n.statement:
                n.score = max(n.score, 0.7 - 0.05 * i)

    data["library_admitted"] = admitted
    data["graph_dl"] = graph_dl(graph)
    return data
