# E61 digest bundle note (R1)

## Scope

E48 implements a bounded deterministic certification-digest bundle inside the
E48 module, per Issue #216 comment #5249272794. The bundle is **module-local**
(does not introduce a new shared canonical schema across W3 modules).

## Three new 64-hex SHA-256 helpers (in `src/qclaw_e48_reconstruction/digests.py`)

| Helper | Covers | Source of bytes | Excludes volatile |
|--------|--------|-----------------|-------------------|
| `raw_artifact_sha256` | Exact serialized L2 candidate artifact blob | `canary/out/canary_artifact.json` | Nothing (full coverage) |
| `canonical_semantic_sha256` | Deterministic canonical semantic dict (volatile-stripped) | L2 candidate package dict | Yes (see `_VOLATILE_FIELDS`) |
| `l0_provenance_sha256` | Immutable L0 identity + ordered manifest of every L0 span used by L2 | L0 source metadata + atom `source_spans` | Yes |

`l0_source_sha256` (in `NormalizedSemanticView`) is a **separate** digest that
identifies the L0 raw text by itself; it is the parent of `l0_provenance_sha256`
(the latter additionally commits to the exact byte ranges used). Do **not**
call `raw_artifact_sha256` "the L0/raw-source digest" — it is the artifact
digest. The L0 digest is `l0_source_sha256` / `source_hash`.

## Legacy `content_hash` (16-hex)

Kept only for E47 compatibility. It is a 16-hex value, NOT a production
identity, and MUST NOT be relied on for cross-agent identity. It lives in
the legacy `legacy_content_hash_compat_only` field on `DigestBundle` and in
the `content_hash` field of the L2 package.

## R1 fix: persisted exact candidate artifact

As of R1, `raw_artifact_sha256` is computed over the exact bytes of the
persisted `canary/out/canary_artifact.json` (the L2 candidate artifact
serialized once at build time, then hashed). This replaces the prior
behavior of computing the digest over ad-hoc serialized bytes that
might be reformatted by downstream tooling.

The artifact path, size, and the SHA-256 are all reported in
`canary/out/canary_digests.json` so a downstream auditor can re-hash the
persisted blob and confirm identity.

## Determinism contract

- `raw_artifact_sha256` is over the artifact bytes — same artifact file
  → same digest. Re-running `build_canary_projection.py` regenerates the
  artifact deterministically (sorted keys, UTF-8, no whitespace) so the
  digest is stable.
- `canonical_semantic_sha256` is over a canonical dict with volatile fields
  stripped — same semantic content → same digest across runs and across
  Python 3.11 / 3.13.
- `l0_provenance_sha256` is over an ordered manifest — any source mutation
  or span mutation changes the digest; volatile fields (e.g. timestamps)
  do not.

## Mutation-test contract

- Changing `view.normalized_text` (semantic content) → `canonical_semantic_sha256` changes.
- Changing `pkg["source"]["source_hash"]` (L0 identity) → `l0_provenance_sha256` changes; `canonical_semantic_sha256` does NOT (source identity is volatile for the canonical semantic digest).
- Changing `pkg["ingested_at"]` (volatile) → no digest changes.
- Changing `pkg["content_hash"]` (legacy, volatile) → no digest changes.
- Changing `canary_artifact.json` bytes (e.g. key ordering) → `raw_artifact_sha256` changes; `canonical_semantic_sha256` does NOT.

Tests covering this contract: `tests/test_digests.py` (R1 mutation tests
added at the end of the file).