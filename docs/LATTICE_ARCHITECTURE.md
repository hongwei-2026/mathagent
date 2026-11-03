# MathLattice — research-level reasoning architecture (low-resource)

**Goal:** Aim the *shape* of Fields-adjacent work without OpenAI-scale compute.  
**Non-goal:** Claim Fields Medal proofs from an API call.

## Why contest stacks fail on Fields problems

| Contest / IMO stack | Fields / research need |
|---|---|
| Fixed statement → prove | Often must **conjecture** the statement first |
| One proof tree | **Theory-building**: definitions, folklore lemmas, transfer |
| Pass@k sampling | Long-horizon **memory** across failed attempts |
| End-to-end formalization | **Dependency graphs** of concepts not in Mathlib |

## Sources we absorb

| System | Idea taken |
|---|---|
| **Ansatz / Continual Graph Memory** | Typed graph of facts / plans / counterexamples + curator |
| **DreamProver** | Wake (prove) / Sleep (abstract reusable lemmas) |
| **LeanConjecturer / Lemmanaid** | Explicit conjecture generation before proving |
| **Aria** | Concept dependency graph + bottom-up formalization |
| **FAR / “Problem is the Problem”** | Maintain an *attemptable open-problem pool* with status |
| **EconProver + our econ** | Cheap certify leaves; escalate only on failures |
| **OpenAI formal-math** | Statement curriculum as free unsupervised schedule |

## MathLattice loop

```
                 ┌─────────────────────────────┐
                 │   Research Graph Memory      │
                 │  + Concept / Abduction       │
                 │  Target, Conjecture, Lemma,  │
                 │  Plan, Gap, Counterex        │
                 └──────────────▲───────────────┘
                                │ admit if certified
        ┌───────────────────────┴───────────────────────┐
        │                                               │
   WAKE (explore)                                 SLEEP (compress)
   1. pick frontier conjecture                    1. cluster similar lemmas
   2. curriculum / decompose                      2. abstract → Conjecture only
   3. econ / Lean / SymPy certify                 3. prune / rescore
   4. write Gap if blocked                        4. never fake Lemma
        │                                               │
        └──────────────────► Curator ◄──────────────────┘
```

## Concept-value loop (A→E) — `--concept-value`

Addresses: probabilistic search ≠ conceptual creation.

| Step | Module | Role |
|---|---|---|
| **A** Abduction | `lattice/abduction.py` | Explain gaps by inventing Concept language |
| **B** Concept slots | `graph.admit_concept` | Typed node + closes_gap edges + scores |
| **C** Analogy | `lattice/analogy.py` | Structure maps; sympy witnesses → systematicity |
| **D** Surprise/curator | `lattice/value.py` + `curator.py` | Rank by V=compress×minimal×syst×surprise |
| **E** Human gate | `mathagent lattice-gate` | Co-abduction accept/reject before treating as theory |

```bash
mathagent lattice "..." --concept-value
mathagent lattice-gate <project> <concept_id> accept --note "..."
```

High `conceptual_value` without verified analogy maps stays `HUMAN_REVIEW`.

## Paradigm layer (MDL / library sleep / causal surprise)

| Piece | Module | Role |
|---|---|---|
| **MDL compression** | `lattice/mdl.py` | Concept V uses bit-gain (close gaps − def − axioms − new gaps), not only gap counts |
| **Library sleep** | `lattice/sleep.py` | Sleep emits gated `library_ops` as Concepts — never high-score uncertified conjectures |
| **Causal surprise** | `lattice/causal.py` | After wake, `do(concept)` → empirical leaf certify rate updates surprise |

## Think layer (next paradigm)

Executable library + hypothesis arena + evidence ledger: see [`THINK_ARCHITECTURE.md`](THINK_ARCHITECTURE.md).

```bash
mathagent lattice "..." --think --auto-accept
```

## Admission rule (resource honesty)

Only nodes with a **certificate** enter as `Lemma`:
- Lean ok, or
- SymPy/finite certify, or
- explicit `manual_accepted` (human)

Sleep-phase “abstract lemmas” are stored as **high-score Conjectures** until certified.
Everything else stays `Conjecture` or `Gap`. Fields-level targets almost always retain Gaps — that is a feature.

## Mapping onto this repo

| Lattice component | Code |
|---|---|
| Graph memory | `src/mathagent/lattice/graph.py` |
| Conjecture phase | `src/mathagent/lattice/conjecture.py` |
| Abduction / concepts | `src/mathagent/lattice/abduction.py` |
| Analogy maps | `src/mathagent/lattice/analogy.py` |
| Value rubrics | `src/mathagent/lattice/value.py` |
| Curator | `src/mathagent/lattice/curator.py` |
| Wake prove | `src/mathagent/lattice/wake.py` → uses `formal.econ` + `formal.certify` |
| Sleep consolidate | `src/mathagent/lattice/sleep.py` |
| Pipeline | `src/mathagent/lattice/pipeline.py` |
| CLI | `mathagent lattice "..."` / `lattice-gate` |

Persistence: `data/lattice/<project_id>.json` (gitignored working state).
