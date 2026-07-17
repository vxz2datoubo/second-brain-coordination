# SYSTEM STATE

Last updated: 2026-07-16 03:32 UTC+8
Maintainer: WorkBuddy (stamped by WB-HANDOFF-0001 + ORG-CODEX-SETUP-0001)
Status: LIVE — System audit completed, coordination pack deployed.

## Current stage

- Research: ✅ Active (news-backtest decay classifiers, FIFO fund pool engine)
- Backtest: ✅ Active (news_nextday fwd1-5 IC, quintile, strategy P&L; chip digestion profile)
- Simulation: ❌ Not yet
- Shadow mode: ❌ Not yet
- Live trading: ❌ Not yet (manual discretionary only)

## Active repositories

| Path | Branch | Commit | Dirty | Owner |
|---|---|---|---|---|
| F:\aidanao | N/A (no Git) | N/A | N/A | Shared (WorkBuddy, QClaw, Codex) |

⚠️ F:\aidanao 不是 Git 仓库。没有分支、commit 或冲突跟踪。变更历史通过 `.workbuddy/memory/YYYY-MM-DD.md` 每日日志手动维护。

## Data capabilities

| Data domain | Source | Granularity | History | Point-in-time | Status | Known limitations |
|---|---|---|---|---|---|---|
| Real-time quotes (L1) | TDX MCP | snapshot | N/A | ❌ | ✅ active | No DDX field; 10-level depth snapshot only |
| Real-time quotes (L1) | WeStock MCP | snapshot | N/A | ❌ | ✅ active | Shallower depth than TDX |
| 4-channel fund flow | WeStock MCP | daily | ~3-5y | ❌ | ✅ active | Medium/Small orders = mixed (retail + institution splits + quant) |
| Fund flow history | Tushare bridge | daily | long | ❌ | ✅ active (T+1) | Not real-time |
| Tick-by-tick trade (L2) | N/A | N/A | N/A | N/A | ❌ GAP | Blocked – evaluating TdxQuant/eltdx |
| Tick-by-tick order (L2) | N/A | N/A | N/A | N/A | ❌ GAP | Blocked – same as above |
| Call auction order flow | N/A | N/A | N/A | N/A | ❌ GAP | Snapshot-based inference only |
| News (structured) | WeStock MCP + local SQLite | daily index | 1 year (300418, 300058) | ⚠️ | ✅ active | 769 articles; 22-dim daily index; no intraday article timestamp |
| K-line | TDX / WeStock / local JSON | 1min/day | 1 year (local JSON) | ❌ | ✅ active | |
| Chip / Volume Profile | WeStock + local | daily | — | ❌ | ✅ active | |
| Sector rankings | WeStock MCP | real-time | N/A | ❌ | ✅ active | |
| Margin/short selling | WeStock + Tushare | daily | long | ❌ | ✅ active (T+1) | Not real-time |
| Dragon & Tiger seats | WeStock + Tushare | daily | long | ❌ | ✅ active (T+1) | |
| Financials | WeStock + Tushare | quarterly | 10y+ | ❌ | ✅ active | No PIT flag |

## Production and candidate models

| Model | Version | Stage | Data snapshot | Validation status | Owner |
|---|---|---|---|---|---|
| News decay classifier (backtest_news_nextday.py) | v1 | backtest | 2025-07-15 – 2026-07-15 | ✅ fwd1-5 IC + strategy P&L | WorkBuddy |
| Chip digestion profile | v1 | backtest | ~30 trading days | ⚠️ partial | WorkBuddy |
| FIFO fund pool engine | v1 | unit test | synthetic | ✅ 24/24 tests pass | WorkBuddy |
| Alert engine | v1 | production | live (2h automation) | ⚠️ not validated | WorkBuddy |

## Current services

| Service | Port | Status | Health check | Log path |
|---|---|---|---|---|
| SuperBrain backend | 8766 | ✅ online | GET /api/memory/status | logs/ |
| MaiBot WebUI | 8000-8001 | ✅ online | — | F:\aipengyou\logs\ |
| MaiBot Deskpet WS | 8523 | ✅ online | — | F:\aipengyou\logs\ |
| TTS Bridge | 9881 | ✅ online | — | F:\aipengyou\logs\ |
| STT Bridge | 18530 | ❌ offline | — | F:\aipengyou\logs\ |
| TDX client | 14571 | ✅ online | — | TDX native |
| QClaw engine | 5284,14110,19000 | ✅ online | — | QClaw native |

## Current blockers

1. **L2 tick-by-tick trade data unavailable** — TdxQuant/eltdx integration pending.
2. **No Point-in-Time data** — Backtests use final revised financials (look-ahead risk).
3. **No walk-forward validation** — All backtests are full-sample.
4. **No production trading cost model** — Only fund_pool_fifo.py includes commissions/taxes.
5. **No Git repository** — Changes are not version-controlled.
6. **AGENTS.md conflict** — Old (trading manual) vs new (coordination protocol) version needs user merge decision.

## Latest completed tests

| Component | Command | Result | Time |
|---|---|---|---|
| fund_pool_fifo.py | unit tests | 24/24 pass | 2026-07-15 |
| backtest_news_nextday.py | full run | IC + strategy CSVs generated | 2026-07-15 |
| alert_engine.py | query 7 days | pending.json populated | 2026-07-15 |

## Active tasks

| Task ID | Owner | Reviewer | Status | Branch/worktree |
|---|---|---|---|---|
| WB-HANDOFF-0001 | WorkBuddy | User → ChatGPT | ✅ complete | N/A |
| ORG-CODEX-SETUP-0001 | WorkBuddy | User | ⏳ AGENTS.md conflict pending merge | N/A |

## Next proposed actions

1. User merges or rejects `AGENTS.candidate.md` → `AGENTS.md`.
2. Complete Codex desktop app upgrade (Microsoft Store / manual MSIX).
3. Evaluate TdxQuant or eltdx for real-time L2 tick data.
4. Initialize Git repository for `F:\aidanao`.
5. Add walk-forward validation to backtest framework.
6. Enable 2FA on purchased Codex account.
