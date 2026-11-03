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

## Status machine (Concept)

```text
admit → OPEN | HUMAN_REVIEW
         │         │
         │    lattice-gate accept/reject
         │         │
         ▼         ▼
      ACCEPTED   REJECTED ── spawn/wake 跳过
         │
    spawn predicted_leaf_checks → wake call_op
         │
    cheap_tests / arena ──败者──► REJECTED
```

## CLI

```bash
mathagent lattice "<problem>" --think [--auto-accept] [--wake-rounds 1] [--max-wake 3]
mathagent lattice-gate <project_id> <concept_id> accept|reject --note "..."
```

- `--think` 隐含 concept-value 环，并跑 `run_think_cycle`（start / mid / end）。
- `--auto-accept`：**仅烟测**；会跳过人类共谋门。
- 证据写入：`data/lattice/evidence.jsonl`；图：`data/lattice/<project>.json`。

## Design rationale (why three, not one mega-module)

1. **Executable** closes DreamCoder’s gap: abstractions outside the action space are comments.
2. **Arena + cheap tests** closes Robot-Scientist’s gap: hypotheses must die on failed predictions.
3. **Evidence** closes lifelong/continual gap: one-run V scores cannot define “good concept”.

Together they constrain *language change* in the research graph—not just sample more proofs.

## Acceptance (minimal)

1. **Executable:** ≥1 library op with `sympy_template` + binding → `call_op` ok; wake prefers `call_op`; invoke telemetry increments.
2. **Arena / cheap:** ≥2 concepts on same gap; all-fail cheap predictions → `REJECTED`; else fitness keeps one winner.
3. **Evidence:** each think end appends rows with `delta_graph_dl`; next run `prior_boost` can raise *or demote* by historical MDL.

Tests: `tests/test_think_pillars.py`, `tests/test_concept_value.py`.
