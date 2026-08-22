# E45 verified-capability semantic authority closure

## Route Identity

- task_id: QCLAW-E44-POST-AUDIT-VERIFIER-ONLY-CAPABILITY-USER-ORIGIN-SEMANTIC-EVALUATOR-REAL-MUTATION-AND-DUAL-PROVIDER-CLOSURE-0026-E45
- route_epoch: 45
- source: Issue #187 / PR #189 / frozen_head `846861da`
- formal_review: `coordination/ENGINEERING-LEARNING/REVIEWS/QCLAW-E44-INDEPENDENT-AUDIT-RETURN-TO-E45.yaml`

## Core Constraint

E45 must treat Codex E58's verifier-only capability as the sole low-level trust anchor. E45:
- Does NOT create its own trusted issuer/HMAC key/caller-constructible verifier
- Does NOT infer user origin from prose ("I know", pronouns)
- Does NOT expose registries to callers
- Does NOT pass ground truth/expected outcomes into production pipeline

## Phase Plan

### Q0 — Plan-only, tree_scope_gate, E44-SOURCE-SELECTION
- First commit: exactly one added QCLAW-E45/PROJECT-PLAN.md
- Blob-level diff: zero deleted, zero modified
- Open Draft PR + literal TaskLeaseClaim

### Q1 — Verifier-only VerifiedEvidenceCapabilityView
- Consumer protocol consuming Codex E58 verifier interface
- UNTRUSTED_TEST_DOUBLE for task-local testing
- Explicit boundary: does not claim canonical production capability

### Q2 — Derivation-only EvidenceRegistry/EvidenceFactory
- Every field recomputed from capability + policy, not caller-supplied
- No mutable issued registries, no caller HMAC keys, no partial signatures
- Registry insertion private + identity-bound

### Q3 — Master/cognition/skill from verified evidence
- KNOWN_AND_STATED requires exact verified user-message origin
- Explicit user facts need verified evidence binding to exact source span
- Master transitions, contradiction classification, skill promotions from independently issued evaluator receipts
- Caller counts/booleans/scope overrides forbidden

### Q4 — Separated ground-truth corpus evaluator
- Production input and ground truth are different types
- Production never receives expected outcomes, should_fail, anti-pattern labels
- Deterministic canonical output: actual outcomes, authority checks, mutation coverage
- No timestamp/Python/seed environment fields in canonical output

### Q5 — Genuine isolated copied-production mutations
- Each: unique exact byte replacement, named invariant test, nonzero mutant exit
- Exact byte restoration, restored-green rerun, duration + stream hashes
- Execute every mutation in every Provider matrix job

### Q6 — Dual Provider CI
- Python 3.11/3.13 × seeds 0/1/777 = 6 matrix jobs + 1 strict compare
- Route-consistent artifact contract
- Independently download/verify tested run
- One receipt-only direct child, repeat receipt-head Provider
- Publish literal external anchor

## Authorized Paths

- `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-E45/**`
- `.github/workflows/qclaw-e45-semantic-authority-evaluation.yml`

All other paths read-only. PR #189 and all predecessor branches frozen. Codex E58 paths read-only.
