# THREAT MODEL — Codex GitHub Dispatcher Phase 1

## Assets
- Codex OAuth session (ChatGPT membership)
- GitHub PAT (repo + workflow scope)
- Local workspace (F:\aidanao\coordination\worktrees\codex-dispatcher-mvp)
- Dispatcher state (SQLite DB, lock file)
- Dispatcher logs

## Threat Actors
| Actor | Capability | Motivation |
|-------|-----------|------------|
| Malicious comment author | Can post Issue comments under shared GitHub account | Execute arbitrary Codex tasks |
| Local malware | File read access to dispatcher state | Steal cursor/state, inject tasks |
| Network MITM | Intercept GitHub API traffic | Read dispatch content, inject responses |
| Accidental misconfiguration | Valid dispatch with wrong workspace/head | Corrupt worktree state |

## Phase 1 Mitigations

### T1: Unauthorized Dispatch
- **Control**: Only comments on issues labeled `codex-dispatch` are processed
- **Control**: Only `issuer_agent: GPT` + `target_agent: CODEX` accepted
- **Control**: Only `risk_class: low` + `approval_policy: automatic`
- **Control**: Fixed repository allowlist (single repo)
- **Control**: Fixed workspace alias allowlist (single workspace)
- **Control**: Strict YAML schema — unknown keys rejected
- **Residual risk**: Shared GitHub account means issuer_agent is NOT crypto auth

### T2: Replay Attacks
- **Control**: SQLite idempotency DB — each key executed only once
- **Control**: Cursor initialized to latest comment ID at install time
- **Residual risk**: None (replay fully blocked)

### T3: Code Execution via Comments
- **Control**: Dispatcher NEVER executes comment body as code
- **Control**: Only dispatcher's fixed wrapper prompt is passed to Codex
- **Control**: Instructions passed as GitHub URL (not inline code)
- **Residual risk**: None (Codex reads from GitHub autonomously)

### T4: File System Damage
- **Control**: Codex sandbox forced to `read-only`
- **Control**: Worktree dirty-check before each execution
- **Control**: Isolated worktree (separate from main working directory)
- **Residual risk**: Codex could bypass sandbox (depends on Codex CLI implementation)

### T5: Credential Leakage
- **Control**: Token read from Git Credential Manager (never stored in code)
- **Control**: Log output redacted (credential patterns stripped)
- **Control**: GitHub API tokens never written to comments
- **Residual risk**: Stack traces in Codex output may contain env vars (attempted redaction)

### T6: Denial of Service
- **Control**: Single-instance lock prevents overlapping dispatchers
- **Control**: 15-minute timeout per Codex task
- **Control**: 60-second poll interval (max 60 API requests/hour)
- **Residual risk**: Codex task queue could fill with valid low-risk tasks

### T7: Worktree Corruption
- **Control**: git status --porcelain before every execution
- **Control**: No auto-stash, reset, clean, or checkout
- **Residual risk**: Manual intervention needed if worktree becomes dirty

## Out of Scope (Phase 1)
- Multi-tenant authentication (single GitHub account)
- Network TLS interception detection
- Codex sandbox escape auditing
- Audit log tampering detection
