# E35 Test Run Receipt

**Tested Commit**: `d674a04b384c24888529647a0596a8c4145a9905`
**Branch**: `qclaw/knowledge-atomization-byte-exact-lossless-0016-e35`
**Plan**: #143
**Timestamp**: 2026-08-03T12:45:00+08:00

## Python 3.11.10
- Result: **102/102 PASS, 0 FAIL**
- PYTHONHASHSEED: 0

## Python 3.13.3
- Result: **102/102 PASS, 0 FAIL**
- PYTHONHASHSEED: 0

## Cross-Version
- Byte-identical: YES
- 3-seed PYTHONHASHSEED (0, 1, 42): CONSISTENT

## Source Policy
- E34 (PR #137): FROZEN reference only
- E29 (PR #122): DESIGN_REFERENCE_ONLY
- Zero file copy from either source

## Architecture
- S0: ByteIndex (byte↔codepoint↔line)
- S1: LosslessAdapters (MD/TXT/JSON/JSONL/Conv, 100% coverage)
- S2: SpanRedactor (14 patterns, overlap-safe, lineage-preserving)
- S3: AtomExtractor (21 types, default CLAIM)
- S4: RelationExtractor (6 types, evidence-span, no adjacency)
- S5: PacketBuilder (SHA-256 deterministic)
- S6: Rejection validators (real assertions)
