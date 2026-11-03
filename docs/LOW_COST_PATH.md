# Low-Cost Path vs OpenAI-Scale Math Agents

**Question:** Can open models + tiny compute approach what OpenAI does with huge agent/compute budgets?

**Answer:** Yes for *formal* math — if you copy the *efficient* open research stack, **not** OpenAI’s IMO NL-only mega-RL recipe.

## What OpenAI actually did (IMO 2025)

- Natural-language proofs, **no Lean** in the contest run.
- General-purpose RL + curated math data; undisclosed (likely very large) test-time compute.
- Explicitly declined Lean/formal IMO track.
- Not a reproducible “laptop recipe”.

Copying “many agents + lots of tokens” is the expensive path. Frontier open work shows a cheaper axis: **verifier + decomposition + selective CoT**.

## Transferable recipes (learn these)

| Paper / system | Trick | Cost win |
|---|---|---|
| **DeepSeek-Prover-V2** | Big model plans `have`/`sorry` subgoals; **7B** closes them | Keep expensive model for planning only |
| **EconProver** (ACL 2026) | Dynamic CoT: hard problems get CoT, easy get non-CoT | **~12%** compute for same accuracy |
| **Pythagoras-Prover-4B** | Curriculum SFT + ALF data aug | **4B > 671B** on miniF2F pass@32 |
| **Prover Agent** | Small LM + agent loop, sample budget ~260 | 88% miniF2F-class with tiny sampling |
| **Gödel’s Poetry / Goedel-Code-Prover** | Direct prove → Lean repair → recursive decompose → reconstruct | Avoid Pass@8192 |
| **Seed-Prover (light)** | Lean feedback refine ×8–16 instead of Pass@8192 | Hours → minutes for many IMO-lite |
| **Structured tactic hints** | Fixed tactic skeletons in prompt | +43% relative @ same k=16 |
| **OpenAI formal-math (2022)** | Statement curriculum learning | Free curriculum without self-play |

## MathAgent’s low-cost doctrine

```
cheap_model (deepseek-chat / local 4–8B)
    │
    ├─1─ direct Lean proof (non-CoT, k≤4)
    │       └─ Lean error → repair ≤2   [Seed light / Prover Agent]
    ├─2─ if fail: decompose have/sorry  [DeepSeek-Prover / Gödel Poetry]
    │       └─ recurse leaves with budget
    ├─3─ escalate CoT/reasoner ONLY if still open  [EconProver]
    └─4─ SymPy/finite certify algebraic leaves     [neuro-symbolic]
         + lemma bank reuse                        [Seed 1.5 cache]
```

**Do**
- Spend tokens on *failed* hard goals, not every easy lemma.
- Treat Lean as the reward model (free, local, on D:).
- Prefer one planner + many cheap leaf proofs over a swarm of heavy agents.

**Don’t**
- Mirror OpenAI’s “general agent × huge wall-clock” without a verifier.
- Always call `deepseek-reasoner` / long CoT.
- Download mathlib until a leaf actually needs it.

## Honesty bound

- Formal olympiad (miniF2F / Putnam-lite): **tractable** on low budget with the stack above.
- OpenAI IMO-gold *natural language* style: still proprietary-scale.
- Fields-level research: architecture helps; new theory still needs humans + long search.

## CLI

```bash
mathagent econ "theorem add_comm (a b : Nat) : a + b = b + a := by"
mathagent econ --budget-tokens 8000 --max-repair 2 "Prove AM-GM algebraically"
```
