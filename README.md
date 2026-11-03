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

## Quick start

```bash
# 1) install
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 2) configure
copy .env.example .env   # then edit MATHAGENT_API_KEY / MODEL / BASE_URL

# 3) solve one problem
mathagent solve "Solve 2x+5=17"

# 4) offline tool smoke test (no API key)
python scripts/smoke_tools.py

# 5) evaluate bundled samples
mathagent eval --dataset samples --limit 5

# 6) UI
streamlit run src/mathagent/ui_app.py
```

### DeepSeek / Ollama examples

```env
# DeepSeek
MATHAGENT_API_KEY=sk-...
MATHAGENT_BASE_URL=https://api.deepseek.com/v1
MATHAGENT_MODEL=deepseek-chat

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
