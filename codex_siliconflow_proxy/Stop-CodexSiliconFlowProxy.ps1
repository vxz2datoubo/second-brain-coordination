$ErrorActionPreference = "Stop"

$proxyRoot = "F:\aidanao\codex_siliconflow_proxy"
$stateDir = Join-Path $proxyRoot "state"
$pidPath = Join-Path $stateDir "proxy.pid"

if (-not (Test-Path $pidPath)) {
    Write-Output "No running SiliconFlow proxy was found."
    exit 0
}

$processId = (Get-Content $pidPath -Raw).Trim()
if ($processId) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId
        Write-Output "Stopped SiliconFlow proxy. PID: $processId"
    } else {
        Write-Output "PID file exists, but the process is no longer running."
    }
}

Remove-Item $pidPath -ErrorAction SilentlyContinue
