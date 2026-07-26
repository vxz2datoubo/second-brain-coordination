# DELETION-RATIONALE.md ? PR #64 Stage C Cross-PR File Removal

**task_id:** QCLAW-UNIFIED-KNOWLEDGE-SUPPLY-CHAIN-ONTOLOGY-DETERMINISM-AND-LTM-EVIDENCE-0013-E10
**route_epoch:** 10
**stage:** Stage C: PR #64 Executable Architecture Truth
**authority:** CANDIDATE_ONLY ? does NOT claim canonical runtime

## Removed Files (moved to Stage E scope)

The following 4 files were supply-chain artifacts that span multiple PRs.
Per the unified task plan, cross-PR global index/manifest/handoff files
belong to **Stage E** (the final cross-PR consolidation stage).
They have been removed from the 0008/ architecture directory to avoid
duplication that Stage E will resolve.

### 1. KNOWLEDGE-SUPPLY-CHAIN-INDEX.md
- **Reason:** Cross-PR supply chain index that maps PR #57 ? #96 ? #100 ? #64 ? #65
- **Stage E ownership:** This is the global "table of contents" for all supply chain PRs
- **Local pointer:** ARCHITECTURE.md already contains source lock + authority matrix references
- **SHA of removed file:** ce9ee3c3170f6073f77782b40730a9a729eca5f3

### 2. AUTHORITY-AND-NON-DUPLICATION-MATRIX.yaml
- **Reason:** Duplicates content in AUTHORITY-MATRIX.yaml (which is kept) plus extends to cross-PR scope
- **Stage E ownership:** Global non-duplication enforcement across all PRs
- **Local pointer:** AUTHORITY-MATRIX.yaml remains in 0008/ with PR-local authority matrix
- **SHA of removed file:** 9f38876c1f087cfc085b83b6d0f69cb39bc18236

### 3. COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml
- **Reason:** Cross-PR count manifest that asserts all PRs must match the same counts
- **Stage E ownership:** Unified source-of-truth manifest for all supply chain PRs
- **Local pointer:** verify_counts.py now directly validates against Q0 source files; ATOM-TYPE-TAXONOMY.yaml and RELATION-TAXONOMY.yaml embed the counts locally
- **SHA of removed file:** 39f1cd80dbb7c741559ef48d4f5d5cf792ff6c9a

### 4. CODEX-D2-CANDIDATE-HANDOFF.yaml
- **Reason:** Cross-PR handoff that exposes D2 family mapping from PR #100
- **Stage E ownership:** Consolidated handoff between PR #96/#100 ? PR #58 (gateway)
- **Local pointer:** ARCHITECTURE.md already references PR #100 as candidate D2 adapter
- **SHA of removed file:** d98249995d909a29f50a4c588b0e328951842521

## What Remains in 0008/ (PR #64 Local Architecture)

| File | Purpose |
|------|---------|
| ARCHITECTURE.md | Architecture description with source lock |
| ATOM-TYPE-TAXONOMY.yaml | Atom type taxonomy from Q0 ground truth |
| RELATION-TAXONOMY.yaml | Relation type taxonomy from Q0 ground truth |
| AUTHORITY-MATRIX.yaml | PR-local authority + non-duplication matrix |
| verify_counts.py | Executable verification against Q0 sources |
| DELETION-RATIONALE.md | This file |
| AI_HANDOFF.yaml | Stage C handoff metadata |
| TEST-RUN-RECEIPT.yaml | Test run receipt |
| DETERMINISM-RECEIPT.yaml | Two-run determinism receipt |

**CANDIDATE_ONLY | NO_TRADE | PUBLIC_SAFE | NO_AUTHORITY_PROMOTION**
