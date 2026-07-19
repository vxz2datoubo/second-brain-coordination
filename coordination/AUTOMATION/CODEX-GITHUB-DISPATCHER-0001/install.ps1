# CODEX-GITHUB-DISPATCHER-0001 — Install Script
# Creates user-level Task Scheduler task that launches the dispatcher at login.
# Requires: Python 3.x available at %WORKBUDDY_PYTHON% or python.exe on PATH.

$ErrorActionPreference = "Stop"
$TaskName = "CodexGitHubDispatcher0001"
$DispatcherDir = "F:\ai\second-brain-coordination\coordination\AUTOMATION\CODEX-GITHUB-DISPATCHER-0001"
$DispatcherScript = Join-Path $DispatcherDir "dispatcher.py"
$PythonExe = if ($env:WORKBUDDY_PYTHON) { $env:WORKBUDDY_PYTHON } else {
    # Try managed Python
    $managed = "$env:USERPROFILE\.workbuddy\binaries\python\versions\3.13.12\python.exe"
    if (Test-Path $managed) { $managed } else { "python.exe" }
}

Write-Host "Installing Codex GitHub Dispatcher (Phase 1) ..."
Write-Host "  Task: $TaskName"
Write-Host "  Script: $DispatcherScript"
Write-Host "  Python: $PythonExe"

# Remove existing task if present
try {
    schtasks /delete /tn $TaskName /f 2>$null
    Write-Host "  Removed existing task"
} catch { }

# Create task: trigger at user logon, run in background
$Action = "$PythonExe"
$Arguments = "`"$DispatcherScript`""
$StartDir = $DispatcherDir

$cmd = @(
    "schtasks", "/create",
    "/tn", $TaskName,
    "/tr", "`"$Action`" `"$Arguments`"",
    "/sc", "ONLOGON",
    "/ru", $env:USERNAME,
    "/rl", "LIMITED",
    "/f"
) -join " "

Write-Host "  Command: $cmd"
Invoke-Expression $cmd

Write-Host "  Task created successfully"
Write-Host ""
Write-Host "To start immediately: schtasks /run /tn $TaskName"
Write-Host "To stop: schtasks /end /tn $TaskName"
Write-Host "To uninstall: .\uninstall.ps1"
