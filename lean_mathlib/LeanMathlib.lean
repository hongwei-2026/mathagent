import Mathlib.Data.Real.Basic

example (a b : Real) : a * b = b * a := by
  rw [mul_comm]