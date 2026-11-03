"""
MathAgent core loop.

Combines:
- ToRA: interleaved rationale + tool use
- MathChat: multi-turn tool feedback
- Neuro-Symbolic / DotaMath: self-correction on tool errors
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from openai import OpenAI

from mathagent.config import Settings, get_settings
from mathagent.eval.grader import extract_final_answer
from mathagent.prompts import SOLVE_USER_TEMPLATE, SYSTEM_PROMPT
from mathagent.tools.registry import TOOL_SCHEMAS, dispatch_tool


SIMPLE_ARITH_RE = re.compile(
    r"^[\d\s\.\+\-\*/\(\)\^%,]+$",
)


@dataclass
class ToolEvent:
    name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class SolveResult:
    problem: str
    answer: str
    final_message: str
    turns: int
    tool_events: list[ToolEvent] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)


class MathAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
        on_event: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        else:
            if not self.settings.api_key:
                raise ValueError(
                    "MATHAGENT_API_KEY is empty. Copy .env.example to .env and set your key."
                )
            self.client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
            )
        self.on_event = on_event or (lambda _msg: None)

    def _emit(self, msg: str) -> None:
        self.on_event(msg)

    def _maybe_fast_path(self, problem: str) -> str | None:
        """Skip LLM for pure arithmetic strings."""
        cleaned = problem.strip().rstrip("=?？")
        if SIMPLE_ARITH_RE.match(cleaned) and any(op in cleaned for op in "+-*/^"):
            from mathagent.tools.sympy_ops import calculator

            try:
                return calculator(cleaned.replace("^", "**"))
            except Exception:
                return None
        return None

    def solve(self, problem: str) -> SolveResult:
        fast = self._maybe_fast_path(problem)
        if fast is not None:
            self._emit(f"[fast-path] {fast}")
            return SolveResult(
                problem=problem,
                answer=fast,
                final_message=f"FINAL_ANSWER: {fast}",
                turns=0,
                tool_events=[],
                messages=[],
            )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": SOLVE_USER_TEMPLATE.format(problem=problem)},
        ]
        tool_events: list[ToolEvent] = []

        for turn in range(1, self.settings.max_turns + 1):
            self._emit(f"[turn {turn}] calling {self.settings.model}")
            response = self.client.chat.completions.create(
                model=self.settings.model,
                temperature=self.settings.temperature,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            msg = choice.message
            assistant_payload: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
            }
            if msg.tool_calls:
                assistant_payload["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_payload)

            if msg.content:
                self._emit(msg.content)

            if not msg.tool_calls:
                answer = extract_final_answer(msg.content or "")
                return SolveResult(
                    problem=problem,
                    answer=answer,
                    final_message=msg.content or "",
                    turns=turn,
                    tool_events=tool_events,
                    messages=messages,
                )

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                    result = "Error: invalid JSON arguments"
                else:
                    self._emit(f"[tool] {name}({args})")
                    result = dispatch_tool(name, args)
                tool_events.append(ToolEvent(name=name, arguments=args, result=result))
                self._emit(result[:500])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        # Force a wrap-up turn without tools
        messages.append(
            {
                "role": "user",
                "content": (
                    "Max tool turns reached. Based on the conversation so far, "
                    "give the best final answer now as FINAL_ANSWER: <answer>"
                ),
            }
        )
        response = self.client.chat.completions.create(
            model=self.settings.model,
            temperature=self.settings.temperature,
            messages=messages,
        )
        content = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": content})
        return SolveResult(
            problem=problem,
            answer=extract_final_answer(content),
            final_message=content,
            turns=self.settings.max_turns,
            tool_events=tool_events,
            messages=messages,
        )

    def stream_events(self, problem: str) -> Iterator[str]:
        """Yield human-readable progress events while solving."""
        queue: list[str] = []

        def _on(msg: str) -> None:
            queue.append(msg)

        agent = MathAgent(settings=self.settings, client=self.client, on_event=_on)
        result = agent.solve(problem)
        yield from queue
        yield f"FINAL_ANSWER: {result.answer}"
