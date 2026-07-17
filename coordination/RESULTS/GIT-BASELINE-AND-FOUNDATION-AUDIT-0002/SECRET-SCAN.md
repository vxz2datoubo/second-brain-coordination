# SECRET-SCAN — 密钥与敏感信息扫描

> Task: GIT-BASELINE-AND-FOUNDATION-AUDIT-0002 | WorkBuddy role
> Date: 2026-07-16 05:43 UTC+8
> Scope: F:\aidanao (excl. node_modules, .venv, __pycache__, handoff/, playwright_user_data/, Cache/)

## Critical Findings

### 🔴 P0 — Must exclude from Git

| # | File | Secret Type | Value |
|---|------|-------------|-------|
| 1 | `core/tushare_bridge.py:16` | Tushare API Token | `42faf4958b7e400596a9c62b845cad0c` (hardcoded) |
| 2 | `data/wallet.json:18` | Tushare API Token | Same token duplicated |

### 🟠 P1 — Should exclude or gitignore

| # | File | Content | Risk |
|---|------|---------|------|
| 3 | `codex_siliconflow_proxy/proxy_server.py:14` | `SILICONFLOW_API_KEY` env var reference | Value from env, not hardcoded — safe if .env is gitignored |
| 4 | `F:/aidanao/codex_accounts/vault.json` | Contains email + password for purchased Codex account | Must gitignore codex_accounts/ |
| 5 | `F:/aidanao/codex_accounts/braylonwasheleski_2026-07-16.json` | Contains email + OAuth refresh_token | Must gitignore |
| 6 | `bulletin/deskpet-注意事项.md:63` | References FISH_AUDIO_API_KEY path | Not a secret itself, but points to sensitive config |

### 🟢 Clean — Documentation examples (no real secrets)

| # | File | Content |
|---|------|---------|
| 7 | `maibot/sources/maibot-docs-llms-full-2026-06-22.md` | `sk-your-api-key-here` — documentation examples |
| 8 | `maibot/atoms/pages/P052-manual-configuration-model-config.md.md` | API key field descriptions |

## .env Files

**None found.** No `.env` or `*.env` files exist in `F:\aidanao` (excl. node_modules, .venv).

## Required .gitignore entries

```
core/tushare_bridge.py
data/wallet.json
codex_accounts/
*.env
```

**Recommendation**: Refactor `tushare_bridge.py` to read token from environment variable or a gitignored config file before Git initialization.
