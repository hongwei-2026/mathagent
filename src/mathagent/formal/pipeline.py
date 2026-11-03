"""
Low-resource Fields-oriented formal pipeline.

Stack:
  OpenAI formal-math  → statement curriculum + search against a verifier
  DeepSeek-Prover-V2  → NL sketch + Lean `have`/`sorry` subgoal decomposition
  Aristotle           → informal reasoning + lemma formalization + certify

On a laptop we use DeepSeek API as the planner/prover and SymPy/finite checks
as cheap verifiers; Lean is optional hard mode when installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings, get_settings
from mathagent.formal.certify import CertificateResult, certify_subgoal
from mathagent.formal.json_util import extract_json
from mathagent.formal.lean_check import lean_available
from mathagent.formal.memory import LemmaBank, LemmaRecord
from mathagent.formal.prompts import (
    CURRICULUM_SYSTEM,
    FIELDS_GUARDRAIL,
    PLANNER_SYSTEM,
    SUBGOAL_SOLVER_SYSTEM,
)


@dataclass
class SubgoalOutcome:
    subgoal: dict[str, Any]
    solver: dict[str, Any]
    certificate: CertificateResult


@dataclass
class FormalResult:
    problem: str
    plan: dict[str, Any]
    curriculum: dict[str, Any] | None
    outcomes: list[SubgoalOutcome] = field(default_factory=list)
    proved_count: int = 0
    total_subgoals: int = 0
    lean_available: bool = False
    verdict: str = ""
    gaps: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.proved_count / max(self.total_subgoals, 1)


class FormalPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
        on_event: Callable[[str], None] | None = None,
        use_curriculum: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        else:
            if not self.settings.api_key:
                raise ValueError("MATHAGENT_API_KEY missing")
            self.client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
            )
        self.on_event = on_event or (lambda _m: None)
        self.use_curriculum = use_curriculum
        self.bank = LemmaBank()

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        # deepseek-reasoner may put reasoning in reasoning_content; final in content
        model = self.settings.resolved_formal_model
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system + "\n" + FIELDS_GUARDRAIL},
                {"role": "user", "content": user},
            ],
        }
        # temperature only for non-reasoner models
        if "reasoner" not in model.lower():
            kwargs["temperature"] = self.settings.temperature
        self.on_event(f"[model] {model}")
        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        content = msg.content or ""
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            self.on_event(f"[reasoner] {str(reasoning)[:800]}")
        self.on_event(content[:1200])
        return extract_json(content)

    def build_curriculum(self, problem: str) -> dict[str, Any]:
        self.on_event("[formal] building statement curriculum")
        return self._chat_json(
            CURRICULUM_SYSTEM,
            f"Target theorem / problem:\n{problem}",
        )

    def plan(self, problem: str, curriculum: dict[str, Any] | None = None) -> dict[str, Any]:
        self.on_event("[formal] planning + subgoal decomposition")
        related = self.bank.related(problem)
        related_txt = "\n".join(f"- {r.statement}" for r in related) or "(none)"
        curr_txt = json.dumps(curriculum, ensure_ascii=False)[:3000] if curriculum else "{}"
        return self._chat_json(
            PLANNER_SYSTEM,
            (
                f"Problem:\n{problem}\n\n"
                f"Known verified lemmas:\n{related_txt}\n\n"
                f"Curriculum JSON:\n{curr_txt}\n"
            ),
        )

    def solve_subgoal(self, problem: str, subgoal: dict[str, Any], prior: list[SubgoalOutcome]) -> dict[str, Any]:
        prior_txt = "\n".join(
            f"- {o.subgoal.get('id')}: {o.solver.get('result')} [{o.certificate.method} ok={o.certificate.ok}]"
            for o in prior
        ) or "(none)"
        return self._chat_json(
            SUBGOAL_SOLVER_SYSTEM,
            (
                f"Parent problem:\n{problem}\n\n"
                f"Subgoal JSON:\n{json.dumps(subgoal, ensure_ascii=False)}\n\n"
                f"Prior certified results:\n{prior_txt}\n"
            ),
        )

    def run(self, problem: str) -> FormalResult:
        curriculum = self.build_curriculum(problem) if self.use_curriculum else None
        plan = self.plan(problem, curriculum)
        subgoals = list(plan.get("subgoals") or [])
        outcomes: list[SubgoalOutcome] = []
        proved = 0

        for sg in subgoals:
            self.on_event(f"[formal] subgoal {sg.get('id')}: {sg.get('statement', '')[:160]}")
            try:
                solver = self.solve_subgoal(problem, sg, outcomes)
            except Exception as exc:  # noqa: BLE001
                solver = {
                    "status": "failed",
                    "informal_proof": "",
                    "certificate": {"type": "text", "payload": ""},
                    "result": f"solver error: {exc}",
                    "next_hint": "retry with clearer formalization",
                }
            cert = certify_subgoal(sg, solver)
            outcomes.append(SubgoalOutcome(subgoal=sg, solver=solver, certificate=cert))
            if cert.ok:
                proved += 1
                self.bank.add(
                    LemmaRecord.create(
                        statement=str(sg.get("statement", "")),
                        proof_sketch=str(solver.get("informal_proof", "")),
                        certificate_method=cert.method,
                        certificate_detail=cert.detail[:2000],
                        parent_problem=problem[:500],
                    )
                )
            self.on_event(f"[cert] {sg.get('id')} → {cert.method} ok={cert.ok}")

        gaps = [str(r) for r in (plan.get("risks") or [])]
        for o in outcomes:
            if not o.certificate.ok:
                gaps.append(
                    f"{o.subgoal.get('id')}: {o.subgoal.get('statement')} "
                    f"(cert={o.certificate.method})"
                )

        total = len(subgoals)
        if total == 0:
            verdict = "no_subgoals"
        elif proved == total:
            verdict = "all_subgoals_certified"
        elif proved == 0:
            verdict = "unsolved_open_gaps"
        else:
            verdict = "partial_certified"

        # Fields honesty: even full local cert ≠ Fields medal proof
        difficulty = str(plan.get("difficulty", "")).lower()
        if difficulty in {"research", "fields_adjacent"} and verdict == "all_subgoals_certified":
            verdict = "locally_certified_research_sketch"
            gaps.append(
                "Research/Fields-adjacent claims need Lean/mathlib (or journal) review; "
                "local certificates only cover decomposed computational/finite lemmas."
            )

        return FormalResult(
            problem=problem,
            plan=plan,
            curriculum=curriculum,
            outcomes=outcomes,
            proved_count=proved,
            total_subgoals=total,
            lean_available=lean_available(),
            verdict=verdict,
            gaps=gaps,
        )
