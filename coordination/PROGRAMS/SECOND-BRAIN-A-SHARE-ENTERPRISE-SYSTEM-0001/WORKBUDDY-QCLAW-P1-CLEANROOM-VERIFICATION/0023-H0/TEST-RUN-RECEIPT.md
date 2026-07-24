# WorkBuddy Cleanroom Test Run Receipt (R4)

| Field | Value |
|-------|-------|
| Version | R4 |
| Tested head | 81de4da53e14ddd35a7d3afca0a3f4a4a9747080 |
| Receipt head | TBD (to be filled after receipt commit) |
| Command | python INDEPENDENT-VERIFICATION-SCRIPT.py |
| OS | Windows |
| Python | 3.13.14 |

## R4 Path Scan (fail-closed, 18 files including self)
| Field | Value |
|-------|-------|
| Findings | 0 (CLEAN) |
| Exit code | 0 |
| Negative tests | 4/4 PASS |
| Manifest hash | 5d4d63aca3bdd376a68609492167bb8c553f6ed47b69180af477a1e259d27fd3 |

## QCLAW Reproduction
| Field | Value |
|-------|-------|
| Head | 63c344084d9af86cb26c1cc65a30d409fefa872f |
| Files | 15 (ls-tree verified) |
| Validator | BYTE-IDENTICAL, 37/0/0 |
| Combined hash | dc815fc10d3d6eb5164587b4bcc9f3247bb8d30b5e9533f873f5ba14982488f5 |

## R4 Changes
- _r2_scanner.py: GIT-DELETED (not tombstone)
- Fail-closed: any finding/missing file/validator fail → exit 1
- Google token + credential assignment patterns added
- OS auto-detected (not hardcoded "Windows")
- git ls-tree manifest verification
