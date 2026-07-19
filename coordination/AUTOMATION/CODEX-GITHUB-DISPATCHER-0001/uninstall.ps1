# CODEX-GITHUB-DISPATCHER-0001 — Uninstall Script
# Stops and removes the Task Scheduler task. Does NOT delete state directory.

$TaskName = "CodexGitHubDispatcher0001"

Write-Host "Uninstalling Codex GitHub Dispatcher ..."

# Stop running instance
try {
    schtasks /end /tn $TaskName 2>$null
    Write-Host "  Stopped running instance"
} catch {
    Write-Host "  No running instance"
}

# Delete task
try {
    schtasks /delete /tn $TaskName /f 2>$null
    Write-Host "  Task deleted"
} catch {
    Write-Host "  Task not found"
}

Write-Host ""
Write-Host "State directory (NOT deleted): %LOCALAPPDATA%\SecondBrain\CodexDispatcher\"
Write-Host "To clean state: Remove-Item -Recurse `$env:LOCALAPPDATA\SecondBrain\CodexDispatcher\"
