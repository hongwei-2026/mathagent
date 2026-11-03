# Think Architecture — three pillars toward conceptual cognition

**Problem:** MathLattice had research *discipline* (graph, rubrics, gates) but not *thinking*:
concepts were narrative JSON; wake ignored the library; hypotheses never killed each other;
value scores did not accumulate across projects.

**Non-goal:** larger CoT / higher IMO pass@k.

## Frontier anchors

| Pillar | Systems / ideas taken |
|--------|------------------------|
| **1 Executable library** | DreamCoder wake–sleep (Ellis et al. 2023): abstractions must be *callable primitives*; LILO / decompile amortized knowledge; theorem-discovery agents that add theorems as *actions* |
| **2 Hypothesis competition** | Lakatos SRP (hard core + protective belt); IBE / competing hypotheses (not always exclusive); abduction-as-belief-revision |
| **3 Cross-run evidence** | CoEvo knowledge library; LeanAgent lifelong DB; Mathscape compression reward; Robot Scientist closed loops |

## Loop

```
          ┌──────── EvidenceLedger (cross-project) ────────┐
          │  which ops/concepts actually ↓ graph_dl / ↑ certify │
          └──────────────────▲─────────────────────────────┘
                             │ commit winners / demote losers
   Arena (competing Concepts on same gaps)
        │ eliminate by leaf certify + MDL Δ
        ▼
   Executable Library  ──call──►  Wake cheap certify
        ▲ invent / refactor                       │
        └──────── Sleep library_ops ──────────────┘
```

## Modules

| File | Responsibility |
|------|----------------|
| `lattice/think/executable.py` | Instantiate `{{param}}` SymPy/Lean templates; `call_op` must succeed or refute |
| `lattice/think/arena.py` | Group concepts by shared gaps; score; `REJECTED` losers |
| `lattice/think/evidence.py` | Append-only ledger under `data/lattice/evidence.jsonl` |
| `lattice/think/loop.py` | Orchestrate think cycle after concept-value admit |

## Acceptance (minimal)

1. **Executable:** ≥1 library op with `sympy_template` + binding → `call_op` returns certify ok; wake prefers `call_op` over free-form LLM.
2. **Arena:** ≥2 concepts sharing a gap → after leaf outcomes, exactly one remains non-`REJECTED` (or both rejected if all fail).
3. **Evidence:** each think run appends records; next run can boost ops with historical `mdl_gain>0` / certify rate.
