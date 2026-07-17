# YAML_VALIDATION — 3 Candidate YAML 语法与逻辑验证

> Task: ORG-CODEX-REVIEW-PACK-0003 | Date: 2026-07-16 03:55 UTC+8

## Validation Summary

| File | Syntax | Dup Keys | Tabs | Candidate State | Issues |
|------|:------:|:--------:|:----:|:---------------:|--------|
| risk_limits.candidate.yaml | ✅ PASS | None | None | ✅ All parameters `status: candidate` | 1 false positive (see below) |
| session_windows.candidate.yaml | ✅ PASS | None | None | ✅ All sessions candidate | None |
| strategy_parameters.candidate.yaml | ✅ PASS | None | None | ✅ All parameters `status: candidate` or `candidate_pending_*` | 1 false positive (see below) |

## Fields and Types

### risk_limits.candidate.yaml (98 lines)
```
parameters:
  position (dict, 3 items)
    single_trade_amount: {value: 5000, unit: CNY, status: candidate}
    max_daily_t_trades: {value: 3, unit: trades, status: candidate}
    max_total_exposure: {value: 0.90, unit: ratio, status: candidate}
  drawdown (dict, 3 items)
    daily_drawdown_circuit_breaker: {value: 0.02, unit: ratio, status: candidate}
    consecutive_loss_circuit_breaker: {value: 3, unit: trades, status: candidate}
    consecutive_loss_days_position_reduction: {value: 2, unit: days, status: candidate}
  stop_conditions (dict, 2 items)
    intraday_drop_no_add: {value: 0.05, unit: ratio, status: candidate}
    stop_loss_check_threshold: {value: 0.07, unit: ratio, status: candidate}
  cooling_periods (dict, 1 item)
    post_sell_cooldown: {value: 30, unit: minutes, status: candidate}
```
✅ All `effective_from`, `source`, `approved_by`, `last_validated_at` fields present.

### session_windows.candidate.yaml (78 lines)
```
sessions (dict, 8 items)
  T1-T8 each: {start, end, strategy, priority, description}
call_auction (dict, 3 items)
  phase_1/phase_2/execution: {start/end/time, description}
```
✅ All time values in HH:MM format. Priority values 1-5.

### strategy_parameters.candidate.yaml (83 lines)
```
position_allocation (dict, 2 items)
  kunlun_300418: {value: 0.60, unit: ratio, status: candidate}
  bluefocus_300058: {value: 0.40, unit: ratio, status: candidate}
confidence_levels (dict, 5 items)
  A_plus_plus/A/B/C/D: {threshold, unit: score, action}
t_strategy (dict, 3 items)
  inverted_t_priority/inverted_t_caution/sell_fly_handle
market_states (dict, 5 + note)
```
✅ All candidate/inactive. `note` field properly indicates undefined quant criteria.

## Unit Verification

| Parameter | Value | Unit | Correct? |
|-----------|-------|------|:--------:|
| single_trade_amount | 5000 | CNY | ✅ |
| max_total_exposure | 0.90 | ratio (90%) | ✅ |
| daily_drawdown | 0.02 | ratio (2%) | ✅ |
| intraday_drop_no_add | 0.05 | ratio (5%) | ✅ |
| stop_loss_check | 0.07 | ratio (7%) | ✅ |
| post_sell_cooldown | 30 | minutes | ✅ |
| confidence thresholds | 90/75/60/45/0 | score | ✅ |
| position weights | 0.60/0.40 | ratio | ✅ |

## False Positives from Automated Scanner

- **risk_limits.yaml**: Scanner flagged `value: 5000` and `value: 3` as "ratio values may be percentage" — but these use `unit: CNY` and `unit: trades` respectively, not ratio. **No action needed.**
- **strategy_parameters.yaml**: Scanner flagged `value: 40` — this is `unit: score`, not ratio. **No action needed.**

## Verification

✅ All 3 YAML files maintain `candidate`/`candidate_pending_*` status
✅ No duplicate keys
✅ No tab characters
✅ All numeric values match their declared units
✅ All parameters have provenance tracking fields
✅ No file will auto-activate on deployment
