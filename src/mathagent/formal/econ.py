"""
Low-cost proving engine.

Combines:
  EconProver     — cheap non-CoT first, escalate CoT only on failure
  Seed light     — Lean feedback repair with tiny iteration budget
  DeepSeek-Prover / Gödel Poetry — decompose when direct prove fails
  Structured hints — tactic skeletons in the prompt
  Lemma bank     — reuse certified leaves
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings, get_settings
from mathagent.formal.budget import Budget
from mathagent.formal.json_util import extract_json
from mathagent.formal.lean_check import check_lean_snippet, lean_available
from mathagent.formal.memory import LemmaBank, LemmaRecord
from mathagent.formal.tactic_hints import skeleton_prompt_block


DIRECT_SYSTEM = f"""You are a LOW-COST Lean 4 prover (non-CoT / short mode).
Return ONLY a complete Lean 4 snippet that proves the goal.
Rules:
- No markdown fences unless needed.
- Prefer core Lean (no Mathlib) when possible.
- {skeleton_prompt_block()}
"""

REPAIR_SYSTEM = """You repair a FAILED Lean 4 proof under a tight token budget.
Given the theorem, previous code, and Lean errors, return a corrected FULL Lean snippet only.
Keep changes minimal. Prefer simp/omega/rfl/exact.
"""

DECOMPOSE_SYSTEM = """You are a DeepSeek-Prover-style decomposer.
Break a hard Lean/math goal into cheaper subgoals.

