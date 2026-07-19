# GIT-PREFLIGHT — Git初始化前审计总结

> Task: GIT-BASELINE-AND-FOUNDATION-AUDIT-0002 | WorkBuddy role
> Date: 2026-07-16 05:43 UTC+8

## Quick Summary

| Check | Result |
|-------|--------|
| Nested Git repos | ✅ 0 found — safe for root `git init` |
| `.env` files | ✅ 0 found |
| Secrets found | 🔴 2 hardcoded tokens (Tushare API token) + 1 wallet file |
| Files >100MB | ✅ 0 |
| Files >50MB | ✅ 0 |
| Files >10MB | ⚠️ 6 (31MB SQLite, 30MB .exe, 25MB+16MB JSON data) |
| Total files scanned | 1,599 |

## Foundation Write-back Verification

Foundation task (`FOUNDATION-DATA-GOVERNANCE-0001`) modified files dated 2026-07-16:

| File | Size | SHA256 | Modified |
|------|------|--------|:------:|
| `brain_core/foundation_data_governance.py` | 71KB | `37a11de...` | 05:31 |
| `brain_core/service.py` | 262KB | `f53247d...` | 05:32 |
| `bulletin/super-second-brain-v01-board.md` | 12KB | `27fa6b14...` | 05:43 |
| `apps/cli/brainctl.py` | (exists) | `72ad5d3e...` | — |

SQLite (`data/super_brain_v01.sqlite`): 31.1MB, 35 tables, `bulletin_state_records: 167`, `evolution_logs: 536`, `trade_decisions: 152`

`data/audit/events.jsonl`: 12MB, 86,889 lines — runtime audit log, should be gitignored.

SelfEvolutionLog: Stored in SQLite as `evolution_logs` table (536 rows), not as a standalone file.

## File Types Summary

| Type | Count | >1MB | Recommendation |
|------|:-----:|:----:|-------|
| Python (.py) | ~300 | 1 | `trading_domain.py` (1.2MB) — review for splitting |
| SQLite (.sqlite/.db) | 6 | 1 | gitignore all |
| JSON data | ~50 | 6 | gitignore data/raw/ and data/audit/ |
| Screenshots (.png) | ~10 | 5 | gitignore tools/screenshots/ |
| ZIP archives | ~5 | 1 | gitignore backups/ and handoff/ |
| .exe | 1 | 1 | gitignore tools/dreamina/ |

## Recommended `.gitignore` candidates

```gitignore
# Secrets & credentials
core/tushare_bridge.py
data/wallet.json
codex_accounts/
*.env

# Large data & databases
data/raw/
data/audit/
data/*.sqlite
data/*.db
data/knowledge-graph-backup-*.json

# Runtime & logs
data/logs/
_tmp_status_debug/
logs/

# External tools & binaries
tools/dreamina/
*.exe

# Generated output
output/
handoff/
backups/
exports/

# Screenshots & media
tools/screenshots/
*.png
*.jpg

# Backup archives
*.zip
*.tar.gz

# Temporary
__pycache__/
*.pyc
```

## Recommended `.gitattributes` candidates

```
*.sqlite filter=lfs diff=lfs merge=lfs -text
*.jsonl filter=lfs diff=lfs merge=lfs -text
```

## Files NOT to gitignore (candidate for initial commit)

- All `.md` documentation (governance, protocols, memory)
- All `.py` source (except `tushare_bridge.py`)
- All `.yaml` / `.yml` configs (except those containing secrets)
- `coordination/`
- `memory/`
- `daytrade_system/`
- `core/` (except `tushare_bridge.py`)
- `config/trading/*.candidate.yaml`
- `docs/`
- `mcp/`
- `tests/`
- `apps/`
