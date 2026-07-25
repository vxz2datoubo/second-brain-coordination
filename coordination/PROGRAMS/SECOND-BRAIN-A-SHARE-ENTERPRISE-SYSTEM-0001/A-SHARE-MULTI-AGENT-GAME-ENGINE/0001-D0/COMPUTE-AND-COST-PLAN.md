# Compute and Cost Plan

## D0 actual cost

D0 uses document parsing and static validation only. No ingestion, GPU allocation, simulation rollout, replay, source activation or model training is authorized.

## Future budgeting formula

Before a phase is approved, estimate `runs = scenarios × parameter_sets × seeds × folds × baselines`. Record estimated and hard-ceiling CPU/GPU hours, peak memory, disk for inputs/checkpoints/logs, retained artifact count, and operator review time. A missing estimate is a blocked gate, not a reason to use unbounded defaults.

| Stage | Scenario / parameter / seed policy | Ceiling and cancellation trigger | Retention |
| --- | --- | --- | --- |
| D1 synthetic MVP | Small deterministic fixtures; one parameterized ruleset; fixed seed unnecessary. | Unit-test duration and memory ceiling set in task. Cancel on nondeterminism or invariant failure. | Source plus concise test receipt. |
| D3 replay calibration | Registered scenarios, variants, folds and seeds only. | Stop when data-admission, leakage or cost-unit gate fails. | Manifests, hashes, summaries; raw restricted data excluded. |
| D4 opponent models | Parameter/seed counts preregistered with baseline comparison. | Stop on calibration regression, coverage failure or variant-budget breach. | Registered configs and aggregate metrics. |
| D5 self-play | Fixed scenario/seed grid and checkpoint schedule. | Stop at compute ceiling, nonreproducibility, exploitability regression or no incremental value. | Hashes, selected checkpoints under approved policy. |
| D6 MARL decision | No training budget exists by default. | Requires independent approval and user budget. | ADR/rejection report before any run. |

No coefficient, hardware throughput, market-impact cost or runtime estimate is invented in D0. The next task must attach measured or explicitly assumed values with units and uncertainty.
