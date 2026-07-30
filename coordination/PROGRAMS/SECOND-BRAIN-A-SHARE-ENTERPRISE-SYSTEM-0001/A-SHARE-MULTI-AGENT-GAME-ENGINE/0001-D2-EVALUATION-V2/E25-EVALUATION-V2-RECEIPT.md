# E25 Evaluation V2 Gate B-R3 Receipt

- `task_id`: `CODEX-D2-EVALUATION-V2-CONTROLLED-VIOLATION-TRACE-PROVENANCE-AND-EVIDENCE-PRESERVATION-CLOSURE-0017-E25`
- `agent_id`: `CODEX`; `route_epoch`: `26`
- `PR`: [#106](https://github.com/vxz2datoubo/second-brain-coordination/pull/106) (Draft); [Issue #23](https://github.com/vxz2datoubo/second-brain-coordination/issues/23)
- `branch`: `codex/d2-evaluation-v2-0014-e22`
- `reviewed_base`: `3dd2bf116d018a2dfa132cdbb22de5fd11547d61`
- `remote_main_read_at_start`: `114b040a813bbb03457b422ca73c8e8c072a5962`
- `tested_commit`: `5c10a31326eb873fd02233a445f9a5d6c17a1c3c`
- `tested_parent`: `3dd2bf116d018a2dfa132cdbb22de5fd11547d61`
- `CI`: [run 30577091133](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/30577091133), success.
- `boundary`: `PUBLIC_SAFE / SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`

## Delivered Remediation

1. Ten predicate IDs have real controlled-artifact constructors and
   object-derived named failure oracles. No caller boolean or boolean inversion
   is used as proof.
2. All 80 invariant rows execute a valid predicate and a derived bad object;
   the named oracle reads a concrete failing object and reason code.
3. Episode and counterfactual signatures use exact retained first-execution
   objects. They neither rerun episodes nor rebuild inputs from a parallel
   formula.
4. An abstaining alternative action is represented as `order=None`.
5. E22/E23/E24 adverse findings are retained in cumulative ledgers.

## Evidence Status

| Evidence | Result | Detail |
| --- | --- | --- |
| Focused local suite | PASS | `49` tests, direct exit `0`, Python `3.13.13` |
| Public runner | PASS | exit `0`, report SHA `85b734d1ea80b71869e6794a639f72cfa23b0664478adfcd42bb9cca3d6facb7` |
| Runner stream capture | PASS | stdout `31bec3448b929d1bd30069b348b5074a66a83ce136e934278475053af3d7c62a`; stderr empty SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| GitHub Actions | PASS | run `30577091133` completed successfully |
| Clean archive rerun | NOT_ACCEPTED | Windows binary tar pipeline corrupted archive data; ZIP retry plus capture exceeded local timeout. No archive pass is claimed. |

This receipt's own SHA is anchored only after its push. Gate C, Gate D, Issue
#92, real data, replay, backtest, fitting, accounts, orders, and trading remain
frozen or prohibited.

Completion signal:
`CODEX_E25_D2_EVALUATION_V2_CONTROLLED_VIOLATION_TRACE_PROVENANCE_AND_EVIDENCE_PRESERVATION_READY_FOR_GPT_REVIEW`

Rollback: revert this receipt-only commit, then revert
`5c10a31326eb873fd02233a445f9a5d6c17a1c3c`. No external or runtime state
exists to restore.
