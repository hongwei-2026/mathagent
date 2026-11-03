# Keep Lean 4 entirely on D: (no C:\Users\...\.elan pile-up)
# Prerequisites: elan already bootstrapped under D:\lean\elan
# Optional: place toolchain zip at D:\lean\lean-windows.zip and extract first.

$ErrorActionPreference = "Stop"

$LeanRoot = "D:\lean"
$ElanHome = Join-Path $LeanRoot "elan"
$Tmp = Join-Path $LeanRoot "tmp"
$Cache = Join-Path $LeanRoot "cache"
$HomeDir = Join-Path $LeanRoot "home"
$Workspace = "D:\mathagent\lean_workspace"

New-Item -ItemType Directory -Force -Path $ElanHome, $Tmp, $Cache, $HomeDir, $Workspace | Out-Null

[System.Environment]::SetEnvironmentVariable("ELAN_HOME", $ElanHome, "User")
[System.Environment]::SetEnvironmentVariable("XDG_CACHE_HOME", $Cache, "User")
[System.Environment]::SetEnvironmentVariable("MATHAGENT_LEAN_HOME", $ElanHome, "User")
[System.Environment]::SetEnvironmentVariable("MATHAGENT_LEAN_WORKSPACE", $Workspace, "User")
[System.Environment]::SetEnvironmentVariable("MATHAGENT_LEAN_TMP", $Tmp, "User")
[System.Environment]::SetEnvironmentVariable("MATHAGENT_LEAN_CACHE", $Cache, "User")

$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*D:\lean\elan\bin*") {
    [System.Environment]::SetEnvironmentVariable("Path", "D:\lean\elan\bin;$userPath", "User")
}

$env:ELAN_HOME = $ElanHome
$env:XDG_CACHE_HOME = $Cache
$env:TMP = $Tmp
$env:TEMP = $Tmp
$env:HOME = $HomeDir
$env:Path = "D:\lean\elan\bin;$env:Path"

Write-Host "ELAN_HOME=$env:ELAN_HOME"
elan --version
lean --version
lake --version
Write-Host "OK: Lean resolves from D: — no cloud required"
if (Test-Path "$env:USERPROFILE\.elan") {
    Write-Warning "C:\Users\...\.elan exists — delete after verifying D:\lean works."
}
