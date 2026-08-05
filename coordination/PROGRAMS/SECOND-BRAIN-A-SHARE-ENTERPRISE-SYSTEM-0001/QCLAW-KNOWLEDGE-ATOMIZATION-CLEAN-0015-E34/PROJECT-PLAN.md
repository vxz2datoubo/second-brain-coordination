# QCLAW E34 — Source-Admission Manifest & Project Plan
**Route Epoch**: 34 | **Issue**: #135
**Generated**: 2026-08-03 03:05 GMT+8

## Phase 0: Source Admission Audit (COMPLETE)

| Source | File | Size | Parse Check | Disposition | Notes |
|--------|------|------|-------------|-------------|-------|
| E27 | `atomizer.py` | 22.7KB | PARSE_OK | **ADMIT** | 21 content types, UTF-8 ✅ |
| E27 | `redact.py` | 8.8KB | PARSE_OK | **ADMIT** | 14 secret patterns; safe example values only |
| E27 | `cli.py` | 3.4KB | PARSE_OK | **ADMIT** | Clean CLI entry |
| E27 | `knowledge_atom.schema.json` | 3.5KB | JSON_FIX_NEEDED | **ADMIT_AFTER_FIX** | `\.` → `.` in regex pattern (line 12) |
| E27 | `run_all_tests.py` | 16.5KB | PARSE_OK | **ADMIT** | Test template; safe example values only |
| E27 | `run_integrated_pipeline.py` | 4.7KB | PARSE_OK | **ADMIT** | 4-step pipeline |
| E27 | `.gitignore` | 121B | TEXT_OK | **ADMIT** | Standard ignores |
| E27 | `E27-PIPELINE-CONFIG.yaml` | 1.1KB | YAML_OK | **ADMIT** | Pipeline config reference |
| E28 | `parser.py` | 8.2KB | PARSE_OK | **ADMIT** | Parser v3 byte-exact |
| E28 | `atomizer_v2.py` | 10.4KB | PARSE_OK | **ADMIT** | Enhanced atomizer |
| E28 | `relations_v2.py` | 4.6KB | PARSE_OK | **ADMIT** | 6 relation types |
| E28 | `redact_v2.py` | 6.3KB | PARSE_OK | **ADMIT** | Safe example values only |
| E28 | `PROJECT-PLAN.yaml` | 5.7KB | YAML_OK | **ADMIT** | Structure reference only |

**E29**: DESIGN_REFERENCE_ONLY. All blobs are Base64-wrapped — zero byte copy permitted.

## Phase 1: Implementation Plan

### S1 — Core Pipeline (atomizer + parser + classifier + redact)
- Merge E27 atomizer (21 types) + E28 atomizer_v2 + E29 structural adapter design
- Adopt E28 Parser v3 byte-exact accounting
- Build conservative classifier (default CLAIM, zero lexical FACT promotion)
- Build span-based redaction (no secret-derived hashes/fingerprints)

### S2 — Relations + Schema + CLI
- E28 relations_v2 (SUPPORTS/DEPENDS_ON/REFINES/CONTRADICTS/RAISES_UNKNOWN/VERIFIED_BY)
- E27 schema (with JSON fix) as canonical contract
- CLI wrapper

### S3 — Integrated Pipeline + Tests
- 4-step pipeline: redact → atomize → classify → relate → validate → packet
- 18 test families (70-140 assertions expected)
- Failure-history rejection gates

### S4 — CI + Evidence + Receipt
- 1 tested commit (semantic files) + 1 receipt-only commit (evidence files)
- Exact-head CI: 3.11 + 3.13 matrix, fail-closed
- 3-seed archive deterministic
- Cross-version byte-identical verification

## Phase 2: Verification Contract

| Check | Criterion |
|-------|-----------|
| All adopted files have fresh identity | Each file recorded with source PR/commit/blob SHA |
| No E29 bytes | E29 is design-reference-only |
| No old failure inherited | All 10 historical pollution types blocked |
| Clean UTF-8 | Every file `ast.parse()` or `json.loads()` passes |
| CI visible on GitHub | Workflow file is valid YAML, recognizable by Actions |
| Byte-identical cross-Python | 3.11.10 + 3.13.3 identical output |
| 3-seed deterministic | Archive SHA256 identical across seeds |
| Non-empty receipt | Evidence files only, different tree from tested |

## Budget

| Phase | Est. Points | Status |
|-------|-------------|--------|
| Phase 0 (Audit) | 10 | ✅ COMPLETE |
| Phase 1 (Plan PR) | 5 | ✅ COMPLETE |
| S1-S4 Implementation | 450-600 | PENDING |
| **Target** | **450-650** | |
| **Hard stop** | **700** | |
