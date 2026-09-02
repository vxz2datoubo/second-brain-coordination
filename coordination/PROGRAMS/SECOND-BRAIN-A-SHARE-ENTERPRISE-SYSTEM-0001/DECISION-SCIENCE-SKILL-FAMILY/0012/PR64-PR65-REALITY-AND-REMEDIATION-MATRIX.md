# PR #64 and PR #65 Reality and Remediation Matrix

## PR #64: Knowledge Atomization P0

| Area | Verified reality | Required remediation | Gate |
|---|---|---|---|
| Identity | Draft PR head `60a420b2f47b9a96820d388289ea29fbca40aa43` | Replace old task IDs and placeholder SHA in every handoff | Machine search has zero stale identifiers/placeholders |
| Artifacts | 36 architecture, taxonomy, schema and feedback files | Keep status `P0_DOCUMENT_AND_CONTRACT_CANDIDATE` | No runtime or P1 claim |
| Taxonomy | Relation schema exposes 30 types; taxonomy lists 27 | Unify the sets or declare and test exactly three inverse aliases | Automated equality/alias test passes |
| Tests | GitHub generic CI passed, but package-specific validation scripts and receipts are absent | Add parse, schema, ID determinism, taxonomy and sample contract tests with actual commands/exit codes | No skipped mandatory gate |
| Runtime | Compatibility with PR #57/58 remains unknown | Map every atom/relation/packet field to canonical Python contracts | No second store, retrieval or gateway |
| Sequence | Current priority is independent PR #58 adversarial evidence | Keep PR #64 parked until that P0 evidence task is accepted | GPT explicitly reactivates remediation |

**Disposition:** `REFERENCE_ONLY / CONTRACTED_CANDIDATE / DO_NOT_MERGE_YET`.

## PR #65: Long-Term Memory M0

| Area | Verified reality | Required remediation | Gate |
|---|---|---|---|
| Runtime audit | Audited nonexistent `lib/runtime/*.rb` rather than Python `integrated_offline_memory` | Re-run M0 against PR #57 merge and PR #58 exact head | Every claim cites existing file/class/schema |
| Issue state | Describes implemented PR #58 C1-C6 as pending | Import current #38 paused/90% state and exact remaining external gate | Status agrees with router and PR comments |
| Non-duplication | Claims 44 `NO_DUPLICATION` results without current code inspection | Reclassify every row as `REUSE/EXTEND/WRAP/REFERENCE/REJECT/UNKNOWN` | Reviewer can trace each row to code |
| Proposed runtime | Query parser, AnswerEvidenceBundle, retrieval/index and memory APIs overlap PR #57/58 | Delete duplicate runtime proposal; retain only genuinely orthogonal memory-policy research | Zero second canonical runtime |
| Evidence | Lacks feedback, handoff, UNKNOWN and executable test receipt | Add complete feedback v2 and actual command evidence | No self-certified PASS |
| Sequence | Started before PR #58 acceptance gate | Remain frozen at M0 | GPT explicitly authorizes re-audit |

**Disposition:** `REJECTED_CURRENT_AUDIT / FREEZE_M1 / REAUDIT_OR_CLOSE`.

## Recommended Repository Action

1. Do not merge either PR as currently written.
2. After PR #58's independent gate, remediate PR #64 metadata and contracts first.
3. Re-audit PR #65 only if a concrete capability remains outside PR #57/#58 after that remediation; otherwise close it as superseded-by-canonical evidence while preserving its discussion history.

