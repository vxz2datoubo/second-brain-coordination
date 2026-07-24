# WorkBuddy Cleanroom Test Run Receipt (R3)

| Field | Value |
|-------|-------|
| Version | R3 |
| Tested head | d6d2df6459f33688258820a30305eb349e157d17 |
| Command | python INDEPENDENT-VERIFICATION-SCRIPT.py |
| OS | Windows 11 |
| Python | 3.13.14 |

## R3 Path Scan (self-auditing, 19 files)
| Field | Value |
|-------|-------|
| Findings | 0 (CLEAN) |
| Manifest hash | 1915572b11efce56b44a24cb0071b55e6fa0670b4a5abdb9c7140cf214533948 |
| Method | Regex patterns from safe fragments, scans ALL files including scanner source |

## QCLAW Reproduction (63c344084d9af86cb26c1cc65a30d409fefa872f)
| Field | Value |
|-------|-------|
| Files | 15 (exact manifest, real extensions) |
| Validator | BYTE-IDENTICAL |
| Result | 37 PASS / 0 FAIL / 0 SKIP |
| Combined hash | dc815fc10d3d6eb5164587b4bcc9f3247bb8d30b5e9533f873f5ba14982488f5 |
| Output hash | f372b9ad44021c821d581ef3f16d9ab5e9dada96b53be4df5c82f2193b75e65c |

## R3 Changes from R2
- _r2_scanner.py DELETED (contained absolute paths)
- Scanner rewritten: Path(__file__) + git rev-parse, scans itself, safe fragment patterns
- 40-char full heads throughout
- True tested_head → receipt_head chain
