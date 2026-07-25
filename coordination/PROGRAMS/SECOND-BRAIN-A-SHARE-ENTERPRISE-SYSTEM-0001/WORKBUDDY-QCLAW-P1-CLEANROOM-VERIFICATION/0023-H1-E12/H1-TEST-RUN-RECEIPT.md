# H1-E12 Test Run Receipt

| Field | Value |
|-------|-------|
| task_id | WORKBUDDY-QCLAW-P1-CLEANROOM-H1-E12-FRESH-BRANCH-FAIL-CLOSED-VERIFIER-R1 |
| receipt_head_ref | THIS_COMMIT |
| receipt_parent_tested_head_full_sha | b4b210bd302f80a33c69c20d5e796c7f86dc6383 |
| reviewed_to_tested_changed | H1-INDEPENDENT-VERIFIER.py + 4 stub files (5 files total) |
| OS | Windows |
| Python | 3.13.14 |

## Normal
5 files, 0 findings, mhash=7b234af59c8a57e5604ff1178b17ce2e63033bd4b0bb57755b79a498d0e7507a
QCLAW: 15 manifest exact, 37/0/0, combined=dc815fc10d3d6eb516

## Negtests
NT1 injected_path: PASS, exit=1
NT2 missing_artifact: PASS, exit=1
NT3 forced_fail: PASS, exit=7
