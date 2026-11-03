from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from mathagent import __version__
from mathagent.agent import MathAgent
from mathagent.config import get_settings
from mathagent.data.loader import load_benchmark, load_local_samples
from mathagent.eval.grader import math_equal

# Path already imported above for eval/formal outputs


app = typer.Typer(add_completion=False, no_args_is_help=True, help="MathAgent CLI")
console = Console()


@app.command()
def version() -> None:
    """Print version."""
    console.print(f"mathagent {__version__}")


@app.command()
def solve(
    problem: str = typer.Argument(..., help="Math problem text"),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Solve a single math problem with tool-integrated reasoning."""
    agent = MathAgent()
    result = agent.solve(problem)
    if json_out:
        console.print_json(
            data={
                "answer": result.answer,
                "turns": result.turns,
                "tools": [
                    {"name": e.name, "arguments": e.arguments, "result": e.result}
                    for e in result.tool_events
                ],
            }
        )
        return
    console.print(Panel(problem, title="Problem", border_style="cyan"))
    for event in result.tool_events:
        console.print(f"[yellow]→ {event.name}[/yellow] {event.arguments}")
        console.print(event.result[:400])
    console.print(Panel(result.answer or result.final_message, title="Answer", border_style="green"))


@app.command("eval")
def eval_cmd(
    dataset: str = typer.Option("samples", help="samples | gsm8k | math"),
    limit: Optional[int] = typer.Option(5, help="Number of problems"),
    split: str = typer.Option("test", help="HF split"),
    out: Optional[Path] = typer.Option(None, help="Write JSONL predictions"),
) -> None:
    """Evaluate on bundled samples or HuggingFace benchmarks."""
    if dataset == "samples":
        rows = load_local_samples()
        if limit is not None:
            rows = rows[:limit]
    else:
        rows = load_benchmark(dataset, split=split, limit=limit)

    agent = MathAgent()
    correct = 0
    outputs = []
    for i, row in enumerate(rows, 1):
        problem = row["problem"]
        gold = str(row.get("answer", "")).strip()
        console.rule(f"[{i}/{len(rows)}] {row.get('id', i)}")
        result = agent.solve(problem)
        ok = math_equal(result.answer, gold) if gold else False
        correct += int(ok)
        mark = "✓" if ok else "✗"
        console.print(f"{mark} pred={result.answer!r} gold={gold!r}")
        outputs.append(
            {
                "id": row.get("id"),
                "problem": problem,
                "gold": gold,
                "pred": result.answer,
                "correct": ok,
                "turns": result.turns,
            }
        )

    acc = correct / max(len(rows), 1)
    console.print(Panel(f"{correct}/{len(rows)} = {acc:.1%}", title="Accuracy"))
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for row in outputs:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        console.print(f"Wrote {out}")


@app.command()
def formal(
    problem: str = typer.Argument(..., help="Hard theorem / research-style statement"),
    no_curriculum: bool = typer.Option(False, help="Skip statement curriculum step"),
    out: Optional[Path] = typer.Option(None, help="Write full JSON result"),
) -> None:
    """
    Low-resource formal pipeline (OpenAI formal-math + DeepSeek-Prover style).

    Decompose → certify lemmas (SymPy/finite; Lean if installed) → report gaps.
    Honest about Fields-level: local cert ≠ journal-ready proof.
    """
    from mathagent.formal.pipeline import FormalPipeline

    pipe = FormalPipeline(use_curriculum=not no_curriculum, on_event=console.print)
    result = pipe.run(problem)
    console.print(
        Panel(
            f"verdict={result.verdict}\n"
            f"certified={result.proved_count}/{result.total_subgoals}\n"
            f"lean={result.lean_available}\n"
            f"insight={result.plan.get('key_insight', '')}",
            title="Formal result",
            border_style="magenta",
        )
    )
    if result.gaps:
        console.print(Panel("\n".join(f"• {g}" for g in result.gaps[:12]), title="Gaps"))
    if out:
        payload = {
            "problem": result.problem,
            "verdict": result.verdict,
            "proved_count": result.proved_count,
            "total_subgoals": result.total_subgoals,
            "lean_available": result.lean_available,
            "plan": result.plan,
            "curriculum": result.curriculum,
            "gaps": result.gaps,
            "outcomes": [
                {
                    "subgoal": o.subgoal,
                    "solver": o.solver,
                    "certificate": {
                        "ok": o.certificate.ok,
                        "method": o.certificate.method,
                        "detail": o.certificate.detail[:2000],
                    },
                }
                for o in result.outcomes
            ],
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"Wrote {out}")


@app.command()
def lattice(
    problem: str = typer.Argument(..., help="Research / Fields-adjacent problem statement"),
    project: Optional[str] = typer.Option(None, help="Project id for graph persistence"),
    wake_rounds: int = typer.Option(1, help="Wake/sleep cycles"),
    max_wake: int = typer.Option(4, help="Max conjectures attempted per wake"),
    concept_value: bool = typer.Option(
        False, "--concept-value", help="A→E loop: abduction/concepts/analogy/curator/human-gate"
    ),
    auto_accept: bool = typer.Option(
        False, "--auto-accept", help="Smoke only: auto-ACCEPT concepts (skips human co-abduction)"
    ),
    out: Optional[Path] = typer.Option(None, help="Write JSON result"),
) -> None:
    """
    MathLattice: conjecture pool → research graph → wake/sleep (Fields-oriented architecture).

    With --concept-value: abduction → Concept slots → analogy maps → curator rank →
    human gate queue → wake prefers concept-linked cheap leaves.

    Does NOT claim Fields proofs. Builds certified lemmas + explicit gaps on a laptop budget.
    See docs/LATTICE_ARCHITECTURE.md.
    """
    from mathagent.formal.budget import Budget
    from mathagent.lattice.pipeline import LatticePipeline

    pipe = LatticePipeline(
        budget=Budget(max_tokens=14000, max_llm_calls=18, max_direct_samples=2),
        wake_rounds=wake_rounds,
        max_wake_nodes=max_wake,
        concept_value=concept_value,
        auto_accept_concepts=auto_accept,
        on_event=console.print,
    )
    result = pipe.run(problem, project_id=project)
    console.print(
        Panel(
            f"mode={result.mode}\n"
            f"verdict={result.verdict}\n"
            f"difficulty={result.difficulty}\n"
            f"insight={result.key_insight}\n"
            f"graph={result.graph_summary}\n"
            f"lemmas={len(result.certified_lemmas)} gaps={len(result.gaps)} "
            f"concepts={len(result.concepts)}\n"
            f"human_review={result.human_review_queue}\n"
            f"saved={result.graph_path}",
            title="MathLattice",
            border_style="magenta",
        )
    )
    if result.concepts:
        lines = []
        for c in result.concepts[:6]:
            v = (c.get("scores") or {}).get("conceptual_value")
            lines.append(f"• [{c['status']}] {c.get('name')}: V={v} — {c['statement'][:100]}")
        console.print(Panel("\n".join(lines), title="Concepts"))
    if result.certified_lemmas:
        console.print(Panel("\n".join(f"• {x}" for x in result.certified_lemmas[:8]), title="Certified"))
    if result.gaps:
        console.print(Panel("\n".join(f"• {x}" for x in result.gaps[:8]), title="Gaps (honest)"))
    if out:
        payload = {
            "project_id": result.project_id,
            "mode": result.mode,
            "problem": result.problem,
            "verdict": result.verdict,
            "difficulty": result.difficulty,
            "key_insight": result.key_insight,
            "graph_summary": result.graph_summary,
            "concepts": result.concepts,
            "curator": result.curator,
            "human_review_queue": result.human_review_queue,
            "certified_lemmas": result.certified_lemmas,
            "gaps": result.gaps,
            "sleep": result.sleep,
            "wake": [
                {"node_id": w.node_id, "ok": w.ok, "method": w.method, "detail": w.detail[:500]}
                for w in result.wake_outcomes
            ],
            "graph_path": result.graph_path,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"Wrote {out}")


@app.command("lattice-gate")
def lattice_gate(
    project: str = typer.Argument(..., help="Project id (graph file under data/lattice)"),
    concept_id: str = typer.Argument(..., help="Concept node id"),
    action: str = typer.Argument(..., help="accept | reject"),
    note: str = typer.Option("", help="Human co-abduction note"),
) -> None:
    """Accept or reject a Concept after human co-abduction review."""
    from mathagent.lattice.graph import GraphStore, NodeKind, NodeStatus

    store = GraphStore()
    graph = store.load(project)
    if graph is None:
        console.print(f"[red]No graph for project={project}[/red]")
        raise typer.Exit(1)
    node = graph.nodes.get(concept_id)
    if node is None or node.kind != NodeKind.CONCEPT:
        console.print(f"[red]Not a concept: {concept_id}[/red]")
        raise typer.Exit(1)
    act = action.strip().lower()
    if act == "accept":
        node.status = NodeStatus.ACCEPTED
    elif act == "reject":
        node.status = NodeStatus.REJECTED
    else:
        console.print("[red]action must be accept|reject[/red]")
        raise typer.Exit(1)
    gate = dict(node.meta.get("human_gate") or {})
    gate["required"] = False
    gate["notes"] = note
    gate["decision"] = act
    node.meta["human_gate"] = gate
    path = store.save(graph)
    console.print(f"{act} {concept_id} → {path}")


@app.command()
def econ(
    problem: str = typer.Argument(..., help="Lean theorem or informal hard goal"),
    max_tokens: int = typer.Option(12000, help="Soft token budget"),
    max_repair: int = typer.Option(2, help="Lean repair attempts per sample"),
    max_samples: int = typer.Option(3, help="Cheap direct samples before decompose"),
    local: bool = typer.Option(False, "--local", help="Prefer local Ollama prover (D: models)"),
    out: Optional[Path] = typer.Option(None, help="Write JSON result"),
) -> None:
    """
    Low-cost proving path (EconProver + Seed-light + DeepSeek-Prover style).

    Cheap model first → Lean repair → decompose → escalate CoT only if needed.
    See docs/LOW_COST_PATH.md.
    """
    from mathagent.config import Settings, reload_settings
    from mathagent.formal.budget import Budget
    from mathagent.formal.econ import EconEngine
    from mathagent.local_llm import probe_ollama
    from openai import OpenAI

    settings = reload_settings()
    client = None
    if local:
        st = probe_ollama()
        if not st.available or not st.preferred:
            console.print(f"[red]Local Ollama unavailable:[/red] {st.detail}")
            console.print("Install Ollama, set OLLAMA_MODELS=D:\\models\\ollama, pull DeepSeek-Prover-V2-7B GGUF.")
            raise typer.Exit(1)
        console.print(f"[cyan]local[/cyan] {st.preferred} @ {st.base_url}")
        settings = Settings(
            api_key=os.environ.get("MATHAGENT_API_KEY", "ollama"),
            base_url=st.base_url,
            model=st.preferred,
            formal_model=st.preferred,
            lean_home=settings.lean_home,
            lean_workspace=settings.lean_workspace,
        )
        client = OpenAI(api_key="ollama", base_url=st.base_url)

    budget = Budget(
        max_tokens=max_tokens,
        max_repair=max_repair,
        max_direct_samples=max_samples,
    )
    engine = EconEngine(settings=settings, client=client, budget=budget, on_event=console.print)
    result = engine.run(problem)
    style = "green" if result.ok else "yellow"
    console.print(
        Panel(
            f"verdict={result.verdict}\nok={result.ok}\nescalated={result.escalated}\n"
            f"calls={result.budget.used_calls if result.budget else '?'} "
            f"tok≈{result.budget.used_tokens if result.budget else '?'}\n\n"
            f"{result.final_code[:1200]}",
            title="Econ result",
            border_style=style,
        )
    )
    if out:
        payload = {
            "problem": result.problem,
            "ok": result.ok,
            "verdict": result.verdict,
            "escalated": result.escalated,
            "final_code": result.final_code,
            "budget": {
                "used_calls": result.budget.used_calls if result.budget else 0,
                "used_tokens": result.budget.used_tokens if result.budget else 0,
                "log": result.budget.log if result.budget else [],
            },
            "steps": [
                {"phase": s.phase, "ok": s.ok, "detail": s.detail, "code": s.code[:2000]}
                for s in result.steps
            ],
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"Wrote {out}")


@app.command("lean-check")
def lean_check_cmd(
    file: Optional[Path] = typer.Option(None, help="Lean file (default: workspace Scratch.lean)"),
    code: Optional[str] = typer.Option(None, help="Inline Lean snippet"),
) -> None:
    """Typecheck a Lean snippet using the D: workspace (local, no cloud)."""
    from mathagent.formal.lean_check import check_lean_snippet, lean_available
    from mathagent.formal.lean_env import lean_elan_home, lean_workspace

    console.print(
        {
            "elan_home": str(lean_elan_home()),
            "workspace": str(lean_workspace()),
            "lean_available": lean_available(),
        }
    )
    if code:
        src = code
    elif file:
        src = file.read_text(encoding="utf-8")
    else:
        scratch = lean_workspace() / "Scratch.lean"
        src = scratch.read_text(encoding="utf-8") if scratch.exists() else "theorem t : True := trivial"
    result = check_lean_snippet(src)
    style = "green" if result.ok else "red"
    console.print(Panel(f"ok={result.ok}\n{result.stderr or result.stdout}", title="Lean check", border_style=style))


@app.command()
def doctor() -> None:
    """Show resolved settings (secrets redacted)."""
    from mathagent.formal.lean_check import lean_available
    from mathagent.formal.lean_env import lean_elan_home, lean_workspace

    s = get_settings()
    key = s.api_key
    redacted = (key[:4] + "…" + key[-4:]) if len(key) > 8 else ("(empty)" if not key else "****")
    from mathagent.local_llm import probe_ollama

    local = probe_ollama()
    console.print(
        {
            "model": s.model,
            "formal_model": s.resolved_formal_model,
            "base_url": s.base_url,
            "api_key": redacted,
            "max_turns": s.max_turns,
            "temperature": s.temperature,
            "lean_home": str(lean_elan_home()),
            "lean_workspace": str(lean_workspace()),
            "lean_available": lean_available(),
            "c_user_elan_exists": Path.home().joinpath(".elan").exists(),
            "ollama_available": local.available,
            "ollama_model": local.preferred,
            "ollama_detail": local.detail,
            "mathlib_workspace_exists": Path("D:/mathagent/lean_mathlib").exists(),
        }
    )


if __name__ == "__main__":
    app()
