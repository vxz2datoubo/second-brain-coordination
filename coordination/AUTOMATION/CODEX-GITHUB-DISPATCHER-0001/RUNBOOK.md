# RUNBOOK — Codex GitHub Dispatcher Phase 1

## Quick Commands

### Install
```powershell
cd F:\ai\second-brain-coordination\coordination\AUTOMATION\CODEX-GITHUB-DISPATCHER-0001
powershell -File install.ps1
```

### Uninstall
```powershell
cd F:\ai\second-brain-coordination\coordination\AUTOMATION\CODEX-GITHUB-DISPATCHER-0001
powershell -File uninstall.ps1
```

### Start Manually
```powershell
schtasks /run /tn CodexGitHubDispatcher0001
```

### Stop
```powershell
schtasks /end /tn CodexGitHubDispatcher0001
```

### Check Status
```powershell
schtasks /query /tn CodexGitHubDispatcher0001 /v /fo LIST
```

### View Logs
```powershell
Get-Content $env:LOCALAPPDATA\SecondBrain\CodexDispatcher\logs\dispatcher.log -Tail 50
```

### Clean State (DANGER: resets cursor, may cause replay)
```powershell
Remove-Item -Recurse $env:LOCALAPPDATA\SecondBrain\CodexDispatcher\
```

## Health Checks

| Check | Command | Expected |
|-------|---------|----------|
| Codex CLI | `codex.cmd --version` | `codex-cli 0.141.0` |
| GitHub API | `curl -s https://api.github.com | head -1` | HTTP 200 |
| Task running | `schtasks /query /tn CodexGitHubDispatcher0001` | Status: Running |
| Worktree clean | `git -C F:\aidanao\coordination\worktrees\codex-dispatcher-mvp status --porcelain` | (empty) |
| Cursor valid | Check dispatcher.log for "Cursor initialized" | Shows latest comment ID |

## Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Another dispatcher instance running" | Stale lock file | Kill all python.exe, delete dispatcher.lock |
| 401 from GitHub API | PAT expired | Regenerate PAT, update Windows Credential Manager |
| "Codex CLI not found" | Path changed | Update CODEX_CMD in codex_wrapper.py |
| Worktree dirty | Uncommitted changes | Manual checkout or stash in worktree |
| ChatGPT auth expired | OAuth token expired | Run `codex login` manually |
| "403 Resource not accessible" | Token lacks scope | Regenerate PAT with `repo, workflow` scopes |

## Escalation

If dispatcher is unresponsive after restart:
1. Check logs at `%LOCALAPPDATA%\SecondBrain\CodexDispatcher\logs\dispatcher.log`
2. Verify GitHub API reachable: `curl -H "Authorization: Bearer <token>" https://api.github.com/user`
3. Verify Codex auth: `codex.exe doctor 2>&1 | grep auth`
4. If OAuth expired: manual `codex login` required — dispatcher cannot auto-renew
