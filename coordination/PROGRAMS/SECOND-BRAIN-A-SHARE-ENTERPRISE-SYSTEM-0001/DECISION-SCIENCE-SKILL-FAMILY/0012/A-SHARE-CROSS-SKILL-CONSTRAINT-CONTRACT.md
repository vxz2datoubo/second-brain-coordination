# A-share Cross-Skill Constraint Contract

Every DS contract must accept a versioned `RuleSnapshotRef` supplied by the
market-fact authority. W12 must not hard-code a timeless interpretation.

## Mandatory Dimensions

- exchange, board, security type and effective date;
- market phase and official session schedule;
- fresh versus seasoned sellable inventory under applicable settlement rules;
- price-limit regime, no-limit stage, suspension and resumption state;
- order unit, tick size, odd-lot and integer-share constraints;
- call auction, continuous auction, closing auction and after-hours mechanisms;
- commission, stamp tax, transfer fee, financing and other dated costs;
- short-selling eligibility, security eligibility, borrow availability and cost;
- point-in-time source capability, timestamps, sequence and entitlement;
- strict separation between research artifacts and order authority.

## Required Propagation

`DecisionFrame`, `ProbabilityEstimate`, `ResearchAuditReport`, `DecisionEpisode`,
W11 consumer records and candidate `LearningPacket` must retain the same rule
snapshot identifier and UNKNOWN fields. Downstream code may narrow permissions;
it may not infer a missing permission, sellable quantity or source capability.

## Forbidden Inferences

- T+1 does not imply that a security trades only once per day.
- Accumulated L2 counters are not raw trades, orders or cancellation events.
- Local receive time is not exchange event time.
- Risk-warning treatment is not one timeless percentage across boards and dates.
- A broker UI feature is not proof of a licensed programmable data capability.
- A research score is not an order instruction.

## Required Rule-Snapshot Objects

T+1 and turnover semantics are split across `market_turnover_rate`,
`portfolio_turnover`, `sellable_quantity` and `round_trip_eligibility`. A
`PositionLot` must retain trade date, total/settled/sellable/frozen/already-sold
quantities, turnaround eligibility and `rule_snapshot_id`.

`A_SHARE_RULE_SNAPSHOT` is versioned by exchange, board, security type and
effective interval. It must include settlement/turnaround, price limits, lot and
tick rules, sessions, suspension/resumption, fees/taxes, margin/borrow capability,
delayed clauses, source identity/hash and verification status.
