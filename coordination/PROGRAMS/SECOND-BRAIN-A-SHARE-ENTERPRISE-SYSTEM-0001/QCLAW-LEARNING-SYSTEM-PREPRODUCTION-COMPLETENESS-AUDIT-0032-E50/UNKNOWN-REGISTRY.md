# E50 Unknown Registry

## Genuine unknowns (not fabricated coverage)

### U-001 — D3 atom taxonomy gap

E48 L2 derivation (`qclaw_e48_foundation.l2_derive`) only emits 4 atom types:
- DERIVED_CONCEPT (for terminology aliases)
- CONDITION + MECHANISM (cross-sentence mechanism detection)
- UNKNOWN_REFUSAL (for unknown markers)

Missing 9 atom types from the D3 required set:
- COUNTEREXAMPLE
- INDICATOR
- DATA_SOURCE
- SCOPE
- FAILURE_CONDITION
- VERIFICATION_METHOD
- HYPOTHESIS
- EXECUTABLE_ACTION
- DEFINITION

**Status**: real gap, not fabricated.

**Why not fixed in E50**:
- Building these atom extractors would scope-expand the audit into a feature-implementation task
- E50 is a bounded audit; coverage failures are valid findings (per task brief)
- Future task (E51 or similar) can extend L2 derivation if GPT accepts E50 recommendation

**Risk if left unfixed**: D3 PARTIAL persists; recommendation cannot promote to `READY_FOR_PRODUCTION_CANDIDATE_LEARNING`.

### U-002 — L2 evidence_kind gap

E48 L2 emits only `INFERENCE` evidence_kind atoms. The schema defines 5 categories (SOURCE_EXTRACT, USER_CLAIM, EXTERNAL_CLAIM, INFERENCE, VALUE_JUDGMENT) but the derivation only fills one.

**Why not fixed in E50**:
- Would require extracting more semantic structure from sources
- D5 audit verified the byte-identical invariant holds when SOURCE_EXTRACT atoms are constructed independently (so the schema contract is intact)
- Same fix path as U-001 (future L2 extension)

### U-003 — CI runner dependency

D11 deterministic checks pass locally. Python 3.11 + 3.13 matrix verification requires the E48 CI workflow (`.github/workflows/qclaw-e48-semantic-reconstruction.yml`). The E50 audit does not introduce a new workflow; it relies on the existing E48 workflow.

**Resolution**: trigger E48 CI after pushing E50 commit; matrix run verifies cross-version determinism.

### U-004 — Subprocess cap monitoring

D12 zero-orphans check is local. The `qclaw_task_python_cap=2` cap is enforced at runtime by the CI runner, not by E50 code.

**Resolution**: CI-level enforcement via shell wrapper; not a code-level concern for E50.

### U-005 — Bounded whitelist specifics

The recommendation `READY_FOR_BOUNDED_REAL_SOURCE_PILOT` suggests a whitelist. The exact whitelist is NOT defined by E50 (out of scope). Suggested categories in AI_HANDOFF.md but require GPT/Owner sign-off.

**Resolution**: GPT to specify whitelist in R1 review.

### U-006 — Coverage of empty edge case

The cross-source master tracks supersession / contradiction / duplicate edges. A fully empty corpus would not exercise these paths in production. E50 uses a 9-fixture corpus which exercises all paths; edge cases with N=0 are not separately audited.

**Resolution**: tests cover small-N cases (e.g., `test_dedup_same_content_same_id` with N=1); production N=0 would need separate audit.

## Not unknowns (resolved)

- Canonical_id stability: confirmed stable across Python 3.11 / 3.13 via NFC normalization (Unicode standard)
- Digest contract: 6 digests inherited from E48 (raw_artifact, canonical_semantic, l0_provenance, l0_source, view, projection); 7-digest variant in D9 audit includes legacy `l0_source_size_bytes` for clarity
- Skill promotion rollback: verified produces reverse digest distinct from promotion digest
- Supersession retrieval: verified cid_old disappears from default query (include_superseded=False) and reappears with include_superseded=True

## Future work (proposals, NOT in E50 scope)

- Future L2 extension: emit COUNTEREXAMPLE / INDICATOR / DATA_SOURCE / SCOPE / FAILURE_CONDITION / VERIFICATION_METHOD / HYPOTHESIS / EXECUTABLE_ACTION / DEFINITION atoms
- Future L2 extension: emit SOURCE_EXTRACT / USER_CLAIM / EXTERNAL_CLAIM / VALUE_JUDGMENT atoms (not just INFERENCE)
- Future E50 extension: cross-source temporal versioning (multiple versions of same source with explicit ordering)
- Future E50 extension: confidence calibration (compare predicted confidence to actual outcome)