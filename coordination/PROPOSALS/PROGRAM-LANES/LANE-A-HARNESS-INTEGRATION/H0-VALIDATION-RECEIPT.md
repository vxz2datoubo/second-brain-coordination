# H0 Validation Receipt — Control Tower Fail-Closed Evidence

- status: `EXPECTED_FAIL_CLOSED / CONTROL_PLANE_RECONCILIATION_BLOCKER_CONFIRMED`
- PR: `#336`
- validated proposal head: `67fdbf8a3b3284ea73a0239eca01cc4684433691`
- PR merge test ref: `b0c9c2f64eac6d169641ec5b492c552c4eb4ac3e`
- canonical base/main: `823d5b22c7b449626bc03cdf1f574c592e50b9fc`
- GitHub Actions run: `31877439648`
- workflow: `Program Control Tower foundation`
- Python: `3.11` and `3.13`
- boundary: `PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION / NO_TRADE`

## Result

Both Python 3.11 and Python 3.13 jobs failed at the same stage:

`Reconcile current canonical control-plane state`

The preceding targeted regression suite passed:

- `20 tests`
- `20 PASS`
- collision O0-O4 tests PASS
- route/witness freshness tests PASS
- stale route epoch fail-closed test PASS
- proposal-isolation tests PASS

Therefore the workflow failure is **not** evidence that the H0 proposal YAML/docs broke the Control Tower test suite.

## Exact Control Tower blocker

Control Tower emitted:

- check: `CT-R01-STALE-VIEW`
- code: `PROGRAM_REGISTRY_ROUTE_DRIFT`
- severity: `ERROR`
- message: `Program registry observed state is stale relative to the per-agent ACTIVE route.`

Observed drift for CODEX:

| Field | Current per-agent ACTIVE route | Program registry expected |
|---|---:|---:|
| issue | 332 | 305 |
| pr | null | 307 |
| route_epoch | 132 | 120 |
| status | READY | READY_REMEDIATION |
| task_id | `...P2-4B-STRUCTURAL-ANALOGY` | `...P2-2-EPISTEMIC-MATERIALITY-HARDENING` |

The check exited with code `2`, so downstream steps were skipped:

- Validate Program Lane work claims
- Verify work-claim bulletin projection
- Verify durable authorization witness round trip
- Emit Codex route witness

This is correct fail-closed behavior.

## Additional stale-state evidence outside this CI comparison

The CI reconciliation treats `ACTIVE-CODEX-TASK.yaml` as the current per-agent route and therefore only proves the Program registry is stale relative to R132.

A separate, stronger closure fact also exists:

- PR #334 P2.4B is already merged to canonical main `823d5b22c...`;
- Issue #335 Foundation Closure is completed with verdict `CLOSED_WITH_BOUNDED_GAPS`;
- Issue #335 explicitly states `ACTIVE-CODEX-TASK.yaml` still projecting R132 as READY is itself a stale control-plane cleanup item and must not allow another `读取任务`.

Therefore remediation must not merely update Program registry from R120 -> R132 READY. The correct semantic cleanup is:

1. preserve R132 as completed history;
2. neutralize the executable R132 projection;
3. close Lane C heavy implementation lease;
4. record Foundation as closed/frozen with bounded gaps;
5. mark Lane A as active **proposal-only architecture design**;
6. preserve Lane B hold unless separately started;
7. then rerun reconciliation/claims/witness.

## Safety interpretation

This failed workflow is a **positive safety signal**:

> The Control Tower detected stale control state and blocked later authorization/witness steps rather than pretending the proposal was ready to execute.

It does **not** authorize changing canonical Control Tower files from Lane A.

## Required next validation after authorized cleanup

After a separately authorized bounded control-plane remediation:

1. fetch current main and all ACTIVE routes;
2. run Control Tower targeted regressions on Python 3.11 and 3.13;
3. run canonical reconciliation;
4. validate Work Claims;
5. verify bulletin projection;
6. verify durable authorization witness round trip;
7. run O0-O4 / WIP / heavy-resource checks;
8. confirm no active Codex execution lease remains unless a new task was explicitly released;
9. confirm Lane A remains proposal-only;
10. rerun H0 static audit and final compatibility verdict.

Until then:

`H0_FINAL_ACCEPTANCE = NOT_READY`

`H1/H2_IMPLEMENTATION_RELEASE = FAIL_CLOSED`
