# Install / configure Ollama with models on D: (avoid filling C:)
# 1) Run D:\lean\OllamaSetup.exe once
# 2) Then:
#    $env:OLLAMA_MODELS='D:\models\ollama'
#    ollama pull yothgewalt/DeepSeek-Prover-V2-7B-GGUF:Q4_K_M
# 3) mathagent econ --local "theorem ..."

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path D:\models\ollama, D:\lean\ollama_home | Out-Null
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\models\ollama", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOME", "D:\lean\ollama_home", "User")
$env:OLLAMA_MODELS = "D:\models\ollama"
$env:OLLAMA_HOME = "D:\lean\ollama_home"
Write-Host "OLLAMA_MODELS=$env:OLLAMA_MODELS"
if (Get-Command ollama -ErrorAction SilentlyContinue) {
  ollama --version
  ollama list
} else {
  Write-Host "ollama not on PATH yet — finish installer first: D:\lean\OllamaSetup.exe"
}
