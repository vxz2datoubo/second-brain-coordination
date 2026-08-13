# E50 R3 Unknown Registry

Authoritative checked-out-tree audit (E50 branch HEAD
`eb9ce813c01169e7c925b9715354eec9ee96f716`). All findings below are honest
gaps discovered by auditing the authoritative canonical modules directly from
the checked-out repository tree (PHASE-3 `integrated_offline_memory`,
PHASE-3 `local_adapter`, PHASE-2 `offline_research`, CODEX-E66 `e66_promotion`),
NOT by E50-local stand-ins (demoted to `_untrusted_test_double/`).

## Blocking findings (critical gates PARTIAL)

### B-001 (D3) — No 13-type atom taxonomy enforced on canonical main

Canonical `MemoryStore._validate_atom` accepts free-form `atom_type` (only
requires it be a non-empty string in the required-field set). There is NO
enum/constraint enforcing the D3 required taxonomy:

concept / definition / mechanism / causal_chain / condition / counterexample
/ indicator / data_source / scope / failure_condition / verification_method
/ hypothesis / executable_action.

Canonical fixtures use only 5 types: rule / observation / strategy / contract
/ procedure.

**Status**: real gap. `_validate_atom` enforces authority_level=CANDIDATE_ONLY,
required fields, truth-state, and secret scan — but NOT taxonomy.

**Fix path**: separate implementation task adds a taxonomy validation constant
to `schema_validation.py` / `_validate_atom`. NOT implemented in E50 (audit
must not implement missing production features to pass).

### B-002 (D5) — E47/E48 5-way EvidenceKind absent from canonical main

Canonical uses `verification_status` + `evidence_quality` (both free-form text,
default UNVERIFIED / UNKNOWN) plus `FieldSemanticDecision` (field-level status
enum VERIFIED / PARTIAL_FIELD_EVIDENCE / UNKNOWN). The E47/E48 5-way
`EvidenceKind` (SOURCE_EXTRACT / USER_CLAIM / EXTERNAL_CLAIM / INFERENCE /
VALUE_JUDGMENT) exists only on the E48 PR branch, not canonical main.

**Status**: real gap. Evidence-gap honesty holds (volume=UNKNOWN is honest),
but the strict 5-way epistemic classification is not a canonical-main contract.

### B-003 (D7) — No executable skill-promotion runtime on canonical main

Canonical has: a SKILLS yaml registry (`coordination/SKILLS/*.yaml` with
lifecycle statuses CANDIDATE_SKILL_REGISTERED / CONTRACTED_NOT_IMPLEMENTED /
etc.) and a PHASE-1 safety gate (`contract_validation.py` approval/replay
envelope). But there is NO executable candidate->experimental->formal state
machine binding transitions to independently-signed test receipts + rollback.
E66 promotion (used for D9) is the Codex knowledge-promotion approval control
flow — it is NOT a skill-learning promotion runtime.

**Status**: real gap. Skill learning/promotion is not implemented as an
executable subsystem on canonical main.

### B-004 (D10) — Fixed-marker prompt-injection list does not catch paraphrasing

Canonical `learning_packet._PROMPT_INJECTION_MARKERS` is a fixed 4-marker
list ("ignore previous instructions", "ignore all instructions",
"system prompt", "developer message"). Direct markers are denied; paraphrased
or indirect injection (e.g. "disregard everything you were told earlier") is
NOT caught.

**Status**: bounded fail-safe gap. Not a silent semantic-corruption failure
(direct injection + secrets + private-source promotion + authority forgery are
all denied), but generalization is weak.

## Non-blocking unknowns

### U-001 (D12) — psutil unavailable on this host

Child-process enumeration fell back to an honest UNKNOWN instead of fabricating
a zero orphan count. The audit spawns only a short-lived read-only
`git rev-parse`, which terminates cleanly. D12 verdict is PARTIAL (not PASS).

### U-002 (D11) — Python 3.11 exercised via CI only

Local audit environment is Python 3.13. Determinism holds across runs (sort_keys
canonicalization + deterministic git blob SHA algorithm). Python 3.11 matrix
verification runs in the `qclaw-e50-preproduction-audit` workflow (with
cross-version canonicalized matrix compare), not locally.

## Resolved (not unknowns)

- Deterministic digest: `canonical.content_hash` / `canonical_json` use
  sort_keys + NFKC + whitespace normalization — order-independent across runs.
- Supersession recall: CURRENT intent returns superseding atom, excludes
  superseded; HISTORICAL intent (valid_at set) returns it.
- Authority boundary: `_validate_atom` forces authority_level=CANDIDATE_ONLY;
  E66 promotion requires full approval-control binding.
- Secret rejection: `_SECRET` regex (ghp_/github_pat_/sk-/PRIVATE KEY) + value
  keys denied at packet build time.
- Authoritative ref binding: every canonical group binds exact per-file git
  blob SHA (deterministic `sha1(b"blob <len>\0" + data)`), no hard-coded paths.

## Future work (proposals, NOT in E50 scope)

- Add 13-type taxonomy validation to canonical `_validate_atom` / schema_validation.
- Promote E47/E48 5-way EvidenceKind to a canonical-main contract.
- Expand prompt-injection defense beyond fixed markers (semantic classifier,
  role-bounded parsing).
- Implement an executable skill-learning/promotion runtime with independent
  test receipts + rollback.
