"""Structured tactic skeletons — cheap pass@k boost (arXiv:2601.16172)."""

TACTIC_SKELETONS: list[str] = [
    "try rfl",
    "try simp",
    "try decide",
    "intro; simp",
    "intro; omega",
    "induction n with\n| zero => simp\n| succ n ih => simp [ih]",
    "constructor <;> simp",
    "apply Nat.add_comm",
    "exact Nat.zero_le _",
    "ring_nf  -- only if mathlib/ring available",
    "nlinarith  -- only if mathlib available",
    "have h : ?_ := by ?_\n  exact h",
]


def skeleton_prompt_block() -> str:
    lines = "\n".join(f"- {s}" for s in TACTIC_SKELETONS[:9])
    return (
        "Prefer one of these Lean 4 tactic skeletons when closing a goal:\n"
        f"{lines}\n"
        "Keep proofs short. No mathlib imports unless unavoidable."
    )
