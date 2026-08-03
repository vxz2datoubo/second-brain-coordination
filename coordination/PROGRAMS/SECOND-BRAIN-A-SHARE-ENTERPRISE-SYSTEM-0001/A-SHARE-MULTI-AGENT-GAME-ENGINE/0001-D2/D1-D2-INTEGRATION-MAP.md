# D1 To D2 Integration Map

D2 does not duplicate a market-state, inventory, matching, rule, calendar, or
replay engine. It imports D1's immutable `MarketState`, `InventoryState`,
`SyntheticOrder`, outcome contracts, and the single `reduce_order` reducer.

| D2 responsibility | Reused D1 surface | Boundary |
| --- | --- | --- |
| Feasibility and synthetic transition | `reduce_order` | D2 cannot bypass D1 validation. |
| Session, price-limit, suspension and T+1 rules | D1 rule/calendar/inventory modules | Synthetic snapshots only. |
| Participant hypotheses and information sets | D2 only | Not participant facts. |
| Per-agent portfolio transition | D2 owns a mapping of D1 `InventoryState` values | An action is reduced against its owning portfolio only. |
| Shared conflict arbitration | D2 `SharedMarketState` | The sole shared mutable resource is a declared synthetic conflict key. |
| Arbitration/event sourcing | D2 only | Arrival sequence is declared and unique; no lexicographic ID priority. |
| Counterfactual episodes | D2 only | Carries prior portfolios and causal event IDs between bounded steps. |

The D1 dependency blobs were individually compared with the exact accepted D1
receipt base before D2 local execution. This map does not authorize market data,
historical replay, backtesting, or order execution.
