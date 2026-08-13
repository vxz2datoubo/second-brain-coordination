# E50 R3 AMED Receipt

## Mission Intent

Independently audit whether the second-brain learning system is sufficiently
complete to support real/private high-value source learning, before any
real-source pilot is released. R3 corrects R2's remaining defects: R2 bound the
audit to a copied `canonical/` snapshot and hard-coded a local Windows clone
path, which both invalidated provider evidence.

## System Position

workstream W3 (knowledge / evidence / conflict / long-term memory)
upstream: USER_SELECTED / GPT_SELECTED raw sources
reused_capability: E48 foundation (accepted by GPT, review_id 4915512021)
downstream: candidate knowledge audit + E61-controlled formal persistence
            (still BLOCKED)

## Hard Boundaries (all held)

- No private/high-value user source ingestion (PUBLIC_SAFE_GENERALIZATION_ONLY)
- No authoritative PROJECT/GLOBAL persistence
- No automatic formal skill/trading-rule promotion
- No fabricated coverage quotas or invented relations
- No merge/rebase/force/amend/history rewrite (additive-only on E50 branch)
- No secrets/credentials/accounts/trading
- Did not touch Codex or E48 worktrees/branches

## R2 → R3 correction

R2 was REJECTED on five findings. R3 fixes each:

1. **PROVIDER_CI (P0-001)**: removed hard-coded Windows clone path. The audit
   now computes the repo root by walking up from the package (no absolute
   path); D11/D12 bind HEAD via `git rev-parse HEAD` with a `.git`-file
   fallback; blob SHAs are computed with the deterministic
   `sha1(b"blob <len>\0" + data)` algorithm (no git binary required).
2. **AUDIT_AUTHORITY (P0-002)**: deleted the `src/qclaw_e50_audit/canonical/**`
   snapshot entirely. All dimensions import the authoritative checked-out tree
   via `authoritative.setup_import_path()` (PHASE-3 / local_adapter /
   PHASE-2 / CODEX-E66 src roots). The evidence matrix now records
   `audited_tree_root` (not `vendor_root`).
3. **SKILL_LEARNING (B03)**: D7 now audits the real skill lifecycle
   (coordination/SKILLS/*.yaml registry + PHASE-1 contract_validation safety
   gate). Finding: there is NO executable candidate->experimental->formal
   runtime binding transitions to independent test receipts + rollback →
   D7 = PARTIAL (not PASS).
4. **RESOURCE_MEASUREMENT (B04)**: D12 no longer synthesizes PASS when psutil
   is unavailable; descendant/orphan enumeration is UNKNOWN → D12 = PARTIAL.
5. **CANONICAL_REF_BINDING (B05)**: every canonical dependency group binds an
   exact per-file git blob SHA (see `canonical_ref_bindings()`), independent of
   control-plane assumptions.

## Active Discovery Duty (honest findings)

- **D3 (PARTIAL)**: canonical `MemoryStore._validate_atom` accepts free-form
  `atom_type` — the 13-type taxonomy is NOT enforced on main; canonical fixtures
  use only 5 types (rule/observation/strategy/contract/procedure).
- **D5 (PARTIAL)**: canonical main uses `verification_status`/`evidence_quality`
  (free-form) + `FieldSemanticDecision` (3-status enum); the E47/E48 5-way
  `EvidenceKind` exists only on the E48 PR branch, not main.
- **D7 (PARTIAL)**: no executable skill-promotion runtime on canonical main.
- **D10 (PARTIAL)**: canonical prompt-injection defense is a fixed 4-marker
  list; paraphrased injection is NOT caught (bounded fail-safe gap).
- **D12 (PARTIAL)**: descendant/orphan lifecycle is UNKNOWN (psutil unavailable
  at audit time); rollback + no-unrelated-termination measured PASS.

## Improvement Authority

- A (safe local autonomous): authoritative-path audit modules, coverage report,
  risk-critical recommendation, unit tests, evidence matrix.
- B (bounded implementation with evidence/tests/rollback): audit harness with
  deterministic evidence matrix + canonicalized cross-version compare; rollback
  via tempdir + no repo mutation.
- C (proposal only): taxonomy/EvidenceKind/prompt-injection/skill-promotion
  fixes listed as FUTURE work in UNKNOWN-REGISTRY.md — NOT implemented in E50.
- D (prohibited / user gate): NOT triggered (no formal write, no merge, no
  credentials, no scope expansion).

## Exploration Budget

- primary delivery (authoritative audit D1-D12 + evidence matrix): ~80%
- active discovery (5 blocking gap findings): ~15%
- system opportunity (CI workflow qclaw-e50-preproduction-audit.yml): ~5%

## Engineering Correctness

- 8 unit tests pass on Python 3.13.3 (`tests/test_audit.py`)
- Audited HEAD bound: `eb9ce813c01169e7c925b9715354eec9ee96f716` (E50 branch)
- Per-file blob SHA bindings in `canonical_ref_bindings()` (deterministic)
- Determinism verified (content_hash sort_keys order-independent)
- CI: Python 3.11 + 3.13 matrix, cross-version canonicalized matrix compare
- Resource postflight: no unrelated terminations; descendant enumeration UNKNOWN
  (psutil unavailable) — reported honestly, not synthesized as PASS

## Recommendation (risk-critical)

`NOT_READY` — critical gates not all PASS: D3 (taxonomy), D5 (evidence-kind),
D7 (skill-promotion), D10 (prompt-injection generalization). Production
candidate learning is never self-issued; `READY_FOR_BOUNDED_REAL_SOURCE_PILOT`
requires GPT acceptance of E50 after all critical gates PASS.

## Next Action

Publish Issue #243 R3 handoff comment with the evidence matrix + recommendation.
Stop. Await GPT R3 review.
