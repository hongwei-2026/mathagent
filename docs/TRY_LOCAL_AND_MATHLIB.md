# Tried: local 7B prover + mathlib on D:

## Mathlib — SUCCESS (local, D:)

| Item | Path / result |
|---|---|
| Project | `D:\mathagent\lean_mathlib` |
| Mathlib pin | tag `v4.34.0` (matches Lean 4.34.0) |
| Cache | `lake` downloaded **8908** oleans |
| Size | ~7 GB under `lean_mathlib` |
| Smoke | `lake env lean LeanMathlib.lean` → **exit 0** |

```powershell
$env:ELAN_HOME='D:\lean\elan'
$env:Path="D:\lean\elan\bin;$env:Path"
cd D:\mathagent\lean_mathlib
lake env lean LeanMathlib.lean
```

Point formal checks at mathlib workspace when needed:

```powershell
$env:MATHAGENT_LEAN_WORKSPACE='D:\mathagent\lean_mathlib'
```

## Local 7B prover (Ollama) — IN PROGRESS

Machine: ~31 GB RAM, **no NVIDIA driver / no GPU path** → CPU GGUF is feasible but slow.

| Step | Status |
|---|---|
| `OLLAMA_MODELS=D:\models\ollama` | set (User env) |
| Download `OllamaSetup.exe` to D:\lean | resumed; large (~1.6 GB) |
| Pull `DeepSeek-Prover-V2-7B-GGUF:Q4_K_M` (~4.2 GB) | after install |
| `mathagent econ --local ...` | wired in CLI |

```powershell
powershell -File scripts\setup_ollama_d.ps1
# after install:
ollama pull yothgewalt/DeepSeek-Prover-V2-7B-GGUF:Q4_K_M
mathagent econ --local "theorem add_comm (a b : Nat) : a + b = b + a := by"
```

Until Ollama is up, keep using DeepSeek API cheap path (`mathagent econ` without `--local`).
