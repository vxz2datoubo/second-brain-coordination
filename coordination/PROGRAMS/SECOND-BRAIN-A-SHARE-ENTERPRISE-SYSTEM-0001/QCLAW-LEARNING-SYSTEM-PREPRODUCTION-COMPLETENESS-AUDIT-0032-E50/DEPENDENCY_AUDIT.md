# E50 Dependency Audit (R3)

## Decision: ZERO third-party dependencies

E50 audit harness is implemented entirely in Python standard library:

- `hashlib` (SHA-256, deterministic git blob SHA)
- `unicodedata` (NFC normalization for cross-Python determinism)
- `json` (serialization, canonicalization)
- `dataclasses` (immutable records)
- `enum` (verdict enums)
- `typing` (type hints)
- `unittest` (test framework)
- `subprocess` (read-only `git rev-parse HEAD` binding; falls back to .git file read)
- `tempfile` / `os` (D12 rollback probe)

## Rationale

E50 audits the **authoritative checked-out canonical modules** (PHASE-3
`integrated_offline_memory`, PHASE-3 `local_adapter`, PHASE-2
`offline_research`, CODEX-E66 `e66_promotion`). Those canonical modules are
themselves standard-library only. E50 inherits that constraint and adds no
new runtime dependency.

## Why not add libraries

- `pytest`: not needed; `unittest` discover handles all tests.
- `pydantic`: not needed; dataclasses with `__post_init__` provide immutability.
- `numpy`: not needed; content hashing + NFC normalization is enough.
- `psutil`: deliberately NOT added. R3 D12 must NOT synthesize a PASS when
  descendant enumeration is impossible. Without psutil, D12 reports the
  lifecycle measurement as UNKNOWN → PARTIAL. (Adding psutil just to flip a
  verdict would be a false instrumentation.)
- network libs (requests / aiohttp): not needed; the audit reads the
  checked-out tree and uses git metadata only.

## Trade-offs

- Pro: zero dependency conflicts, deterministic installs, easy CI, no security
  surface.
- Con: no library-supported testing helpers (8 tests cover all paths).
- Con: no psutil means D12 descendant enumeration is UNKNOWN, reported honestly
  as PARTIAL.

## Conclusion

E50 audit harness + tests run on plain Python 3.11 / 3.13 with no pip install
step. CI runs `python -m unittest discover` + `canary/build_evidence_matrix.py`
directly. This is a deliberate choice aligned with the AMED
`no new dependencies` constraint for STRATEGIC tasks and the R3 requirement
that unmeasurable resource lifecycle be reported as UNKNOWN/PARTIAL, not PASS.
