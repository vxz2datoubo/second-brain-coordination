# P0 Incident Closure Status

`agent_id: CODEX`

## Historical Attribution

The historic 119-Python-process incident has no preserved PID tree, command ledger, resource time series, or owner registry in the E59 evidence set. Its exact causal attribution is therefore `HISTORICAL_ATTRIBUTION_UNRECOVERABLE`. This is not a statement that a cause is absent; it is a refusal to invent one.

## Current Prevention Evidence

The bounded E59 canary was run locally from `tools/run_p0_canary.py`. Each tree contains one root and two Python grandchildren. Peak owned process count was 3, below the single-agent cap of 6 and global cap of 8. Each completed scenario recorded zero owned processes and zero orphans after cleanup; no unrelated process was terminated.

Verified current categories:

| Category | Current experimental result |
|---|---|
| `NESTED_PARALLELISM` | Nested worker fan-out is disabled; the canary permits only two observed grandchildren. |
| `ORPHAN_ON_ERROR_TIMEOUT_OR_CANCEL` | Timeout, controlled exception, and controlled Ctrl-C all performed context cleanup with zero orphans. |
| `REPEATED_LAUNCH_ACCUMULATION` | Two consecutive canaries each returned to zero owned processes. |
| `DUPLICATE_PERSISTENT_DAEMON` | A second owner was rejected by `SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK`. |
| `DUAL_AGENT_HEAVY_STAGE_COLLISION` | A contender sharing the same project mutex was rejected. |
| `ROOT_EXIT_FIRST` | Two grandchildren were discovered before the root exited and remained owned until cleanup. |

## Remediation Evidence

The provisional receipt Provider exposed a valid mutex contention path. The remediation keeps contention fail-closed, but waits at most 30 seconds for a legitimate holder rather than stealing or deleting its lock. Full desktop process scans now enumerate only topology; creation times are read only for a candidate root or descendant before it becomes owned. This retains PID-reuse protection while avoiding a scan delay that could hide short-lived descendants.

The resource protocol requires CPU throttling only after CPU is above 70% for 15 seconds. The gate now records that sustained window instead of rejecting a single 50ms sample. A transient 100% preflight sample occurred during the latest canary; the seven bounded cases completed and postflight was 62.07%. This is evidence for the bounded synthetic canary only, not a claim about system-wide process behavior.

## Limits Of This Closure

This proves only the present, bounded synthetic controls. It does not prove the historical incident cause, deployed-service behavior, or ownership of processes from other projects. A future failure that leaves an owned descendant after grace is a stop condition, not a warning to ignore.
