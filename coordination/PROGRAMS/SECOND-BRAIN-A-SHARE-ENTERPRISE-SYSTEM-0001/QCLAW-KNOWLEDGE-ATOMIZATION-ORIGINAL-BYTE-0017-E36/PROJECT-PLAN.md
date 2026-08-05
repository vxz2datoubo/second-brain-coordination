# E36 Project Plan — Original-Byte Parser & Executable Validators

**Route Epoch**: 36 | **Issue**: #145 | **Base**: `0f02c72f`

## Source Policy
- **E35 (PR #143)**: REVIEWED_AND_FROZEN, commit_topology_credit + module_scaffold_credit only. NO whole-file copy.
- **E29 (PR #122)**: DESIGN_REFERENCE_ONLY

## Architecture

### S0: Original-Byte Boundary Table (`boundary_table.py`)
- Accept arbitrary bytes; reject invalid strict UTF-8 BEFORE parsing
- Build chunk table at UTF-8 grapheme-cluster boundaries
- Handle BOM, CRLF/LF, emoji zwj sequences, combining characters
- Immutable source reference

### S1: Exact-Once Coverage Validator (`coverage.py`)
- Every byte owned exactly once
- Detect: overlap, omission, out-of-range, straddling, inverted intervals
- No coverage clamp — report uncovered bytes
- Freeze mapping on finalize

### S2: Chunk-Granular Adapters (`adapter.py`)
- Position-aware MD/TXT/JSON/JSONL/Conv adapters on chunk ranges
- No character-index fallback
- Full white-space and structure tag retention

### S3: Original-Byte Redaction (`redact.py`)
- Secret pattern matching on original bytes
- Deterministic overlap resolution
- No secret text/hash/fingerprint in output

### S4: Atoms + Relations (`atoms.py`, `relations.py`)
- Atoms: 21 types, strict byte-span attribution
- Relations: explicit linking evidence or rule identity only; no proximity/type-pair

### S5: Packet Hash (`packet.py`)
- Hash: coverage map + redaction mapping + semantic fields + relations + evidence + unknowns + conflicts + lineage + config

### S6: Product Validators + CI (`validators.py`)
- Real rejection tests covering all 11 mandatory negative families
- Dual Python 3.11/3.13 CI with three-seed artifact comparison
- Tested + receipt-only commits, exact-head CI on both

## Commit Plan
1. `plan` — this document
2. `tested` — all source + tests passing
3. `receipt-only` — evidence files only
