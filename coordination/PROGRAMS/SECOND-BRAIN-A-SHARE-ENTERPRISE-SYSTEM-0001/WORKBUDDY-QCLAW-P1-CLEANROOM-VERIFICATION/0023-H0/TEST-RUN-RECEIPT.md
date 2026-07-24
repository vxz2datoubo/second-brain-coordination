# WorkBuddy Cleanroom Test Run Receipt (R2)

| Field | Value |
|-------|-------|
| Version | R2 |
| Tested head | ce1704c (R1) |
| Workspace | <CLEANROOM_WORKSPACE> |
| OS | Windows 11 |
| Python | 3.13.14 |

## QCLAW Validator (unchanged, PR84 head 63c34408)
| Field | Value |
|-------|-------|
| SHA-256 | 45cd0e3ee6f9d54c5ad19799c165b1238b64dfa391d385e366c728863afc6b2a |
| Status | BYTE-IDENTICAL |
| Exit code | 0 |
| Result | 37 PASS / 0 FAIL / 0 SKIP |
| Output SHA-256 | 774c009fe902ba23181cac669bbf7260b492920f9644adc57261f87a79b12e8c |

## R2 Path Scanner (_r2_scanner.py)
| Field | Value |
|-------|-------|
| Files scanned | 17 |
| Findings | 0 |
| Result | CLEAN |
| Output SHA-256 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 |
| Method | Regex patterns; excludes scanner scripts; allows <CLEANROOM_WORKSPACE> |
