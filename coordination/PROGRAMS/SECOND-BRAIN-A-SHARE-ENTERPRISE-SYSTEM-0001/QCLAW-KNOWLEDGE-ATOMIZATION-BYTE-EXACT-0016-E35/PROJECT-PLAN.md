# E35 Project Plan — Byte-Exact Lossless Knowledge Atomization

**Route Epoch**: 35 | **Issue**: #141 | **Base**: `085e7aee`

## Source Policy
- **E34 (PR #137)**: FROZEN, FAILURE_REFERENCE_AND_DESIGN_INPUT_ONLY, NO whole-file copy
- **E29 (PR #122)**: DESIGN_REFERENCE_ONLY, NO decoded byte copy

## Architecture

### S0: Byte Index (`byte_index.py`)
- Byte→codepoint→line triple mapping
- `[start_byte, end_byte)` slices back to exact source bytes
- Every span verifiable: `source_bytes[span.start:span.end].decode("utf-8") == text`

### S1: Lossless Adapters (`adapter.py`)
- **Markdown**: Header, paragraph, list-item, code-block, table all captured; whitespace between units tagged as `GAP`
- **TXT**: Paragraphs + inter-paragraph gaps
- **JSON**: Key-value field extraction + tree gaps
- **JSONL**: Line-by-line with inter-line gaps
- **Conversation**: Turn-by-turn with meta gaps
- **Contract**: 100% non-overlapping byte coverage

### S2: Span-Based Redaction (`redact.py`)
- Plan redaction spans on original bytes
- Resolve overlapping spans (longest-first wins)
- Emit redacted view + preserve original lineage
- No secret-derived hashes/fingerprints

### S3: Atoms + Relations (`atoms.py`, `relations.py`)
- 21 content types, conservative classification
- 6 relation types only: SUPPORTS, DEPENDS_ON, REFINES, CONTRADICTS, RAISES_UNKNOWN, VERIFIED_BY
- Every relation has evidence byte-span
- No adjacency-default semantic relations

### S4: Packet + Hash (`packet.py`)
- SHA-256 of complete semantic content, relations, evidence, UNKNOWNs, conflicts, safe lineage
- Deterministic across Python versions and hash seeds

### S5: Rejection Validators
- Absolute/private paths, placeholder SHAs, self-hashes, Base64 source, unexplained bytes
- Real assertions (not `pass`)

### S6: CI + Receipt
- `.github/workflows/qclaw-e35-knowledge-atomization.yml` (3.11 + 3.13)
- Plan commit → tested commit → receipt-only commit
- Exact-head CI anchors on both heads

## Commit Plan
1. `plan` — this document + skeleton
2. `tested` — all source + tests passing
3. `receipt-only` — evidence files only
