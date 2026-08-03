# E35 Byte-Exact Lossless Knowledge Atomization — ARCHITECTURE.md
# v1.0.0-e35 — 2026-08-03

## S0: ByteIndex (`byte_index.py`)
Recoverable bidirectional mapping: byte→codepoint→line→byte.
Every span slices back to exact source bytes.
`source[span.start:span.end].decode("utf-8") == span.text`

## S1: LosslessAdapter (`adapter.py`)
Five format adapters, each producing non-overlapping spans covering 100% bytes.
Markdown→TXT→JSON→JSONL→Conversation.
Gaps explicitly tagged as STRUCTURE_GAP.

## S2: SpanRedactor (`redact.py`)
14 secret patterns detected on original bytes. Span-based replacement.
Overlap resolution: longest-match-first. Preserves original lineage in redacted output.

## S3: AtomExtractor (`atoms.py`)
21 content types. Conservative: default CLAIM, never FACT.
Atoms reference original byte spans.

## S4: RelationExtractor (`relations.py`)
6 types only: SUPPORTS/DEPENDS_ON/REFINES/CONTRADICTS/RAISES_UNKNOWN/VERIFIED_BY
Every relation has evidence byte-spans. No adjacency-default relations.

## S5: PacketBuilder (`packet.py`)
SHA-256 of: atoms[], relations[], unknowns[], conflicts[], lineage, schema_version.
Deterministic across Python 3.11+ / 3.13+, PYTHONHASHSEED-invariant.

## S6: Rejection Validators
Real assertions: absolute path, placeholder SHA, self-hash, Base64 wrapping, unexplained bytes.
Each rejection is an explicit test failure (not a pass-through).

## Commit Topology
plan (this + skeleton) → tested → receipt-only (exact-head CI on both)
