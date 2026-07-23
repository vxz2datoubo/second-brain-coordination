# Next Vertical Slice Selection

> agent_id: `CODEX`
>
> decision: `SELECT_EXACTLY_ONE`
>
> selected: `0017 BAR_ONLY reference-zone breach/reclaim plus T+1 validation`
>
> implementation_issue: `#69`, only after new explicit routing
>
> boundary: `research_only / NO_TRADE`

## Decision

The next business vertical slice should be the narrow BAR_ONLY portion of module 0017. It tests observable reference-zone breach, reclaim/failure, post-event stabilization and T+1-aware executability using the existing W2 replay path, W4 experiment ownership and W7 validation authority. It does not infer hidden stops, participant identity, raw order flow or intent.

This document selects a candidate; it does not activate or implement it. GPT selects 0017 under documented uncertainty: QCLAW PR #75 supplies substantive candidate counterevidence, but preregistered procedural independence was not proven. Release requires explicit GPT approval of this R1 correction and the current route's stated preregistration gate or a documented bounded waiver.

## Scoring method

Each candidate is scored out of 100: data readiness 25, runtime reuse 20, point-in-time feasibility 15, A-share rule/cost readiness 15, isolated incremental-value testability 10, dependency readiness 10, rollback simplicity 5.

| Candidate | Data | Reuse | PIT | Rules/cost | Isolated test | Dependencies | Rollback | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0017 BAR_ONLY breach/reclaim | 20 | 18 | 12 | 13 | 8 | 8 | 5 | **84** |
| W12 one DS child | 18 | 8 | 14 | 5 | 7 | 5 | 5 | 62 |
| W13 official participant bulletin | 12 | 5 | 8 | 8 | 7 | 5 | 5 | 50 |
| W11 single-opportunity NetEV/Kelly | 6 | 4 | 12 | 10 | 7 | 2 | 5 | 46 |
| PMN official policy calendar | 10 | 4 | 4 | 5 | 7 | 4 | 5 | 39 |
| 0018 net-edge/survival report | 4 | 2 | 10 | 8 | 5 | 1 | 5 | 35 |

Scores are governance estimates, not measured economic value. They can be invalidated by new source, license, runtime or independent-audit evidence.

## Why 0017 wins now

1. The public repository already has deterministic bar replay, local `.day` adaptation and basic A-share T+1/session/cost guards.
2. BAR_ONLY excludes L2/order-book and displayed-depth dependency, raw tick/order events, L3, DDX/DDY, synthetic Delta/CVD/OFI, participant identity, hidden-stop claims and main-force intent; it only labels observable point-in-time bar behavior.
3. The hypothesis can be falsified with an event-study baseline, purged/walk-forward splits, regime partitions, costs and abstention.
4. It does not wait for W5/W13 collectors, W12 probability, W10 decision ledger, W11 allocation or 0018 survival controls.
5. Failure is informative and cheap: the slice can be retired without changing shared authorities.

## Required scope for the routed follow-up

- Define reference zones only from point-in-time bars available before the event.
- Use a preregistered simple baseline before parameter combinations.
- Preserve failed reclaim, no-reclaim and continuation cases.
- Model Fresh versus Seasoned inventory constraints without claiming exact holder intent.
- Include costs, slippage sensitivity, limit/suspension constraints, unexecutable exits and T+1.
- Use purged or walk-forward out-of-sample evaluation and report multiple-testing exposure.
- Produce a W4 experiment family and W7 validation report; no signal may bypass W7.
- Keep probability, allocation and order generation out of scope.

## Rejected-at-this-time alternatives

- **W12 child:** valuable enabling work, but PR #66 is not on main and it is not the strongest first A-share business slice.
- **W13:** official participant evidence is valuable, but source/field/identity-confidence adapters are absent.
- **PMN:** point-in-time expectation reconstruction and revision handling are more expensive than current runtime reuse supports.
- **W11:** blocked by shared probability, rule snapshot and W7 risk envelope.
- **0018:** deliberately downstream of W12, W11, W7 and W9; starting it now would create duplicate logic.

## Acceptance and kill conditions

Promote only if the slice passes deterministic replay, no-future-data checks, rule-version and cost gates, multiple periods/regimes, out-of-sample validation and a simple-baseline comparison. Freeze or retire it if edge disappears after costs, depends on unavailable fields, fails repeated OOS checks, or only survives post-hoc parameter selection.
