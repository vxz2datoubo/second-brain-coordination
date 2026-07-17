$ErrorActionPreference = "Stop"

$proxyRoot = "F:\aidanao\codex_siliconflow_proxy"
$venvDir = Join-Path $proxyRoot ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$uvicornExe = Join-Path $venvDir "Scripts\uvicorn.exe"
$stateDir = Join-Path $proxyRoot "state"
$logsDir = Join-Path $proxyRoot "logs"
$pidPath = Join-Path $stateDir "proxy.pid"
$stdoutLog = Join-Path $logsDir "proxy.stdout.log"
$stderrLog = Join-Path $logsDir "proxy.stderr.log"

function Get-EffectiveEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $processValue = [System.Environment]::GetEnvironmentVariable($Name, "Process")
    if ($processValue) {
        return $processValue
    }

    return [System.Environment]::GetEnvironmentVariable($Name, "User")
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$siliconFlowApiKey = Get-EffectiveEnvValue -Name "SILICONFLOW_API_KEY"
if (-not $siliconFlowApiKey) {
    throw "Missing environment variable: SILICONFLOW_API_KEY"
}

$proxyMasterKey = Get-EffectiveEnvValue -Name "CODEX_SILICONFLOW_PROXY_KEY"
if (-not $proxyMasterKey) {
    throw "Missing environment variable: CODEX_SILICONFLOW_PROXY_KEY"
}

$siliconFlowBaseUrl = Get-EffectiveEnvValue -Name "SILICONFLOW_BASE_URL"
if (-not $siliconFlowBaseUrl) {
    $siliconFlowBaseUrl = "https://api.siliconflow.cn/v1"
}

$env:SILICONFLOW_API_KEY = $siliconFlowApiKey
$env:CODEX_SILICONFLOW_PROXY_KEY = $proxyMasterKey
$env:SILICONFLOW_BASE_URL = $siliconFlowBaseUrl

if (Test-Path $pidPath) {
    $existingPid = (Get-Content $pidPath -Raw).Trim()
    if ($existingPid) {
        $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($existingProcess) {
            Write-Output "SiliconFlow proxy is already running. PID: $existingPid"
            exit 0
        }
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was not found."
}

if (-not (Test-Path $pythonExe)) {
    & uv venv $venvDir --python 3.12
}

& uv pip install --python $pythonExe "fastapi>=0.116.0" "httpx>=0.28.1" "uvicorn>=0.35.0"

$process = Start-Process `
    -FilePath $uvicornExe `
    -ArgumentList @("proxy_server:app", "--host", "127.0.0.1", "--port", "4141") `
    -WorkingDirectory $proxyRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

Set-Content -Path $pidPath -Value $process.Id -Encoding ascii

$started = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:4141/health/liveliness" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $started = $true
        break
    } catch {
    }
}

if (-not $started) {
    throw "SiliconFlow proxy failed to start. Check log: $stderrLog"
}

Write-Output "SiliconFlow proxy started: http://127.0.0.1:4141/v1"