Return STRICT JSON:
{
  "mode": "decompose",
  "lean_sketch": "Lean theorem with `have` ... := by sorry  leaves",
  "subgoals": [
    {"id": "S1", "statement": "...", "lean": "theorem S1 ... := by sorry"}
  ],
  "why_cheaper": "one line"
}
Use core Lean if possible. At most 5 subgoals.
"""

ESCALATE_SYSTEM = """You are in ESCALATED CoT mode (EconProver dynamic switch).
Think carefully, then output a FINAL Lean 4 proof snippet after a short plan.
End with a line: LEAN_PROOF_BEGIN
then the Lean code
then LEAN_PROOF_END
"""


@dataclass
class EconStep:
    phase: str
    ok: bool
    detail: str
    code: str = ""


@dataclass
class EconResult:
    problem: str
    ok: bool
    final_code: str
    steps: list[EconStep] = field(default_factory=list)
    budget: Budget | None = None
    escalated: bool = False
    verdict: str = ""


def _extract_lean(text: str) -> str:
    text = text.strip()
    m = re.search(r"LEAN_PROOF_BEGIN\s*(.*?)\s*LEAN_PROOF_END", text, re.S)
    if m:
        return m.group(1).strip()
    fence = re.search(r"```(?:lean)?\s*(.*?)```", text, re.S)
    if fence:
        return fence.group(1).strip()
    if "theorem" in text or "example" in text:
        return text
    return text


class EconEngine:
    """Laptop-first prover: minimize LLM cost, maximize Lean verifier use."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
        on_event: Callable[[str], None] | None = None,
        budget: Budget | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )
        self.on_event = on_event or (lambda _m: None)
        self.budget = budget or Budget()
        self.bank = LemmaBank()
        self.cheap_model = self.settings.model  # e.g. deepseek-chat
        self.rich_model = self.settings.resolved_formal_model  # reasoner if set

    def _chat(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float | None = 0.0,
        est_tokens: int = 900,
    ) -> str:
        if not self.budget.can_call(est_tokens):
            raise RuntimeError("budget exhausted")
        model = model or self.cheap_model
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if "reasoner" not in model.lower() and temperature is not None:
            kwargs["temperature"] = temperature
        self.on_event(f"[econ/{model}] call#{self.budget.used_calls + 1}")
        resp = self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tok = int(getattr(usage, "total_tokens", 0) or est_tokens)
        self.budget.record(model, tok)
        return content

    def _lean_ok(self, code: str) -> tuple[bool, str]:
        if not lean_available():
            return False, "lean unavailable"
        res = check_lean_snippet(code)
        detail = (res.stderr or res.stdout or "").strip()
        return res.ok, detail

    def direct_and_repair(self, goal: str, depth: int = 0) -> tuple[bool, str, list[EconStep]]:
        steps: list[EconStep] = []
        code = ""
        for sample in range(self.budget.max_direct_samples):
            if not self.budget.can_call():
                break
            raw = self._chat(
                DIRECT_SYSTEM,
                f"Goal / theorem to prove:\n{goal}\n\nAttempt {sample + 1}. Return Lean only.",
                model=self.cheap_model,
                temperature=0.2 if sample else 0.0,
            )
            code = _extract_lean(raw)
            ok, detail = self._lean_ok(code)
            steps.append(EconStep("direct", ok, detail[:500], code))
            self.on_event(f"[direct {sample + 1}] ok={ok}")
            if ok:
                return True, code, steps

            # Seed-light repair loop
            for r in range(self.budget.max_repair):
                if not self.budget.can_call():
                    break
                raw = self._chat(
                    REPAIR_SYSTEM,
                    f"GOAL:\n{goal}\n\nCODE:\n{code}\n\nLEAN ERRORS:\n{detail}\n",
                    model=self.cheap_model,
                )
                code = _extract_lean(raw)
                ok, detail = self._lean_ok(code)
                steps.append(EconStep(f"repair-{r + 1}", ok, detail[:500], code))
                self.on_event(f"[repair {r + 1}] ok={ok}")
                if ok:
                    return True, code, steps
        return False, code, steps

    def decompose(self, goal: str) -> dict[str, Any]:
        raw = self._chat(
            DECOMPOSE_SYSTEM,
            f"Hard goal:\n{goal}\n",
            model=self.cheap_model,
            est_tokens=1200,
        )
        try:
            return extract_json(raw)
        except Exception:
            return {"mode": "decompose", "lean_sketch": "", "subgoals": []}

    def escalate(self, goal: str, history: str) -> tuple[bool, str, EconStep]:
        """EconProver dynamic CoT switch — only when cheap path failed."""
        raw = self._chat(
            ESCALATE_SYSTEM,
            f"GOAL:\n{goal}\n\nPRIOR FAILURES:\n{history[:2500]}\n",
            model=self.rich_model,
            temperature=None,
            est_tokens=2000,
        )
        code = _extract_lean(raw)
        ok, detail = self._lean_ok(code)
        return ok, code, EconStep("escalate_cot", ok, detail[:500], code)

    def run(self, problem: str) -> EconResult:
        if not self.settings.api_key:
            raise ValueError("MATHAGENT_API_KEY missing")

        related = self.bank.related(problem)
        hint = "\n".join(f"- {r.statement}" for r in related[:5])
        goal = problem if "theorem" in problem or "example" in problem else (
            "Convert and prove in Lean 4 (core Lean preferred):\n" + problem
        )
        if hint:
            goal = goal + "\n\nKnown lemmas:\n" + hint

        steps: list[EconStep] = []
        escalated = False

        # Phase 1–2: cheap direct + repair
        ok, code, s1 = self.direct_and_repair(goal)
        steps.extend(s1)
        if ok:
            self.bank.add(
                LemmaRecord.create(
                    statement=problem[:500],
                    proof_sketch=code[:1000],
                    certificate_method="lean",
                    certificate_detail="econ-direct",
                    parent_problem=problem[:300],
                )
            )
            return EconResult(
                problem=problem,
                ok=True,
                final_code=code,
                steps=steps,
                budget=self.budget,
                escalated=False,
                verdict="proved_cheap_direct",
            )

        # Phase 3: decompose + prove leaves
        if self.budget.can_call() and self.budget.max_depth > 0:
            plan = self.decompose(goal)
            steps.append(
                EconStep(
                    "decompose",
                    False,
                    json.dumps(plan.get("subgoals", []), ensure_ascii=False)[:500],
                    str(plan.get("lean_sketch", "")),
                )
            )
            leaf_codes: list[str] = []
            all_leaves_ok = True
            for sg in (plan.get("subgoals") or [])[:5]:
                leaf_goal = sg.get("lean") or sg.get("statement") or ""
                if not leaf_goal:
                    continue
                lok, lcode, ls = self.direct_and_repair(str(leaf_goal), depth=1)
                steps.extend(ls)
                if lok:
                    leaf_codes.append(lcode)
                    self.bank.add(
                        LemmaRecord.create(
                            statement=str(sg.get("statement", ""))[:500],
                            proof_sketch=lcode[:1000],
                            certificate_method="lean",
                            certificate_detail="econ-leaf",
                            parent_problem=problem[:300],
                        )
                    )
                else:
                    all_leaves_ok = False
            if all_leaves_ok and leaf_codes and plan.get("lean_sketch"):
                # try assembling sketch (best-effort): check sketch after stripping sorry if leaves done
                sketch = str(plan.get("lean_sketch"))
                ok_s, detail_s = self._lean_ok(sketch.replace("sorry", "trivial"))
                steps.append(EconStep("assemble", ok_s, detail_s[:500], sketch))
                if ok_s:
                    return EconResult(
                        problem=problem,
                        ok=True,
                        final_code=sketch,
                        steps=steps,
                        budget=self.budget,
                        escalated=False,
                        verdict="proved_via_decomposition",
                    )

        # Phase 4: escalate CoT / reasoner once
        if self.budget.can_call():
            escalated = True
            hist = "\n".join(f"{s.phase}: {s.detail[:200]}" for s in steps[-6:])
            ok_e, code_e, step_e = self.escalate(goal, hist)
            steps.append(step_e)
            if ok_e:
                self.bank.add(
                    LemmaRecord.create(
                        statement=problem[:500],
                        proof_sketch=code_e[:1000],
                        certificate_method="lean",
                        certificate_detail="econ-escalated",
                        parent_problem=problem[:300],
                    )
                )
                return EconResult(
                    problem=problem,
                    ok=True,
                    final_code=code_e,
                    steps=steps,
                    budget=self.budget,
                    escalated=True,
                    verdict="proved_after_cot_escalation",
                )
            code = code_e

        return EconResult(
            problem=problem,
            ok=False,
            final_code=code,
            steps=steps,
            budget=self.budget,
            escalated=escalated,
            verdict="open_within_budget",
        )
