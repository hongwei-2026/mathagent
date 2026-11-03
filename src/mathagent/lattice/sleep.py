"""SLEEP phase: compress certified lemmas into transferable abstractions (DreamProver)."""

from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.graph import Node, NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.prompts import SLEEP_SYSTEM


def sleep_consolidate(
    graph: ResearchGraph,
    *,
    client: OpenAI,
    settings: Settings,
    on_event: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    emit = on_event or (lambda _m: None)
    lemmas = [
        n.statement
        for n in graph.by_kind(NodeKind.LEMMA)
        if n.status == NodeStatus.CERTIFIED
    ]
    blocked = [n.statement for n in graph.by_kind(NodeKind.GAP)][:12]
    if not lemmas and not blocked:
        return {"keep_lemmas": [], "abstract_lemmas": [], "lessons": ["empty graph"]}

    emit("[lattice/sleep] consolidating")
    model = settings.model  # cheap model for compression
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
                ),
            },
        ],
    )
    content = raw.choices[0].message.content or "{}"
    emit(content[:800])
    try:
        data = extract_json(content)
    except Exception:
        data = {"keep_lemmas": lemmas, "abstract_lemmas": [], "lessons": []}

    # Abstractions statements are NOT certificates — admit as high-priority conjectures.
    for abs_lem in data.get("abstract_lemmas") or []:
        stmt = str(abs_lem.get("statement", "")).strip()
        if not stmt:
            continue
        node = Node.new(
            NodeKind.CONJECTURE,
            stmt,
            transferable=True,
            why=abs_lem.get("why_transferable", ""),
            from_sleep=True,
        )
        node.score = 0.8
        node.status = NodeStatus.OPEN
        graph.add(node)

    for i, stmt in enumerate(data.get("next_frontier") or []):
        for n in graph.nodes.values():
            if n.kind == NodeKind.CONJECTURE and stmt[:40] in n.statement:
                n.score = max(n.score, 0.85 - 0.05 * i)
    return data
