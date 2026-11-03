"""SLEEP phase: DreamCoder-style library learning (definitions / ops), not fake lemmas."""

from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.graph import NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.mdl import graph_dl
from mathagent.lattice.prompts import SLEEP_SYSTEM
from mathagent.lattice.value import conceptual_value, needs_human_gate, score_proposal


def admit_library_op(graph: ResearchGraph, op: dict[str, Any]) -> Any | None:
    """Admit one library_op as a gated CONCEPT. Requires predicted_leaf_checks."""
    stmt = str(op.get("statement", "")).strip()
    if not stmt:
        return None
    leaves = op.get("predicted_leaf_checks") or []
    if not leaves:
        return None
    name = str(op.get("name") or stmt[:48])
    if any(
        n.kind == NodeKind.CONCEPT
        and (n.meta.get("name") == name or n.statement == stmt)
        and n.meta.get("origin") == "sleep"
        for n in graph.nodes.values()
    ):
        return None

    from_lemmas = op.get("from") or []
    prop = {
        "name": name,
        "statement": stmt,
        "closes_gap_ids": op.get("closes_gap_ids") or [],
        "opens_gap_ids": op.get("opens_gap_ids") or [],
        "axiom_ask": op.get("axiom_ask") or [],
        "analogies": [],
        "belief": op.get("belief") or {"p_before": 0.35, "p_after": 0.55},
        "predicted_leaf_checks": leaves,
        "from": from_lemmas,
        "compression": op.get("compression")
        or {"lemmas_replaced": max(1, len(from_lemmas))},
    }
    scores = score_proposal(prop, graph=graph)
    lr = int((prop["compression"] or {}).get("lemmas_replaced") or 0)
    if lr:
        scores["compression"] = max(
            scores["compression"],
            min(1.0, lr / (1.0 + len(prop["opens_gap_ids"]))),
        )
        scores["conceptual_value"] = conceptual_value(scores)
    _ = needs_human_gate(scores, len(prop["axiom_ask"]))
    node = graph.admit_concept(
        stmt,
        name=name,
        closes_gap_ids=prop["closes_gap_ids"],
        scores=scores,
        human_gate=True,  # library ops always co-abduction-gated
    )
    node.meta["origin"] = "sleep"
    node.meta["from_sleep"] = True
    node.meta["library_op"] = op
    node.meta["artifact"] = op.get("artifact") or {
        "template": op.get("template") or "",
        "kind": op.get("kind") or "def",
    }
    node.meta["from_lemmas"] = from_lemmas
    node.meta["predicted_leaf_checks"] = leaves
    node.meta["belief"] = prop["belief"]
    node.meta["axiom_ask"] = prop["axiom_ask"]
    # Provenance edges to matching lemmas
    for src in from_lemmas:
        s = str(src)
        for lem in graph.by_kind(NodeKind.LEMMA):
            if s[:40] in lem.statement or lem.statement[:40] in s:
                graph.link(node.id, lem.id, "abstracts")
                break
    return node


def sleep_consolidate(
    graph: ResearchGraph,
    *,
    client: OpenAI,
    settings: Settings,
    on_event: Callable[[str], None] | None = None,
    concept_value: bool = False,
) -> dict[str, Any]:
    """
    concept_value=False (classic): rescore next_frontier only; never inject nodes.
    concept_value=True: admit library_ops as gated Concepts (no CONJECTURE@0.8).
    """
    emit = on_event or (lambda _m: None)
    lemmas = [
        n.statement
        for n in graph.by_kind(NodeKind.LEMMA)
        if n.status == NodeStatus.CERTIFIED
    ]
    blocked = [n.statement for n in graph.by_kind(NodeKind.GAP)][:12]
    if not lemmas and not blocked:
        return {
            "keep_lemmas": [],
            "library_ops": [],
            "lessons": ["empty graph"],
            "graph_dl": graph_dl(graph),
        }

    emit(
        "[lattice/sleep] library consolidating"
        if concept_value
        else "[lattice/sleep] consolidating (classic, no graph writes)"
    )
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

    admitted: list[str] = []
    ops = list(data.get("library_ops") or [])

    if concept_value:
        for op in ops:
            node = admit_library_op(graph, op)
            if node is None:
                if op.get("statement") and not (op.get("predicted_leaf_checks") or []):
                    data.setdefault("lessons", []).append(
                        f"[library_op refused: no leaf checks] {str(op.get('name') or op.get('statement'))[:80]}"
                    )
                continue
            admitted.append(node.id)
            emit(f"[library] {node.meta.get('name')} status={node.status.value}")
        # Deprecated abstract_lemmas: lessons only — never conjectures
        for legacy in data.get("abstract_lemmas") or []:
            data.setdefault("lessons", []).append(
                f"[deprecated abstract_lemma not admitted] {str(legacy.get('statement', ''))[:120]}"
            )
    else:
        for legacy in (data.get("abstract_lemmas") or []) + ops:
            data.setdefault("lessons", []).append(
                f"[classic sleep: not admitted] {str(legacy.get('statement') or legacy.get('name') or '')[:120]}"
            )

    for i, stmt in enumerate(data.get("next_frontier") or []):
        for n in graph.nodes.values():
            if n.kind == NodeKind.CONJECTURE and stmt[:40] in n.statement:
                n.score = max(n.score, 0.7 - 0.05 * i)

    data["library_admitted"] = admitted
    data["graph_dl"] = graph_dl(graph)
    return data
