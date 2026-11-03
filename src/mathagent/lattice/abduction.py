"""Abductive proposal generation — explain gaps by inventing concepts (Peirce/HALO)."""

from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.graph import NodeKind, ResearchGraph
from mathagent.lattice.prompts import ABDUCTION_SYSTEM
from mathagent.lattice.value import needs_human_gate, score_proposal


def run_abduction(
    graph: ResearchGraph,
    *,
    client: OpenAI,
    settings: Settings,
    on_event: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    emit = on_event or (lambda _m: None)
    gaps = graph.by_kind(NodeKind.GAP)
    targets = graph.by_kind(NodeKind.TARGET)
    target_txt = targets[0].statement if targets else graph.project_id
    gap_lines = []
    for g in gaps[:12]:
        reason = (g.meta or {}).get("reason", "")
        gap_lines.append(f"- [{g.id}] {g.statement}" + (f" (reason: {reason})" if reason else ""))
    gap_txt = "\n".join(gap_lines) or "(none yet)"

    emit("[lattice/abduction] proposing concepts")
    model = settings.resolved_formal_model
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": ABDUCTION_SYSTEM},
            {
                "role": "user",
                "content": f"TARGET:\n{target_txt}\n\nGAPS:\n{gap_txt}",
            },
        ],
    }
    if "reasoner" not in model.lower():
        kwargs["temperature"] = 0.3
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or "{}"
    emit(content[:900])
    try:
        data = extract_json(content)
    except Exception:
        return []

    scored: list[dict[str, Any]] = []
    gap_by_stmt = {g.statement: g.id for g in gaps}
    for prop in data.get("proposals") or []:
        closes = []
        for x in prop.get("closes_gap_ids") or []:
            if x in graph.nodes:
                closes.append(x)
            else:
                for stmt, gid in gap_by_stmt.items():
                    if str(x)[:40] in stmt or stmt[:40] in str(x):
                        closes.append(gid)
                        break
        prop["closes_gap_ids"] = list(dict.fromkeys(closes))
        scores = score_proposal(prop)
        prop["scores"] = scores
        prop["human_gate_required"] = needs_human_gate(scores, len(prop.get("axiom_ask") or []))
        concept = graph.admit_concept(
            str(prop.get("statement", "")),
            name=str(prop.get("name", "")),
            closes_gap_ids=prop["closes_gap_ids"],
            scores=scores,
            human_gate=prop["human_gate_required"],
        )
        concept.meta["why_old_language_fails"] = prop.get("why_old_language_fails", "")
        concept.meta["axiom_ask"] = prop.get("axiom_ask") or []
        concept.meta["analogies"] = prop.get("analogies") or []
        concept.meta["belief"] = prop.get("belief") or {}
        concept.meta["predicted_leaf_checks"] = prop.get("predicted_leaf_checks") or []
        # Persist explanation cost as real gaps (HALO-style price of abduction)
        open_ids: list[str] = []
        for raw in prop.get("opens_gap_ids") or []:
            stmt = str(raw).strip()
            if not stmt:
                continue
            if stmt in graph.nodes:
                open_ids.append(stmt)
                continue
            gap = graph.add_gap(stmt, parent_id=concept.id, reason="opened_by_concept")
            open_ids.append(gap.id)
        concept.meta["opens_gap_ids"] = open_ids
        prop["opens_gap_ids"] = open_ids
        prop["node_id"] = concept.id
        scored.append(prop)
        emit(
            f"[concept] {concept.meta.get('name')} V={scores['conceptual_value']:.2f} "
            f"gate={prop['human_gate_required']}"
        )
    return scored
