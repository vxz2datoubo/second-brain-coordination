# QCLAW E37 — Byte Tokenizer, Mutation Gates, Redaction Mapping, Semantic Packet & Exact CI

**Route**: `QCLAW-KNOWLEDGE-ATOMIZATION-BYTE-TOKENIZER-MUTATION-TESTS-REDACTION-MAPPING-SEMANTIC-PACKET-AND-EXACT-CI-CLOSURE-0018-E37`
**Issue**: [#148](https://github.com/vxz2datoubo/second-brain-coordination/issues/148)
**Base**: main `{main_head}`
**E36**: Issue #145 / PR #147 FROZEN (DESIGN_REFERENCE_ONLY, no whole-file copy)

## Architecture

```
strict UTF-8 bytes → OriginalByteIndex (byte↔codepoint↔line, immutable)
  ↓
Ledger (exact-once: ATOM_CANDIDATE | STRUCTURE | UNKNOWN_ERROR per byte)
  ↓
Adapters: md / txt / json / jsonl / conversation (codepoint→byte mapping ONLY)
  ↓
Redact: original-byte pattern scan → priority+longest-match resolution → irreversible mapping
  ↓
Atoms: source spans + semantic fields + UNKNOWN preservation
  ↓
Relations: SUPPORTS/DEPENDS_ON/REFINES/CONTRADICTS/RAISES_UNKNOWN/VERIFIED_BY (explicit evidence only)
  ↓
Packet: canonical hash over coverage + redaction mapping + semantics + relations + unknowns + conflicts + lineage
  ↓
Validators: product validators + mutation tests (unittest) + pre_receipt_validator
  ↓
CI: 3.11 + 3.13, 3-seed, exact-head verification, artifact byte comparison
```

## Hard Invariants

1. Production entry accepts bytes only; rejects invalid strict UTF-8 before parsing.
2. All character positions converted through verified codepoint→byte mapping before span creation.
3. Every source byte has exactly one ledger owner; zero-length, overlap, omission, duplicate, out-of-range, inverted, illegal-boundary → fail closed.
4. JSON uses original-position tokenizer/parser (NOT json.loads + find/json.dumps).
5. Adapters preserve BOM, CRLF/LF, whitespace, markers, separators; do NOT convert str index to byte span.
6. Redaction: explicit category priority, longest-match, stable tie-break; NO secret plaintext/hash/fingerprint persisted.
7. Relations only from explicit link syntax, rule identity, human confirmation, or verified parser structure; NO proximity/type-pair defaults.
8. Packet hash covers ALL semantic fields; packet_id is NOT self-referencing.
9. Tests use unittest/pytest (NOT custom chk() wrapper or PASS counters).
10. Pre-receipt validator rejects incomplete modules, Planned/TODO, placeholders, unsupported remote evidence, invalid topology.

## Implementation Phases

| Phase | Deliverable | Test Count (approx) |
|-------|-------------|---------------------|
| S0 | OriginalByteIndex (strict UTF-8, immutable boundary table) | 50+ |
| S1 | Ledger (exact-once ownership, all rejection modes) | 45+ |
| S2 | Adapters (md/txt/json/jsonl/conversation, all byte-positioned) | 80+ |
| S3 | Redact (pattern scan + priority resolution + irreversible mapping) | 40+ |
| S4 | Atoms (source spans + 7 semantic fields + UNKNOWN) | 30+ |
| S5 | Relations (6 types, explicit evidence, no adjacency) | 30+ |
| S6 | Packet (canonical hash, complete coverage, validators) | 50+ |
| S7 | Pre-receipt validator + CI workflow (3.11/3.13, 3 seeds) | 30+ |
| **Total** | | **355+** |

## Mutation Families (13 mandated)

1. CJK/emoji/combining prefix → marker/role/JSON key misalignment
2. Zero-length/missing/overlapping/duplicated/out-of-range/inverted/illegal-boundary owners
3. Duplicate JSON key collapse, escaped Unicode key mis-sizing, punctuation/whitespace loss
4. JSONL synthetic final newline, malformed-line silence
5. Conversation role/time/metadata/boundary/body offset corruption
6. Overlapping secrets, safe-example bypass, private key, secret-derived fingerprint
7. Redaction original→view mapping displacement
8. Absolute/private path, abbreviated/placeholder SHA, Base64-wrapped source
9. Packet field omission and self-reference
10. Relation endpoint/proximity/type-pair false evidence
11. Identical failed subprocess stdout, malformed output
12. Cross-version artifact byte tampering
13. Premature receipt, placeholder receipt, commit after receipt

## Commit Protocol

1. **Plan-only commit** (THIS COMMIT): PROJECT-PLAN.md only; no source, test, output, or receipt.
2. Implementation commits (one or more).
3. **Tested head** (all modules + tests + workflow present, E37 CI success verified).
4. **Receipt-only commit** (exactly one, non-empty, evidence-only, final branch head).

## Source Boundary

- E36 (PR #147): DESIGN_REFERENCE_ONLY, no whole-file copy
- E35 (PR #143): REFERENCE_ONLY, no copy
- E29 (PR #122): BASE64_DECODE_AND_COPY_FORBIDDEN
- No local config/model/provider/reasoning access or mutation

## Completion Signal

`QCLAW_E37_BYTE_TOKENIZER_MUTATION_REDACTION_MAPPING_SEMANTIC_PACKET_EXACT_CI_READY_FOR_GPT_REVIEW`
