# A-share Microstructure Simulator Plan

Status: `Future Roadmap`. D0 supplies no simulator, historical input or executable rule value.

## Synthetic rules MVP boundary

The D1 MVP is a deterministic state reducer. It receives a synthetic `RuleSnapshotRef`, never a timeless hard-coded A-share rule, and produces a next state plus an auditable `InvalidOrBlockedActions` list. It models *feasibility*, not profitable execution or true market intent.

### State tuple

`MarketState = {event_time, available_at, market_phase, rule_snapshot_ref, security_status_ref, price_limit_state, halt_state, book_view, data_capability, lineage, unknown_flags}`

`AgentState = {archetype_hypothesis_ref, hidden_type_posterior, objective_hypotheses, information_set_ref, evidence_refs, counterevidence_refs, abstention_reason}`

`InventoryState = {seasoned_quantity, fresh_quantity, locked_quantity, pending_buy_quantity, pending_sell_quantity, settlement_day, unknown_flags}`

`InformationSet = {observable_fields, available_at_cutoff, source_capabilities, withheld_or_unknown_fields, rule_snapshot_ref}`.

No tuple may silently fill an UNKNOWN with zero, current-date values or a locally received timestamp.

## Market-phase transition state machine

| From | To | Guard | Output restriction |
| --- | --- | --- | --- |
| `pre_open` | `call_auction` | Synthetic snapshot declares auction open. | Only auction-valid order intents considered. |
| `call_auction` | `continuous_auction` | Synthetic snapshot declares continuous session. | Unmatched auction intents become explicitly cancelled, carried or UNKNOWN per snapshot. |
| `continuous_auction` | `midday_break` | Synthetic schedule transition. | New matching disabled; pending semantics explicit. |
| `midday_break` | `continuous_auction` | Synthetic schedule transition. | No fabricated trades during break. |
| `continuous_auction` | `closing_auction` | Snapshot explicitly supports this phase. | Otherwise state remains continuous/UNKNOWN. |
| any open phase | `halted` | Security-status snapshot says halted. | Matching, new order acceptance and price inference blocked. |
| `halted` | open phase | Synthetic resumption evidence. | Never infer resumption from a clock alone. |
| final phase | `post_close` | Session closure. | Fresh inventory becomes next-day eligible only when snapshot semantics permit. |

## Order validity and matching semantics

1. Validate phase, halt state, price-limit band, order side, quantity, tick/lot rule, inventory availability and data capability **in that order**. The first failed prerequisite returns `invalid_or_blocked` with its reason.
2. A valid intent is not a fill. Matching returns one of `filled`, `partially_filled`, `unfilled_cancelled`, `unfilled_carried`, or `unknown_outcome`; the snapshot chooses which outcomes are allowed.
3. A sell consumes only `seasoned_quantity` when the applicable rule snapshot makes fresh same-day inventory ineligible. `fresh_quantity` remains visible and cannot be relabeled as seasoned by a price move.
4. Price-limit and suspension values are inputs from `RuleSnapshotRef` and `security_status_ref`; when either is UNKNOWN, dependent actions abstain.
5. No synthetic fill implies queue priority, raw order flow, counterpart identity, exchange matching algorithm detail or real-world execution quality.

## Fixture catalogue for D1

| Fixture ID | Synthetic scenario | Required assertion |
| --- | --- | --- |
| FX-01 | Pre-open action | No continuous-session match occurs. |
| FX-02 | Call-auction valid buy | Outcome follows explicit auction rule, never assumed fill. |
| FX-03 | Auction unmatched intent | Cancellation/carry state is explicit. |
| FX-04 | Continuous partial fill | Filled and residual quantities conserve total intent. |
| FX-05 | Continuous no fill | Inventory and cash hypotheses remain unchanged except declared reservation. |
| FX-06 | Price-limit blocked buy/sell | Limit-state action is blocked with snapshot reference. |
| FX-07 | Halt transition | New matching is blocked; pending order semantics explicit. |
| FX-08 | Fresh-lot same-day sale | Rejected when synthetic rule snapshot forbids it. |
| FX-09 | Seasoned-lot sale | May remain feasible subject to all other guards. |
| FX-10 | Cross-day transition | Eligible inventory changes only through declared settlement transition. |
| FX-11 | UNKNOWN rule snapshot | Dependent action abstains, not defaults to valid. |
| FX-12 | Competing participant hypotheses | Same observable state emits alternatives, not an identity label. |

## Minimum invariant suite

The D1 test task must include at least these twenty negative/positive invariants: conservation of inventory; non-negative buckets; fresh/seasoned separation; no same-day fresh sell when prohibited; no fill while halted; no matching during break; no price outside synthetic band; no trade before `available_at`; deterministic transition for equal input; phase transition legality; explicit pending outcome; partial-fill conservation; no implicit carry; no unknown-to-zero coercion; rule snapshot presence; security-status presence; source capability gate; no identity promotion; counterevidence retention; and no direct order output.

## Promotion gates

Synthetic D1 may advance only after fixture and invariant evidence. Empirical replay additionally requires permitted point-in-time data, rule/security snapshots, availability timestamps, deterministic replay, costs and independent validation. Level-k, self-play and MARL remain blocked behind D3-D6 and must not consume this document as evidence of readiness.
