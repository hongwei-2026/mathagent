"""Abductive proposal generation — explain gaps by inventing concepts (Peirce/HALO)."""

from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.graph import NodeKind, ResearchGraph
from mathagent.lattice.value import needs_human_gate, score_proposal

ABDUCTION_SYSTEM = """You are the ABDUCTION module of MathLattice (concept-value layer).

Task: given a research TARGET and its GAPS, propose explanatory CONCEPTS — not just
more lemmas to grind. Prefer:
- new language / definitions that compress several gaps
- minimal axiom asks (what must be assumed)
- structural analogies to other domains
- honest belief shift: P(this unifies | before) vs after

Return STRICT JSON:
{
  "proposals": [
    {
      "name": "short concept name",
      "statement": "what the concept claims / defines",
      "why_old_language_fails": "why existing lemmas are not enough",
      "closes_gap_ids": ["use gap statements or ids if known"],
      "opens_gap_ids": [],
      "axiom_ask": [{"id": "A1", "kind": "def|axiom|lemma_assumed", "formal": "..."}],
      "baseline_asks": 0,
      "analogies": [
        {
          "domain_a": "...",
          "domain_b": "...",
          "maps": [{"a": "...", "b": "...", "preserves": "..."}],
          "check_status": "unchecked"
        }
      ],
      "belief": {"p_before": 0.2, "p_after": 0.6},
      "predicted_leaf_checks": [
        {"statement": "cheap certifiable consequence", "certify_hint": "sympy|lean|finite_check", "sympy_hint": ""}
      ]
    }
  ]
}

Max 3 proposals. Prefer conceptual compression over easy algebraic restatements.
"""


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
    gap_txt = "\n".join(f"- [{g.id}] {g.statement}" for g in gaps[:12]) or "(none yet)"

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
        # resolve gap ids by substring match if model returned statements
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
        prop["node_id"] = concept.id
        scored.append(prop)
        emit(
            f"[concept] {concept.meta.get('name')} V={scores['conceptual_value']:.2f} "
            f"gate={prop['human_gate_required']}"
        )
    return scored
