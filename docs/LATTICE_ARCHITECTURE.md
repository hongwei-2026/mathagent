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
                 │  nodes: Target, Conjecture,  │
                 │  Lemma, Plan, Gap, Counterex │
                 │  edges: depends / refutes /  │
                 │         abstracts            │
                 └──────────────▲───────────────┘
                                │ admit if certified
        ┌───────────────────────┴───────────────────────┐
        │                                               │
   WAKE (explore)                                 SLEEP (compress)
   1. pick frontier conjecture                    1. cluster similar lemmas
   2. curriculum / decompose                      2. abstract transferable lemma
   3. econ / Lean / SymPy certify                 3. prune dead conjectures
   4. write Gap if blocked                        4. update frontier scores
        │                                               │
        └──────────────────► Curator ◄──────────────────┘
                              scores routes
                              decides stop / escalate CoT
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
| Wake prove | `src/mathagent/lattice/wake.py` → uses `formal.econ` + `formal.certify` |
| Sleep consolidate | `src/mathagent/lattice/sleep.py` |
| Curator + run | `src/mathagent/lattice/pipeline.py` |
| CLI | `mathagent lattice "..."` |

Persistence: `data/lattice/<project_id>.jsonl` on D: (gitignored working state).
