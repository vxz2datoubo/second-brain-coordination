# DELETION-RATIONALE.md
## Stage D — Cross-PR Duplicate Remediation for PR #65

**task_id:** QCLAW-UNIFIED-KNOWLEDGE-SUPPLY-CHAIN-ONTOLOGY-DETERMINISM-AND-LTM-EVIDENCE-0013-E10
**route_epoch:** 10
**stage:** D
**target_pr:** 65

## Removed Files

The following 4 files were removed from `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-LONG-TERM-MEMORY/0009/`
because they are **cross-PR duplicates** that belong to the **supply-chain ontology layer**, whose canonical home will be
established in **Stage E** (`0010-Q0` or a dedicated supply-chain coordination directory).

| File Removed | Why Removed | Future Owner |
|---|---|---|
| `AUTHORITY-AND-NON-DUPLICATION-MATRIX.yaml` | Cross-PR duplicate. Authority matrices span PR #57, PR #58, PR #65, and PR #100. PR #65 should reference, not duplicate | Stage E (0010-Q0 supply-chain layer) |
| `CODEX-D2-CANDIDATE-HANDOFF.yaml` | Cross-PR duplicate. Candidate handoff protocol is a coordination artifact, not an LTM-specific artifact | Stage E (0010-Q0 supply-chain layer) |
| `COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml` | Cross-PR duplicate. Source-of-truth counts are supply-chain integrity metadata, not LTM-specific | Stage E (0010-Q0 supply-chain layer) |
| `KNOWLEDGE-SUPPLY-CHAIN-INDEX.md` | Cross-PR duplicate. Supply chain indexing is a coordination concern across all PRs | Stage E (0010-Q0 supply-chain layer) |

## Why Not Keep Copies?

1. **Single Source of Truth**: Each supply-chain artifact must have exactly one canonical location. Duplicates create COUNT_DRIFT and divergence.
2. **PR #65 Scope**: PR #65 is the Long-Term Memory plan — it describes retrieval, memory lifecycle, and adversarial cases. It should reference shared artifacts, not own them.
3. **Stage E Responsibility**: Stage E will establish the canonical supply-chain directory and consolidate all cross-PR artifacts there.

## What Stays in 0009/

- **LTM-TRUTH.md** — Truthful plan status document (PR #65 specific)
- **NON-DUPLICATION-MAP.yaml** — Truthful non-duplication mapping (PR #65 specific)
- **PLAN-ADVERSARIAL-CASES.yaml** — 48+ unique adversarial cases (PR #65 specific, NEW)
- **validate_plan.py** — Executable plan validator (PR #65 specific, NEW)
- **AI_HANDOFF.yaml** — Handoff receipt (NEW)
- **TEST-RUN-RECEIPT.yaml** — Test run receipt (NEW)
- **DETERMINISM-RECEIPT.yaml** — Determinism receipt (NEW)

## How PR #65 References These Artifacts

The preserved `NON-DUPLICATION-MAP.yaml` and the adversarial cases in `PLAN-ADVERSARIAL-CASES.yaml`
reference supply-chain artifacts by path/name, not by duplicate copy. Stage E will provide the
canonical paths that PR #65 can reference.

## Verification

- `validate_plan.py` includes checks for cross-PR boundary violations
- `validate_plan.py` detects COUNT_DRIFT across any remaining references
- No PR #65 file claims ownership of shared supply-chain artifacts

**NO_TRADE | PUBLIC_SAFE | CANDIDATE_ONLY**
