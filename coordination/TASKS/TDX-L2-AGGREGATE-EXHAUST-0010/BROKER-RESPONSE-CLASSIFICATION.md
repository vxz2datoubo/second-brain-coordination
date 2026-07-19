# Broker Response Classification

Use `brain_core.realtime_l2_aggregate.classify_broker_market_data_response`
after WorkBuddy fills `BROKER-RESPONSE-SCHEMA.json` for a broker.

## Inputs

The classifier expects the JSON fields from `BROKER-RESPONSE-SCHEMA.json`:

- API surface
- market-data-only mode
- field coverage
- timestamp and sequence semantics
- cost and entitlement terms
- license permissions
- evidence file paths

## Conservative Rules

- A verbal "Level-2 is supported" answer is not enough.
- Raw trade ticks, raw order events, order queue, cancel events, and auction
  trajectory remain candidates until field docs, SDK docs, sample payloads, and
  license terms are attached.
- If account/order functions are required in the same process, the route is
  blocked until the broker provides a market-data-only mode.
- If local storage or automation permission is unknown, the route remains
  `needs_review`.
- Public crawler routes are not classified here. They remain
  `auxiliary_crosscheck_only`.

## Route Status

| Status | Meaning |
|---|---|
| `insufficient` | No meaningful capability evidence. |
| `needs_review` | Some useful market data exists, but raw L2 evidence or license boundaries are incomplete. |
| `raw_l2_candidate_needs_runtime_probe` | Broker reply includes docs, sample payload paths, timestamp semantics, and license boundaries. Codex still needs runtime validation before promotion. |
| `blocked` | Route requires account/order functions in the same process or otherwise violates safety boundaries. |

## Promotion Boundary

Even `raw_l2_candidate_needs_runtime_probe` is not production-ready. It only
means the next Codex/WorkBuddy task can run a read-only probe against broker
sample data or a sandbox market-data endpoint.

No route may enable live trading, order submission, account query, position
query, or broker login automation from this classification step.
