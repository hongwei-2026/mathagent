# MathAgent Lean workspace (D: only)

| Path | Role |
|---|---|
| `D:\lean\elan` | elan + Lean toolchains (`ELAN_HOME`) |
| `D:\lean\cache` | XDG cache |
| `D:\lean\tmp` | build temp |
| `D:\mathagent\lean_workspace` | this lake project |

No cloud required. Mathlib is optional and large; start with core Lean.

```powershell
$env:ELAN_HOME='D:\lean\elan'
$env:Path = "D:\lean\elan\bin;$env:Path"
$env:TMP='D:\lean\tmp'; $env:TEMP='D:\lean\tmp'
cd D:\mathagent\lean_workspace
lake build
lake env lean Scratch.lean
```
