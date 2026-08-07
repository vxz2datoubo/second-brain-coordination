# E58 P0 bounded canary receipt

| Field | Value |
| --- | --- |
| agent_id | `CODEX` |
| task_id | `CODEX-E57-POST-RECEIPT-SEMANTIC-EXECUTION-VERIFIER-CAPABILITY-RAW-JSONL-AND-DUAL-PROVIDER-CLOSURE-0054-E58` |
| executed_at_local | `2026-08-07 Asia/Shanghai` |
| execution mode | `synthetic local P0 canary only` |
| baseline Python count | `0` |
| postflight Python count | `0` |
| preflight available RAM | `23.470 GiB` |
| preflight CPU estimate | `12%` |
| worker cap | `2` concurrent canary children; `3` CPU-bound and `6` task-owned Python hard caps |
| observed containment | `process_group_fallback` after Job Object assignment returned `ERROR_ACCESS_DENIED (5)` under the desktop host outer Job |
| unrelated process termination | `none` |
| result | `PASS` |

## Exact command

```text
python -m unittest discover -s tests -v
```

The launcher set `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`,
`VECLIB_MAXIMUM_THREADS=1`, `LOKY_MAX_CPU_COUNT=1`, and
`TOKENIZERS_PARALLELISM=false` before launch.

## Result

`10` tests passed in `0.187s`, exit code `0`.

| Stream | SHA-256 |
| --- | --- |
| stdout | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| stderr | `30bc9e7649fc6639a6326443e77b22e447fc2e585ebde7bf3d06363421ab4874` |

Covered outcomes are normal exit, unexpected exit, timeout cleanup, ordinary
exception/cancellation, `KeyboardInterrupt`, two-worker cap rejection, mutex
contention, idempotent close, command-digest redaction, and explicit containment
mode. The two timeout-like fixtures are task-owned child processes only; their
Popen handles are reclaimed by the registry before postflight.

## Interpretation

The historical 119-process incident remains
`UNKNOWN_PENDING_INSTRUMENTED_REPRODUCTION`: no historical PID tree survives.
This receipt establishes only that the E58-local lifecycle boundary now has a
bounded, forward-looking test and returns its owned child count to zero. It does
not attribute the historical incident to E57 or to any other Agent.
