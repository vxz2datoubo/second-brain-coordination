# WorkBuddy Cleanroom Test Run Receipt (H1)

| Field | Value |
|-------|-------|
| task_id | WORKBUDDY-PH11-H1-PRODUCTION-PATH-NEGTESTS-AND-TRUTHFUL-RECEIPT-CLOSURE |
| receipt_head_ref | THIS_COMMIT |
| receipt_parent_tested_head_full_sha | c2f66116c1b12f4b6cc7952c15c85e5caae974bc |
| reviewed_to_tested_changed | INDEPENDENT-VERIFICATION-SCRIPT.py (1 file) |
| OS | Windows |
| Python | 3.13.14 |

## Normal Scan
delivery=1, findings=0, mhash=6ce45c9a, fhash=4f53cda1

## QCLAW
git ls-tree 15 exact match, validator 37/0/0, combined=dc815fc10d3d6eb516

## Production-Path Negtests (CLI modes)
| Test | Mode | Expected | Actual | Result |
|------|------|----------|--------|--------|
| NT1 | nt1 | non-zero | findings=1 | PASS |
| NT2 | nt2 | non-zero | exit=1 | PASS |
| NT3 | nt3 | exit=7 | exit=7 | PASS |
