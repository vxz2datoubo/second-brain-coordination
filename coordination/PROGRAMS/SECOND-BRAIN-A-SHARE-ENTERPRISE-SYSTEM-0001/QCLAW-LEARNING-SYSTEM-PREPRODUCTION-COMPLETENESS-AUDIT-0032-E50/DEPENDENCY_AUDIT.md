# E50 Dependency Audit

## Decision: ZERO third-party dependencies

E50 audit harness is implemented entirely in Python standard library:

- `hashlib` (SHA-256)
- `unicodedata` (NFC normalization for cross-Python determinism)
- `json` (serialization)
- `dataclasses` (immutable records)
- `enum` (verdict enums)
- `typing` (type hints)
- `unittest` (test framework)

## Rationale

The vendored E48 foundation (`qclaw_e48_foundation/`) was already zero-dependency (per E48 DEPENDENCY_AUDIT.md and R2 acceptance). E50 inherits that constraint.

E50 audit modules add:
- ingestion: hashlib + dataclasses
- corpus: dataclasses only
- cross_source: hashlib + unicodedata
- cognition: dataclasses + enum
- skill_promotion: dataclasses + json
- retrieval: dataclasses
- codex_boundary: dataclasses + json
- audit_runner: json + os + sys
- recommendation: dataclasses

## Why not add libraries

- `pytest`: not needed; `unittest` discover handles all tests
- `pydantic`: not needed; dataclasses with `__post_init__` provide the immutability
- `numpy`: not needed; canonical_id hashing + NFC normalization is enough
- `psutil`: not needed for D12 (zero subprocess detection at runtime; CI-level monitoring)
- network libs (requests / aiohttp): not needed; E50 reads from local vendored foundation, no remote calls during evaluation

## Trade-offs

- Pro: zero dependency conflicts, deterministic installs, easy CI, no security surface
- Con: no library-supported testing helpers (but 25 tests cover all paths)
- Con: no advanced graph algorithms (but D4 only needs identity / dedup / supersession, not graph algorithms)

## Conclusion

E50 audit harness + tests run on plain Python 3.11 / 3.13 with no pip install step. This is a deliberate choice aligned with E48's vendored snapshot policy and the AMED `no new dependencies` constraint for STRATEGIC tasks.