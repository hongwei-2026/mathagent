<div align="center">

# MathAgent: Low-Resource AI for Mathematical Research Reasoning

**Towards Lattice · Think · Formal — conceptual math agents under laptop budgets.**

<img src="docs/assets/mathagent-banner.png" alt="MathAgent banner" width="720"/>

<br/>

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](docs/README.md)
[![tests](https://img.shields.io/badge/tests-pytest-orange.svg)](tests/)
[![lean](https://img.shields.io/badge/Lean-4%20local-purple.svg)](docs/TRY_LOCAL_AND_MATHLIB.md)
[![github](https://img.shields.io/badge/GitHub-mathagent-181717.svg)](https://github.com/hongwei-2026/mathagent)

📖 [English](README_en.md) | [中文](README.md)

</div>

**MathAgent** is a low-resource open stack for mathematical reasoning: a contest-style **tool agent (ToRA / MathChat)**, **Formal / Econ** cheap certification, research-oriented **MathLattice** graph memory, and **Think pillars** that push toward conceptual cognition (executable library · hypothesis arena · cross-run evidence). It leans on **SymPy / Lean / DeepSeek-compatible APIs** and refuses to treat unverified narrative as proof.

> **Honesty:** Fields-level results are not “one API call.” This repo maximizes *certifiable progress* and records open gaps as explicit `Gap` / `HUMAN_REVIEW` nodes.

---

## Docs

| Doc | Topic |
|-----|--------|
| [docs/README.md](docs/README.md) | Reading order |
| [docs/LOW_COST_PATH.md](docs/LOW_COST_PATH.md) | Econ / selective CoT |
| [docs/LATTICE_ARCHITECTURE.md](docs/LATTICE_ARCHITECTURE.md) | Research graph, A→E, MDL, library sleep |
| [docs/THINK_ARCHITECTURE.md](docs/THINK_ARCHITECTURE.md) | Three Think pillars |
| [docs/TRY_LOCAL_AND_MATHLIB.md](docs/TRY_LOCAL_AND_MATHLIB.md) | Lean / mathlib / local 7B |

---

## Four layers

<div align="center">
<img src="docs/assets/stack-overview.png" alt="MathAgent four-layer stack" width="900"/>
</div>

| Layer | CLI | Use when |
|-------|-----|----------|
| 1 | `solve` / `eval` / UI | Standard problems, tool loop |
| 2 | `formal` / `econ` / `lean-check` | Need certificates, tight budget |
| 3 | `lattice` / `lattice-gate` | Open problems, honest gaps |
| 4 | `lattice --think` | Competing concepts, library ops, evidence |

---

## MathLattice

<div align="center">
<img src="docs/assets/lattice-loop.png" alt="MathLattice loop" width="900"/>
</div>

```bash
mathagent lattice "Twin primes: map certifiable lemmas and mark the open gap"
mathagent lattice "..." --concept-value
mathagent lattice-gate <project> <concept_id> accept --note "..."
```

## Think pillars

<div align="center">
<img src="docs/assets/think-pillars.png" alt="Think pillars" width="900"/>
</div>

```bash
mathagent lattice "..." --think --auto-accept   # smoke only
```

See Chinese README for full setup, Lean paths, layout, and design doctrine: [README.md](README.md).

## License

MIT — [LICENSE](LICENSE).
