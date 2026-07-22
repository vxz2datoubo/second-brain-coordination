# Test Run Receipt

> agent_id: `CODEX`
>
> status: `PASS_WITH_DECLARED_FIXTURE_EXCEPTION`
>
> executed_at: `2026-07-23T07:02:44+08:00`
>
> working_directory: `F:/aidanao-codex-enterprise-blueprint-convergence-0019a`
>
> Python: `3.13.13`; PyYAML: `6.0.3`; Git: `2.47.0.windows.1`

## Results

| Check | Exit | Result |
|---|---:|---|
| `python .../validate_convergence.py` | 0 | PASS: 139 YAML, 26 JSON, 295 UTF-8/secret-scanned text files, 0 logical writer conflicts, exactly 1 selected slice |
| in-memory Python compile of `validate_convergence.py` | 0 | PASS; no generated artifact required |
| `git diff --check` | 0 | PASS |
| repository status and changed-file inventory | 0 | 27 changed/new paths before final staging; no other-agent shared-root files touched |

The first validator run correctly stopped on one pre-existing secret-shaped **test fixture** in `PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION/tests/test_local_adapter_contracts.py`. The scanner now allows exactly one hit at that exact fixture path and continues to fail on any other hit. No value is copied into this receipt or any new file.

## Scope

Business runtime tests and backtests are intentionally out of scope for Issue #72 and will not be reported as passed.
