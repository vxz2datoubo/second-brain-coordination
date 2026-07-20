# Decisions

1. **Single stdlib implementation:** keeps the public reference executable in an empty coordination repository and avoids a parallel dependency stack.
2. **Synthetic data only:** the fixture is labelled `CC0-1.0` and `synthetic`; results cannot support a market or profitability claim.
3. **Execution stays simulated:** actions are strings and ledgers; no adapter exposes an order-shaped network call.
4. **P1 contracts are adapted, not copied:** `ContractRuntime` emits envelope projections while existing local domain ownership remains untouched.
5. **Knowledge gateway is an in-memory synthetic demonstration:** it implements Issue #38's public-safe subset; private/local access remains a future WorkBuddy/GPT integration.
6. **Rejected alternative:** no vector database, cloud service, real data adapter, or MARL component is introduced because each would exceed P2's public-safe offline boundary.
