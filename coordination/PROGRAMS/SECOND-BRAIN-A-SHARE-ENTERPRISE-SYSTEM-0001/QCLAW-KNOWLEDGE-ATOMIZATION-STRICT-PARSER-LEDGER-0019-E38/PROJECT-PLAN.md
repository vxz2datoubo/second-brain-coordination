# E38 Project Plan — Strict Byte Parser & Integrated Ledger

## Route
- task_id: QCLAW-KNOWLEDGE-ATOMIZATION-STRICT-BYTE-PARSER-INTEGRATED-LEDGER-COMPLETE-SEMANTICS-PRODUCT-VALIDATORS-AND-EXACT-ARTIFACT-CI-CLOSURE-0019-E38
- branch: qclaw/knowledge-atomization-strict-parser-ledger-semantics-artifact-ci-0019-e38
- base: main ac17da81cd2ea019786e9f1d229eaede944756d9
- source: E37 frozen at 5942e86a2b9a023c3ffb85c772206390d1eb5772 (PR #149)
- completion_signal: QCLAW_E38_STRICT_PARSER_LEDGER_SEMANTICS_VALIDATORS_EXACT_ARTIFACT_CI_READY_FOR_GPT_REVIEW

## Commit Topology
1. PLAN-ONLY (this commit) — no source, no test, no receipt
2-N. Implementation commits (S0→S6)
N+1. tested_head (E38 CI success required)
N+2. receipt-only (final head, E38 CI success required)

## Phase Plan
### S0: UTF-8 Guard + 0xED/timeout (MUST first)
- Strict UTF-8 validator: reject 0xED surrogate, overlong, truncated, >U+10FFFF, bad cont
- Progress-timeout positive test: every scan loop terminates in bounded steps
- Negative test: 0xED infinite loop simulation → detected + terminated

### S1: Boundary Table + Owner Ledger
- Byte-codepoint-line index; BOM/CRLF/LF/emoji/ZWJ/combining
- ByteLedger: ATOM_CANDIDATE/STRUCTURE/UNKNOWN_ERROR exact-once
- Ledger frozen after finalize; gaps detected

### S2: Strict Parsers (6 formats)
- Markdown: header/content/code_block/table/list_item/blockquote
- TXT: paragraph-level spans
- JSON: stateful tokenizer (reject unclosed string, illegal escape, illegal number, bad brackets)
- JSONL: per-line tokenizer, preserve real line endings
- Conversation (structured+plain): verify field identity, output role/timestamp/metadata/boundary/body spans

### S3: Redaction
- Category priority + longest-match + stable tie-break overlap resolution
- Output cursor (not find(marker) reverse lookup)
- Private key full header/body/footer; safe-example exact fixture identity only
- No secret hash/fingerprint/reversible replacement

### S4: Atoms + Semantics
- 7 semantic fields per atom: condition/exception/negation/temporal_scope/assumption/evidence_status/applicability
- All UNKNOWN by default; no vocabulary FACT upgrade

### S5: Relations + Packet
- 6 types: SUPPORTS/DEPENDS_ON/REFINES/CONTRADICTS/RAISES_UNKNOWN/VERIFIED_BY
- Executable-verifiable link evidence only; human_confirmation alone rejected
- Packet: full ledger/gaps/redaction/semantic/confidence/lineage hash; no self-reference

### S6: Validators + Mutation + CI
- Product validators: path/commit/blob/placeholder/Base64/coverage/timeout/secret/redact/semantic/relation/subprocess/receipt
- Mutation tests: 16 families covering 0xED, char≠byte, JSON key loss, JSONL silent, conversation field swap, redact order, private key header-only, marker collision, secret hash injection, semantic field drop, fake relation evidence, failed subproc, artifact tamper, early receipt, post-receipt
- CI: 3.11+3.13, 3-seed, artifact compare job, exact-head assertion

## E37 Source Policy
E37 = FAILURE_REFERENCE_ONLY. Design direction only (bytes entry, legal boundaries, exact-once ledger, unittest framework, redaction concept). No whole-file copy, no commit carryover, no test/CI/receipt credit inheritance.
