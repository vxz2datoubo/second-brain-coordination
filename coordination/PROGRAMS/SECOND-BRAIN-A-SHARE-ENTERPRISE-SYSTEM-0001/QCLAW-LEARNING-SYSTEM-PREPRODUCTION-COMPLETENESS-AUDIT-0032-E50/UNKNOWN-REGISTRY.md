# E50 R2 Unknown Registry

Canonical-system audit (head `06474d7386db5a4e416e48d8c81cf0dd327328b3`).
All findings below are honest gaps discovered by auditing the canonical
PHASE-3 `integrated_offline_memory` package + CODEX-E66 promotion contract,
NOT by E50-local stand-ins (those are demoted to `_untrusted_test_double/`).

## Blocking findings (critical gates PARTIAL)

### B-001 (D3) — No 13-type atom taxonomy enforced on canonical main

Canonical `MemoryStore._validate_atom` accepts free-form `atom_type` (only
requires it be a non-empty string in the required-field set). There is NO
enum/constraint enforcing the D3 required taxonomy:

concept / definition / mechanism / causal_chain / condition / counterexample
/ indicator / data_source / scope / failure_condition / verification_method
/ hypothesis / executable_action.

Canonical fixtures (`evaluation.py`, `integrated_flow.py`,
`conversation_memory.py`) only use 5 types: rule / observation / strategy /
contract / procedure.

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

### B-003 (D10) — Fixed-marker prompt-injection list does not catch paraphrasing

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

Child-process enumeration fell back to an honest "psutil not installed" note
instead of fabricating a zero orphan count. The audit spawns only a short-lived
read-only `git rev-parse`, which terminates cleanly.

### U-002 (D11) — Python 3.11 exercised via CI only

Local audit environment is Python 3.13. Determinism holds across runs (sort_keys
canonicalization); Python 3.11 matrix verification runs in the
`qclaw-e50-preproduction-audit` workflow, not locally.

## Resolved (not unknowns)

- Deterministic digest: `canonical.content_hash` / `canonical_json` use
  sort_keys + NFKC + whitespace normalization — order-independent across runs.
- Supersession recall: CURRENT intent returns superseding atom, excludes
  superseded; HISTORICAL intent (valid_at set) returns it.
- Authority boundary: `_validate_atom` forces authority_level=CANDIDATE_ONLY;
  E66 promotion requires full approval-control binding.
- Secret rejection: `_SECRET` regex (ghp_/github_pat_/sk-/PRIVATE KEY) + value
  keys denied at packet build time.

## Future work (proposals, NOT in E50 scope)

- Add 13-type taxonomy validation to canonical `_validate_atom` / schema_validation.
- Promote E47/E48 5-way EvidenceKind to a canonical-main contract.
- Expand prompt-injection defense beyond fixed markers (semantic classifier,
  role-bounded parsing).
