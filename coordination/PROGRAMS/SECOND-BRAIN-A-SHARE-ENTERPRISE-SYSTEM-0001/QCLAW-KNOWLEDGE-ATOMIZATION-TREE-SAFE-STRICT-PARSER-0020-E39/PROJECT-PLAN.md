# E39 Project Plan — Tree-Safe Strict Byte Parser & Integrated Ledger

## Route
- task_id: QCLAW-KNOWLEDGE-ATOMIZATION-TREE-SAFE-STRICT-PARSER-INTEGRATED-LEDGER-SEMANTICS-VALIDATORS-AND-EXACT-ARTIFACT-CI-CLOSURE-0020-E39
- branch: qclaw/knowledge-atomization-tree-safe-strict-parser-ledger-artifact-ci-0020-e39
- base: main 3f57c0ad2fb6e664197b2e81c80e5db14961f16a (457 items)
- source: E38 frozen at 4ecc53b2 (PR #155)
- completion_signal: QCLAW_E39_TREE_SAFE_STRICT_PARSER_LEDGER_ARTIFACT_CI_READY_FOR_GPT_REVIEW

## Tree Scope Gate (PASS)
- Base tree: 457 items from main 3f57c0ad
- Plan commit: all 457 items preserved + 1 PROJECT-PLAN.md added = 458
- Zero modified/deleted/renamed/copied paths
- Blob-level verification: 410 source blobs preserved, 0 modified, 0 deleted, 1 new blob

## Commit Topology
1. PLAN-ONLY — one file added, full base tree preserved
2-N. Implementation commits (after tree_scope_gate)
N+1. tested_head (E39 CI success required)
N+2. receipt-only (final head, E39 CI success required)

## Phase Plan
### S0: UTF-8 Guard + 0xED/timeout (MUST first)
- Terminating strict UTF-8 validator: manual byte-scan first with specific messages, Python strict decode as cross-validation
- 0xED surrogate halves rejected; overlong/truncated/>U+10FFFF/bad-cont all rejected
- Progress-timeout positive test on every scan loop

### S1: Boundary Table + Owner Ledger
- Byte-codepoint-line index; BOM/CRLF/LF/emoji/ZWJ/combining; EOF-exclusive boundaries
- ByteLedger: ATOM_CANDIDATE/STRUCTURE/UNKNOWN_ERROR, exact-once, immutable after finalize

### S2: Strict Parsers (6 formats)
- Markdown/TXT byte-level spans
- JSON: stateful tokenizer preserving duplicates/escapes/punctuation/order/whitespace
- JSONL: per-line, real line endings, UNKNOWN_ERROR for bad lines
- Conversation: verified field identity (role/timestamp/metadata/boundary/body)

### S3: Redaction
- Source-order resolution; output cursor positioning; no reverse find(marker)
- Private key full header/body/footer; no secret hash/fingerprint/reversible

### S4: Atoms + 7 Semantic Fields
- condition, exception, negation, temporal_scope, assumption, evidence_status, applicability
- Default UNKNOWN; no vocabulary FACT upgrade

### S5: Relations + Packet
- 6 types (SUPPORTS/DEPENDS_ON/REFINES/CONTRADICTS/RAISES_UNKNOWN/VERIFIED_BY)
- Verifiable link evidence only
- Full packet hash: ledger/gaps/redaction/semantic/relations/unknowns/conflicts/lineage

### S6: Validators + Mutations + CI
- Product validators: path/commit/blob/placeholder/Base64/coverage/timeout/secret/redact/semantic/relation/subprocess/receipt/tree-scope
- 18 mutation families including tree deletion mutation
- CI: 3.11+3.13 × 3 seeds, artifact compare, exact-head assertion

## E38 Source Policy
FAILURE_REFERENCE_ONLY. Terminating UTF-8 S0 direction partially credited.
No whole-file copy allowed. No CI/receipt credit inherited.
