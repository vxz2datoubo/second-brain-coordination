$ErrorActionPreference = "Stop"

$proxyRoot = "F:\aidanao\codex_siliconflow_proxy"
$manageScript = Join-Path $proxyRoot "manage_codex_profile.py"
$startScript = Join-Path $proxyRoot "Start-CodexSiliconFlowProxy.ps1"

& $startScript

& uv run --no-project --with tomlkit python $manageScript enable

Write-Output "Codex has been switched to the DeepSeek V4 Pro proxy configuration. New Codex sessions will use it."
