# Demo Run Report

Two independent CLI runs used the same public-safe synthetic CSV fixture and produced identical core artifacts.

- `run_id`: `run-a94c97c5dae794eb`
- `event_hash`: `0a0aae5d37068940256d9b2f422d7851fd894c3bbd3e31c38e88c38c478a79ab`
- `evidence_hash`: `2096efdff8ea992cdfe288c9ccc6e269cea3cebbf2ad839f7ca9c9e4014f37e0`
- first output: `%TEMP%/p2-offline-demo-20260721-c`
- second output: `%TEMP%/p2-offline-demo-20260721-d`
- result: hashes identical; `ValidationReport.validation_status = EXPERIMENTAL_ONLY`

The run generated manifests, configuration, capability decisions, replay/decision/portfolio ledgers, validation, evidence, ContextBundle, candidate LearningPacket and a reproducibility manifest. It generated three simulated actions, but none is an order, advice, production strategy, or profitability claim.
