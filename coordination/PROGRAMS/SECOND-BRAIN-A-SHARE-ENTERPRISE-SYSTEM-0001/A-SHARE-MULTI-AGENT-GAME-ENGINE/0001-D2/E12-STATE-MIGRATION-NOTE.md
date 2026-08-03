# E12 Stateful Core Migration Note

## Decision

The E11 scaffold's single `working_inventory = agents[0].inventory` is removed.
`arbitrate` now keeps one `AgentPortfolioState` per declared `agent_id` and
calls the accepted D1 reducer only with the owning agent's inventory.

## Compatibility

`GameRun.final_inventory` remains a read-only compatibility projection only
when a run contains exactly one agent. It intentionally returns `None` for a
multi-agent run, preventing a caller from silently choosing a portfolio.

## Shared state

`SharedMarketState` is not a second market model. It holds only an immutable
D1 `MarketState` reference plus explicit synthetic conflict-resource claims.
No real liquidity, order book, identity, price, or market data is represented.

## Rollback

This change is isolated to `0001-D2`. Reverting the E12 remediation commit
restores the E11 scaffold without touching D1, QCLAW, WorkBuddy, or any
accepted authority surface. The migration is candidate-only and requires GPT
review before acceptance.
