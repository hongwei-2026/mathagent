# lean_mathlib (D: only)

Mathlib4 **v4.34.0** workspace for MathAgent hard checks.

- Toolchain: Lean 4.34.0 under `D:\lean\elan`
- Packages + oleans: `D:\mathagent\lean_mathlib\.lake` (~7GB, gitignored)
- Smoke: `lake env lean LeanMathlib.lean` → proves `∀ a b : Real, a*b = b*a`

```powershell
$env:ELAN_HOME='D:\lean\elan'
$env:MATHAGENT_LEAN_WORKSPACE='D:\mathagent\lean_mathlib'
mathagent lean-check
```
