"""
MathLattice pipeline — Fields-oriented research architecture on a laptop budget.

Conjecture pool → typed graph → wake (econ/certify) → sleep (abstract) → curator stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from openai import OpenAI

from mathagent.config import Settings, get_settings
from mathagent.formal.budget import Budget
from mathagent.formal.econ import EconEngine
from mathagent.lattice.conjecture import generate_conjecture_pool
from mathagent.lattice.graph import GraphStore, Node, NodeKind, NodeStatus, ResearchGraph
from mathagent.lattice.sleep import sleep_consolidate
from mathagent.lattice.wake import WakeOutcome, wake_attempt


@dataclass
class LatticeResult:
    project_id: str
    problem: str
    difficulty: str
    key_insight: str
    graph_summary: dict[str, int]
    wake_outcomes: list[WakeOutcome] = field(default_factory=list)
    sleep: dict[str, Any] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    certified_lemmas: list[str] = field(default_factory=list)
    verdict: str = ""
    graph_path: str = ""
    budget: Budget | None = None


def _project_id(problem: str) -> str:
    slug = re.sub(r"\W+", "_", problem.strip().lower())[:48].strip("_")
    return slug or "research"


class LatticePipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAI | None = None,
        on_event: Callable[[str], None] | None = None,
        budget: Budget | None = None,
        wake_rounds: int = 1,
        max_wake_nodes: int = 5,
    ) -> None:
        self.settings = settings or get_settings()
        if not self.settings.api_key:
            raise ValueError("MATHAGENT_API_KEY missing")
        self.client = client or OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
        )
        self.on_event = on_event or (lambda _m: None)
        self.budget = budget or Budget(max_tokens=16_000, max_llm_calls=20, max_direct_samples=2)
        self.wake_rounds = wake_rounds
        self.max_wake_nodes = max_wake_nodes
        self.store = GraphStore()

    def run(self, problem: str, project_id: str | None = None) -> LatticeResult:
        pid = project_id or _project_id(problem)
        graph = self.store.load(pid) or ResearchGraph(project_id=pid)

        # --- Conjecture phase ---
        pool = generate_conjecture_pool(
            problem, client=self.client, settings=self.settings, on_event=self.on_event
        )
        target = graph.add(
            Node.new(NodeKind.TARGET, str(pool.get("target") or problem), difficulty=pool.get("difficulty"))
        )
        plan = graph.add(Node.new(NodeKind.PLAN, str(pool.get("plan") or ""), insight=pool.get("key_insight")))
        graph.link(plan.id, target.id, "plans")

        for c in pool.get("conjectures") or []:
            node = Node.new(
                NodeKind.CONJECTURE,
                str(c.get("statement", "")),
                role=c.get("role"),
                certify_hint=c.get("certify_hint"),
                lean_stub=c.get("lean_stub"),
                sympy_hint=c.get("sympy_hint"),
            )
            node.score = float(c.get("score") or 0.5)
            graph.add(node)
            graph.link(target.id, node.id, "depends")

        for g in pool.get("gaps") or []:
            graph.add_gap(str(g.get("statement", "")), parent_id=target.id, reason=str(g.get("reason", "")))

        # --- Wake / Sleep rounds ---
        econ = EconEngine(
            settings=self.settings,
            client=self.client,
            on_event=self.on_event,
            budget=self.budget,
        )
        outcomes: list[WakeOutcome] = []
        sleep_data: dict[str, Any] = {}

        for rnd in range(self.wake_rounds):
            self.on_event(f"[lattice] wake round {rnd + 1}/{self.wake_rounds}")
            frontier = [
                n
                for n in graph.frontier(limit=self.max_wake_nodes)
                if n.kind == NodeKind.CONJECTURE and n.status == NodeStatus.OPEN
            ]
            if not frontier:
                break
            for node in frontier:
                if self.budget.exhausted:
                    break
                outcomes.append(
                    wake_attempt(
                        graph, node, econ=econ, budget=self.budget, on_event=self.on_event
                    )
                )
            sleep_data = sleep_consolidate(
                graph, client=self.client, settings=self.settings, on_event=self.on_event
            )

        path = self.store.save(graph)
        lemmas = [n.statement for n in graph.by_kind(NodeKind.LEMMA) if n.status == NodeStatus.CERTIFIED]
        gaps = [n.statement for n in graph.by_kind(NodeKind.GAP)]
        difficulty = str(pool.get("difficulty") or "research")

        if lemmas and not gaps:
            verdict = "locally_closed_sketch"
        elif lemmas:
            verdict = "partial_theory_progress"
        else:
            verdict = "mapped_open_landscape"

        if difficulty in {"fields_adjacent", "open"}:
            verdict = f"{verdict}+honest_open_gaps"

        return LatticeResult(
            project_id=pid,
            problem=problem,
            difficulty=difficulty,
            key_insight=str(pool.get("key_insight") or ""),
            graph_summary=graph.summary(),
            wake_outcomes=outcomes,
            sleep=sleep_data,
            gaps=gaps,
            certified_lemmas=lemmas,
            verdict=verdict,
            graph_path=str(path),
            budget=self.budget,
        )
