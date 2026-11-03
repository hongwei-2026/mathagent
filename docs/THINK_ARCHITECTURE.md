# Think Architecture — three pillars toward conceptual cognition

**Problem:** MathLattice had research *discipline* (graph, rubrics, gates) but not *thinking*:
concepts were narrative JSON; wake ignored the library; hypotheses never killed each other;
value scores did not accumulate across projects.

**Non-goal:** larger CoT / higher IMO pass@k.

## Frontier anchors

| System | Takeaway | Pillar |
|--------|----------|--------|
| DreamCoder | Wake **calls** library primitives; sleep compresses solutions | 1 |
| LILO / Stitch | Libraries must be invokable + compressible | 1 |
| Robot Scientist / Eve | Competing hypotheses → cheapest discriminating experiment | 2 |
| BACON / Lakatos | Theory revision; progressive vs degenerating programmes | 2 |
| Peirce / HALO | Abduction has a **price** (opened gaps + axioms) | 2 |
| CoEvo / LeanAgent / Mathscape | Continual library + compression attribution across runs | 3 |
| Ansatz / Aria | Typed graph / concept DAG as durable theory memory | 3 |

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
| `lattice/think/executable.py` | Instantiate `{{param}}` templates; `call_op` + invoke telemetry |
| `lattice/think/cheap_tests.py` | Discriminating sympy/call_op tests; kill all-fail hypotheses |
| `lattice/think/arena.py` | Group by shared gaps; fitness elimination after cheap tests |
| `lattice/think/evidence.py` | JSONL ledger with `delta_graph_dl`; boost/demote priors |
| `lattice/think/loop.py` | start → mid (cheap+arena) → end (Δdl commit) |

## Acceptance (minimal)

1. **Executable:** ≥1 library op with `sympy_template` + binding → `call_op` returns certify ok; wake prefers `call_op` over free-form LLM.
2. **Arena:** ≥2 concepts sharing a gap → after leaf outcomes, exactly one remains non-`REJECTED` (or both rejected if all fail).
3. **Evidence:** each think run appends records; next run can boost ops with historical `mdl_gain>0` / certify rate.
