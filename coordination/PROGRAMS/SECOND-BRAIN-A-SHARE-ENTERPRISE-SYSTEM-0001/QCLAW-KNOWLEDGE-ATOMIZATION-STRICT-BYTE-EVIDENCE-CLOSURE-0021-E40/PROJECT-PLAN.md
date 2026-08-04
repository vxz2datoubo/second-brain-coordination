# E40 Project Plan — Strict Byte Truth & Exact Ownership Closure

## Objective
Byte-level exact ownership, immutable finalized structures, real 0xED mutation timeout proof,
EOF-exclusive line model, JSON/JSONL/conversation byte-truth, irreversible redaction lineage,
semantic evidence relations, and provider-observable artifact CI.

## Epoch
40

## Parent Epoch
E39 (frozen at `ed5f307f`)

## Source Selection Policy
E39 = FAILURE_REFERENCE_ONLY. No whole-file copy from E39. Selected path/blob import only
with source_selection_ledger documenting each selection.

## Phase Plan

### S0 — Immutable Index & Exact Ownership
- Immutable frozen byte index (frozen after construction)
- EOF-exclusive legal boundary mapping (total_bytes mapped to codepoint_count)
- Real 0xED production process mutation with child cleanup proof
- Canonical line model (LF/CRLF/empty/final/trailing-empty-line unified)
- Real mutation tests BEFORE implementation (red-to-green)

### S1 — One-Owner Ledger & Bounded Adapters
- Exact one-owner per byte (ATOM_CANDIDATE/STRUCTURE/UNKNOWN_ERROR)
- Bounded adapters for every original byte (no silent omission)
- JSON: owns whitespace, punctuation, escapes, grammar failures, trailing bytes
- JSONL: parses bounded line slices, never consumes later lines
- Conversation: owns fields, boundaries, colons, spaces, blank separators, terminators

### S2 — Redaction Lineage & Secret Safety
- Production redaction: no implicit safe-example bypass
- No secret-derived material persisted (hash, fingerprint, reversible substitution)
- Source-order irreversible mapping with lineage

### S3 — Verified Semantics & Packet
- Atom seven-field semantics with source/default rules + validators + mutations
- Relations require executable evidence + valid endpoint atoms
- Canonical packet serializes FULL content (not counts-only)

### S4 — Product Validators & Active Mutations
- Validators: no assertTrue(True), import-only, existence-only, documentation-only, print-only
- Named isolated mutations with observed nonzero failure for critical controls

### S5 — Provider Artifact CI
- Workflow: `.github/workflows/qclaw-e40-strict-byte-evidence.yml`
- 6 real artifacts: 3.11 seed 0/1/777 + 3.13 seed 0/1/777
- Independent byte-compare job, errors on missing files

### S6 — Placeholder-Free Receipt
- NO receipt before provider-observable tested-head CI success
- External post-commit identity only
- Exactly one nonempty evidence-only receipt as final head

## Commit Protocol
1. Plan-only commit (this file) — STRICT_ONE_FILE
2. S0 implementation (with mutation tests first, red-to-green)
3. S1-S6 sequential, tree scope gate at each commit
4. tested_head only after provider CI success
5. Exactly one nonempty receipt-only final commit

## Constraints
- No whole-file copy from E39
- Source selection ledger for any E39 reference
- Tree scope gate: zero modified/deleted outside E40 paths at every commit
- No main direct write, merge, rebase, or force-push
