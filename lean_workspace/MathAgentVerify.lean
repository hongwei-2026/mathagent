/-!
  MathAgent Lean workspace on D: (core Lean, no mathlib).
-/

namespace MathAgentVerify

theorem true_intro : True := trivial

theorem nat_add_comm (a b : Nat) : a + b = b + a := Nat.add_comm a b

theorem sq_nonneg_nat (n : Nat) : 0 ≤ n * n := Nat.zero_le _

theorem zero_add (n : Nat) : 0 + n = n := Nat.zero_add n

end MathAgentVerify
