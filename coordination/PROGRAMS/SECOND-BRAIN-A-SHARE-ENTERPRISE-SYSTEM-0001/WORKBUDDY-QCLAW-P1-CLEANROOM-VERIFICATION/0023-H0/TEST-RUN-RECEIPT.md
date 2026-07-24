# WorkBuddy Cleanroom Test Run Receipt (R5)

| Field | Value |
|-------|-------|
| Version | R5 |
| receipt_head_ref | THIS_COMMIT |
| receipt_parent_tested_head_full_sha | 05c96d97d4008f2599517cf3f3daf976333b4ee3 |
| reviewed_to_tested_changed | INDEPENDENT-VERIFICATION-SCRIPT.py (modify) + 3 deletions |
| OS | Windows |
| Python | 3.13.14 |

## Delivery Surface Scan (full diff, not package-only)
| Field | Value |
|-------|-------|
| Delivery files | 4 |
| Findings | 0 (CLEAN) |
| Manifest hash | 785f0347e58037f149b8c3833f7e1f258ac1de9e2052a3b14c5d4665f71fbcab |

## Functional Negtests
| Test | Result |
|------|--------|
| Injected drive path | PASS (detected) |
| Missing QCLAW files | PASS (validator exit 1) |
| Fail-closed findings→exit | PASS |

## QCLAW Reproduction
37 PASS / 0 FAIL / 0 SKIP | Combined: dc815fc10d3d6eb516
