# D1 To D2 Integration Map

D2 does not duplicate a market-state, inventory, matching, rule, calendar, or
replay engine. It imports D1's immutable `MarketState`, `InventoryState`,
`SyntheticOrder`, outcome contracts, and the single `reduce_order` reducer.

| D2 responsibility | Reused D1 surface | Boundary |
| --- | --- | --- |
| Feasibility and synthetic transition | `reduce_order` | D2 cannot bypass D1 validation. |
| Session, price-limit, suspension and T+1 rules | D1 rule/calendar/inventory modules | Synthetic snapshots only. |
| Participant hypotheses and information sets | D2 only | Not participant facts. |
| Arbitration/event sourcing | D2 only | Stable synthetic ledger, not order flow. |
| Counterfactual episodes | D2 only | Changes declared assumptions, not history. |

The D1 dependency blobs were individually compared with the exact accepted D1
receipt base before D2 local execution. This map does not authorize market data,
historical replay, backtesting, or order execution.
