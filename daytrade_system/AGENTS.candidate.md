# AGENTS.md — 交易子系统作用域

> 此为候选版本 (candidate)。
> 仅适用于 `daytrade_system/` 及其子模块。

## Scope

This file governs the trading engine, backtest framework, simulation environment, and production trading modules under `daytrade_system/`.

---

## A-share market invariants

### T+1 settlement
- Shares purchased today cannot be sold until next trading day.
- Intraday round-trip (倒T: sell-then-buy) is the primary strategy for T+0-like operations.
- Cash settlement: sold shares fund availability on T+1.

### Price limits
- Main board (±10%), ChiNext/STAR (±20%).
- ST stocks: latest rules — ±10% baseline. Runtime priority: `upper_limit_price` / `lower_limit_price` from market data → versioned rule engine. Mismatch → block trade + alert. Backtests use historically effective rules valid on each trading day.
- Limit-up: buy orders may not fill. Limit-down: sell orders may not fill.
- Backtests must simulate queue position and fill probability at limits.

### Suspensions
- Trading halts render assets illiquid. Backtests must mark suspension periods and exclude them from strategy evaluation.
- Extended suspensions (>5 trading days) should trigger position review.

### Special designations (ST, *ST, delisting)
- ST and *ST stocks: apply board-specific and period-specific limit rules from versioned engine. Runtime uses `upper_limit_price` / `lower_limit_price`. No hardcoded percentage.
- Delisting risk must be flagged before entry.

---

## Backtest and simulation standards

### Data quality requirements

| Requirement | Standard |
|-------------|----------|
| Point-in-time data | News, financials, constituents at their PIT availability |
| Survivorship bias | Include delisted and suspended stocks |
| Look-ahead leakage | Zero tolerance — any found → fix before results accepted |
| Reproducibility | Data snapshot hash + code commit + config + seed |

### Performance evaluation

| Metric | Threshold | Notes |
|--------|-----------|-------|
| Walk-forward period | ≥ 12 months | Or genuinely held-out test set |
| Minimum trades | ≥ 30 in test set | Smaller = statistically unreliable |
| Cost modeling | Mandatory | Commission (0.03%), stamp duty (0.1% sell), slippage (min 0.1%) |
| Price limit handling | Mandatory | Simulate queue rejection at limits |
| Suspension handling | Mandatory | Mark and exclude from metrics |

### Statistical controls
- Multiple-testing correction for parameter searches
- Separate: research metrics (IC, Sharpe) ≠ executable strategy P&L
- Report: confidence intervals, not just point estimates

---

## Production readiness gates

A strategy advances through gates:

| Gate | Name | Requirements |
|------|------|-------------|
| G0 | Backtest | Walk-forward P&L positive; costs included; ≤5% degradation from in-sample |
| G1 | Paper simulation | Live data feed, paper trading for ≥20 trading days without degradation |
| G2 | Shadow mode | Real-time signals logged, post-hoc P&L computed, no real orders |
| G3 | Production | User-approved, monitored, with circuit breakers active |

Each gate transition requires **user approval**.

---

## Trading cost model

| Cost | Rate | Applied |
|------|------|---------|
| Commission (buy) | 0.03% | Per transaction |
| Commission (sell) | 0.03% | Per transaction |
| Stamp duty (sell) | 0.10% | Per sell transaction |
| Slippage | Min 0.1% | Per round-trip |
| Queue rejection | Simulated at price limits | At limit-up/l-down |

---

## Risk management parameters

See config files (NOT this document):

- `config/trading/risk_limits.yaml`
- `config/trading/session_windows.yaml`
- `config/trading/strategy_parameters.yaml`

---

## Code and testing

### Required test coverage

| Component | Test type | Minimum |
|-----------|-----------|---------|
| Trade execution | Unit | All paths |
| Cost calculation | Unit | All cost components verified |
| Risk checks | Unit | Circuit breaker triggers verified |
| Backtest runner | Integration | Full pipeline run with known output |
| Data pipeline | Integration | Schema validation |

### Test commands

```bash
# Run all trading system tests
python -m pytest daytrade_system/tests/ -v

# Run backtest smoke test
python daytrade_system/runner.py --stock 300418 --days 20 --mode paper
```

---

## WorkBuddy execution boundary

WorkBuddy may:
- Run backtest scripts and collect results.
- Package and report test output.
- Monitor live data and generate alerts.
- Update `coordination/SYSTEM-STATE.md` with current test status.

WorkBuddy may NOT:
- Modify trading strategy logic.
- Bypass production readiness gates.
- Execute real-money orders (user approval required).
- Change risk parameters without user review.

---

**Version**: candidate v1 | **Task**: ORG-CODEX-MERGE-0002 | **Status**: ⏳ Awaiting user approval
