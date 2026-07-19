$ErrorActionPreference = "Stop"

$proxyRoot = "F:\aidanao\codex_siliconflow_proxy"
$manageScript = Join-Path $proxyRoot "manage_codex_profile.py"
$stopScript = Join-Path $proxyRoot "Stop-CodexSiliconFlowProxy.ps1"

& uv run --no-project --with tomlkit python $manageScript disable
& $stopScript

Write-Output "Codex has been restored to the default model configuration."
