# E39 TEST-RUN-RECEIPT

## Tested Head
- **tested_commit**: `71dc7588dc1e8439803472b7350f5027ffe7f028`
- **branch**: `qclaw/knowledge-atomization-tree-safe-strict-parser-ledger-artifact-ci-0020-e39`
- **PR**: #157

## Source Artifact Identity
- **combined_source_artifact_hash**: `fb3c3a7532d0166f031fe79579af81ef488fbfa7861f0d781d36207154f93603`
- **total_source_files**: 17
- **excludes**: `__pycache__`

## Test Summary (dual Python)
| Stage   | Tests | Python 3.11.10 | Python 3.13.3 |
|---------|-------|----------------|---------------|
| S0  utf8_guard     |  52 | PASS | PASS |
| S1  ledger         |  38 | PASS | PASS |
| S2  adapter        |  39 | PASS | PASS |
| S3  redact         |  34 | PASS | PASS |
| S4  atoms/rel/pkt  |  29 | PASS | PASS |
| S5  pre_receipt    |  15 | PASS | PASS |
| **TOTAL**          |**207**|**ALL PASS**|**ALL PASS**|

## Commit Chain
1. `943c23ba` — plan-only (PROJECT-PLAN.md)
2. `c06239df` — S0 utf8_guard
3. `28f0fd0d` — S1 ledger
4. `405d0ffc` — S2 adapter
5. `81ed300e` — S3 redact
6. `437e3917` — S4+S5 atoms/relations/packet + SOURCE-MANIFEST + CI workflow
7. `71dc7588` — S6 pre_receipt validators (TESTED_HEAD)
8. **`${THIS_COMMIT}`** — receipt-only (this file, AI_HANDOFF, D05-COMMAND-EVIDENCE)

## Tree Scope Gate
- Base blob count: 410
- Blobs at tested_head: 410 + 17 = 427 (no deletions, no modifications outside E39 allowed paths)
- Gate: PASS (each stage independently verified)

## CI Workflow
- **workflow**: `.github/workflows/qclaw-e39-tree-safe-parser.yml`
- **matrix**: Python 3.11 + 3.13, seeds 0/1/777, byte-compare job
- **event head**: `${{ github.event.pull_request.head.sha || github.sha }}`

## Protocol Compliance
- [x] Plan-only first commit preserving canonical tree
- [x] No whole-file copy from E34/E35/E36/E37/E38
- [x] All implementations original E39 files
- [x] 207 tests dual Python PASS (unittest, no custom wrappers)
- [x] Tree scope gate passed at every stage (zero modified/deleted outside E39 paths)
- [x] SOURCE-MANIFEST.yaml present and valid
- [x] CI workflow present
- [x] Pre-receipt validators 15/15 PASS
- [x] receipt-only commit (different tree from tested_head)
- [x] receipt is final head

## Environment
- **OS**: Windows 10.0.22631
- **Python 3.11.10**: `F:\Program Files (x86)\QClaw\v0.2.35.624\resources\python\python.exe`
- **Python 3.13.3**: `C:\Program Files\Python313\python.exe`
- **repo**: `vxz2datoubo/second-brain-coordination`
