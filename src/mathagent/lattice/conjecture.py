from __future__ import annotations

from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings
from mathagent.formal.json_util import extract_json
from mathagent.lattice.prompts import CONJECTURE_SYSTEM


def generate_conjecture_pool(
    problem: str,
    *,
    client: OpenAI,
    settings: Settings,
    on_event: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    emit = on_event or (lambda _m: None)
    model = settings.resolved_formal_model
    emit(f"[lattice/conjecture] {model}")
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": CONJECTURE_SYSTEM},
            {"role": "user", "content": f"Research problem / target:\n{problem}"},
        ],
    }
    if "reasoner" not in model.lower():
        kwargs["temperature"] = 0.2
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    emit(content[:1000])
    return extract_json(content)
