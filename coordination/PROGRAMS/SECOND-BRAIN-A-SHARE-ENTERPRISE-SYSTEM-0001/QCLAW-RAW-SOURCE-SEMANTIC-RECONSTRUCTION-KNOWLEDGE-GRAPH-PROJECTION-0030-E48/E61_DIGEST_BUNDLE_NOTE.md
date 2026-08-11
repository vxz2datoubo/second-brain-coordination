# E61 compatibility digest bundle — added to E48 scope

> **Source of change:** GitHub Issue #216 comment #5249272794 (GPT/Codex Connector,
> 2026-08-11T05:18:00Z). Comment is reproduced in `ISSUE-216-COMMENT-2-E61-CROSS-AGENT-DELTA.md`.

## Baseline drift note

- E48 branch `qclaw/raw-source-semantic-reconstruction-graph-projection-0030-e48`
  was created from canonical main `a6c9b1a2`.
- Canonical main moved to `f8dfc7295d0af22e0d41e5f1b2b16ad9c7d82772`
  (commit `route: require provider-specific E61 authority decision before user approval`,
  authored 2026-08-11T05:15:58Z).
- We do **not** rebase / force-push / amend existing commits. We add new commits on top
  and document the drift. The PR description will surface this to GPT for an explicit
  base-commit choice at handoff time.

## E48 must incorporate (within existing L0→L1→L2→L3 plan)

Three 64-hex SHA-256 digests, each with a precise canonicalization contract:

| Field | Input | Excludes | Notes |
|-------|-------|----------|-------|
| `raw_artifact_sha256` | exact serialized L2 candidate artifact / bundle bytes | n/a | full 64-hex |
| `canonical_semantic_sha256` | deterministic canonical semantic representation of the L2 candidate package | volatile ingestion timestamps, UI/layout state, other non-semantic projections | full 64-hex, cross-Python 3.11/3.13 |
| `l0_provenance_sha256` | immutable L0 raw-source identity + exact source/span/provenance manifest required to verify the L2 evidence chain | lossy normalized substitutes | full 64-hex |

## Hard rules (verbatim from comment)

1. Keep the legacy short `content_hash` (16-hex, E47 compatibility) only for compatibility.
   **Never** call it a production identity.
2. L1 `NormalizedSemanticView` and L3 `KnowledgeGraphProjection` remain derived
   projections. Separate derived hashes are allowed but must **not** promote them
   to authority merely because they have hashes.
3. `canonical_semantic_sha256` MUST be deterministic across supported Python 3.11/3.13
   runs and must not drift due to timestamp/order/serialization noise.
4. `l0_provenance_sha256` MUST preserve traceability to exact L0 spans and MUST NOT
   replace raw evidence identity with a normalized substitute.
5. Mutation tests MUST prove:
   - semantic changes alter `canonical_semantic_sha256`,
   - source changes alter `l0_provenance_sha256`,
   - volatile / non-semantic field changes do **not** alter `canonical_semantic_sha256`.
6. PUBLIC_SAFE synthetic fixtures only. No private user transcript in public tests.
7. This does **not** authorize formal PROJECT/GLOBAL persistence, new authority, cloud
   service, credential, merge, or trading action.

## Implementation boundary check

This addition is **bounded** (Improvement Authority level B — "有界 schema 适配器 / 导出
/ UI 改良,带证据/测试/回滚"). It is internal to E48 modules:

- `qclaw_e48_reconstruction/digests.py` — deterministic hash helpers.
- `qclaw_e48_reconstruction/l1_schema.py` — L1 view carries a derived `view_sha256`.
- `qclaw_e48_reconstruction/l3_schema.py` — L3 graph carries `projection_sha256`.
- `tests/test_digests.py` — mutation tests.
- `tests/test_l1_l3_round_trip.py` — E47 reuse check + digest stability.

We do **not** introduce a new shared canonical schema (level C), we do not mint a new
authority (level D), we do not implement the external issuer or formal-write gate.

## Stop boundary check

None of the comment's hard rules triggers a STOP. We proceed and report at handoff.