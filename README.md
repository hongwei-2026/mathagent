# MathAgent

Tool-integrated **AI agent for mathematical reasoning** — built on proven open research, then optimized for practical use.

| Inspiration | What we reuse |
|---|---|
| [**ToRA**](https://github.com/microsoft/ToRA) (Microsoft, ICLR'24) | Interleaved rationale + program/tool use; MATH-style grader |
| [**MathChat**](https://arxiv.org/abs/2306.01337) | Multi-turn agent ↔ tool feedback loop |
| [**Neuro-Symbolic Math Solver**](https://github.com/dbogdanm/Neuro-Symbolic-Math-Solver) | SymPy as deterministic executor + self-correction |
| **GSM8K / MATH** | Standard benchmarks via HuggingFace `datasets` |

## Architecture

```
User problem
    │
    ▼
┌─────────────────────┐
│  LLM (any OpenAI-   │  rationale / plan
│  compatible API)    │
└─────────┬───────────┘
          │ tool calls
          ▼
┌─────────────────────┐
│  Tool layer         │  run_python │ sympy_* │ calculator
│  (sandboxed)        │
└─────────┬───────────┘
          │ observations
          ▼
   self-correct ≤ N turns → FINAL_ANSWER
          │
          ▼
   MATH/ToRA grader (eval)
```

### Optimizations vs. vanilla baselines

1. **Multi-provider LLM** — OpenAI, DeepSeek, Ollama, vLLM via `MATHAGENT_BASE_URL`
2. **Fast path** — pure arithmetic skips the LLM and goes straight to SymPy
3. **Restricted sandbox** — AST-gated Python + process timeout (safer than bare `exec`)
4. **Self-correction** — tool errors are fed back into the chat (MathChat / DotaMath style)
5. **Bundled samples + HF download** — start offline; scale to GSM8K/MATH when ready
6. **CLI + Streamlit UI** — one package for scripted eval and interactive demos

## Low-cost doctrine (beat “many agents × huge compute”)

OpenAI-style IMO runs burn proprietary RL + massive test-time compute (often NL, no Lean).
Open research shows a **cheaper axis** that we implement as `mathagent econ`:

1. **Cheap model first** (non-CoT) — EconProver dynamic CoT  
2. **Lean repair ×2** — Seed-Prover light (not Pass@8192)  
3. **Decompose `have`/`sorry`** — DeepSeek-Prover / Gödel’s Poetry  
4. **Escalate reasoner only if still open** — pay tokens only on failures  
5. **4B-class provers can beat 671B** on miniF2F when trained right (Pythagoras) — architecture > brute force  

Details: [docs/LOW_COST_PATH.md](docs/LOW_COST_PATH.md)

```bash
mathagent econ "theorem add_comm (a b : Nat) : a + b = b + a := by" --out outputs/econ.json
```

## Formal / Fields-oriented mode (low resource)

Goal: push toward **olympiad → research-shaped** problems on a laptop by copying the
*architecture* of frontier systems, not their GPU clusters.

| System | Idea we reuse |
|---|---|
| [OpenAI formal-math](https://openai.com/index/formal-math/) | Statement curriculum learning + search against a verifier |
| [DeepSeek-Prover-V2](https://github.com/deepseek-ai/DeepSeek-Prover-V2) | NL sketch → Lean `have`/`sorry` subgoals → recursive certify |
| Aristotle (IMO'25 formal) | Informal reasoning + lemma autoformalization + hard check |

```text
hard problem
   │
   ├─ statement curriculum (easier → harder)
   ├─ informal sketch + key insight
   ├─ subgoal list (Lean stubs + SymPy hints)
   │     └─ certify each: SymPy / finite Python / Lean(optional)
   └─ lemma bank memory  →  reuse on next harder problem
```

```bash
# DeepSeek reasoner plans; SymPy certifies cheap lemmas
mathagent formal "Prove AM-GM: (x+y)/2 >= sqrt(xy) for x,y>0" --out outputs/amgm.json

# Research/open problems: expect verdict=partial + explicit gaps (honest)
mathagent formal "Twin prime conjecture: produce curriculum + mark the open gap"
```

### Lean 4 on D: (local, no cloud)

Lean runs **fully offline/local**. Cloud is optional. This repo pins everything to D:

| Path | Purpose |
|---|---|
| `D:\lean\elan` | `ELAN_HOME` + toolchains |
| `D:\lean\cache` / `D:\lean\tmp` | caches & temp |
| `D:\mathagent\lean_workspace` | lake project for agent sketches |

```powershell
# one-time env (already set by installer)
$env:ELAN_HOME='D:\lean\elan'
$env:Path = "D:\lean\elan\bin;$env:Path"

mathagent lean-check --code "theorem t : True := trivial"
mathagent formal "Prove Nat.add_comm" --out outputs/formal.json
```

Mathlib is optional and large; core Lean is enough for many algebraic kernels. Add mathlib later inside `lean_workspace` if needed.

> **Honesty:** Fields Medal mathematics is not “solved by an API call”. This pipeline
> maximizes what a **low-resource** stack can *certify* and clearly isolates remaining gaps.

## Quick start

```bash
# 1) install
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 2) configure
copy .env.example .env   # then edit MATHAGENT_API_KEY / MODEL / BASE_URL

# 3) solve one problem (tool agent)
mathagent solve "Solve 2x+5=17"

# 4) formal pipeline (Fields-oriented decomposition)
mathagent formal "Prove that there are infinitely many primes."

# 5) offline tool smoke test (no API key)
python scripts/smoke_tools.py

# 6) evaluate bundled samples
mathagent eval --dataset samples --limit 5

# 7) UI
streamlit run src/mathagent/ui_app.py
```

### DeepSeek / Ollama examples

```env
# DeepSeek (recommended for this repo)
MATHAGENT_API_KEY=sk-...
MATHAGENT_BASE_URL=https://api.deepseek.com
MATHAGENT_MODEL=deepseek-chat
MATHAGENT_FORMAL_MODEL=deepseek-reasoner

# Ollama
MATHAGENT_API_KEY=ollama
MATHAGENT_BASE_URL=http://127.0.0.1:11434/v1
MATHAGENT_MODEL=qwen2.5:14b
```

## Data

| Path | Description |
|---|---|
| `data/samples/problems.jsonl` | 15 curated problems (arith / algebra / calc / word) |
| `python scripts/download_data.py --dataset gsm8k` | Pull GSM8K test set |
| `python scripts/download_data.py --dataset math` | Pull MATH (HF mirror) |

```bash
mathagent eval --dataset gsm8k --limit 20 --out outputs/gsm8k_pred.jsonl
```

## Project layout

```
src/mathagent/
  agent.py          # ToRA-style tool loop
  prompts.py        # system / solve prompts
  tools/            # sandbox + SymPy registry
  eval/grader.py    # ToRA/MATH equivalence
  data/loader.py    # samples + HF benchmarks
  cli.py            # typer CLI
  ui_app.py         # Streamlit
```

## Citation

If you use this stack in research, please cite the upstream work:

```bibtex
@inproceedings{gou2024tora,
  title={ToRA: A Tool-Integrated Reasoning Agent for Mathematical Problem Solving},
  author={Gou, Zhibin and Shao, Zhihong and Gong, Yeyun and Shen, Yelong and Yang, Yujiu and Huang, Minlie and Duan, Nan and Chen, Weizhu},
  booktitle={ICLR},
  year={2024}
}
```

## License

MIT — see [LICENSE](LICENSE). Grader logic adapted from ToRA / Hendrycks MATH (MIT).
