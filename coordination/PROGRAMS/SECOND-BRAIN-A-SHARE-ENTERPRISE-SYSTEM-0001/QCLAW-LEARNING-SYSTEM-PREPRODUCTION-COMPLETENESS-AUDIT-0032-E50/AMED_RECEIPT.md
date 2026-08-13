# E50 R2 AMED Receipt

## Mission Intent

Independently audit whether the second-brain learning system is sufficiently
complete to support real/private high-value source learning, before any
real-source pilot is released. R2 corrects R1's core defect: R1 awarded PASS
credit to E50-local stand-ins instead of auditing the canonical system.

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

## R1 → R2 correction

R1 was REJECTED because D4/D5/D6/D7/D8/D9 "PASS" results came from E50-local
stand-ins (CrossSourceMaster, cognition helper, SkillCandidate, local retrieval
dict, local Codex boundary). R2:

1. Vendored the canonical PHASE-3 `integrated_offline_memory` package
   (MemoryStore / retrieval / conversation_memory / learning_packet /
   contracts / schema_validation / canonical) + CODEX-E66 `e66_promotion` +
   PHASE-2 `offline_research` as a read-only `canonical/` snapshot.
2. Demoted all R1 stand-ins to `_untrusted_test_double/` (no canonical PASS credit).
3. Rewrote every dimension (D1-D12) to call the canonical paths directly.
4. Rebound the audit to the exact canonical head.

## Active Discovery Duty (honest findings)

- **D3 (PARTIAL)**: canonical `MemoryStore._validate_atom` accepts free-form
  `atom_type` — the 13-type taxonomy is NOT enforced on main; canonical fixtures
  use only 5 types (rule/observation/strategy/contract/procedure).
- **D5 (PARTIAL)**: canonical main uses `verification_status`/`evidence_quality`
  (free-form) + `FieldSemanticDecision` (3-status enum); the E47/E48 5-way
  `EvidenceKind` exists only on the E48 PR branch, not main.
- **D10 (PARTIAL)**: canonical prompt-injection defense is a fixed 4-marker
  list; paraphrased injection is NOT caught (bounded fail-safe gap).

## Improvement Authority

- A (safe local autonomous): vendored canonical snapshot (read-only), wrote
  D1-D12 audit modules, coverage report, risk-critical recommendation, unit tests.
- B (bounded implementation with evidence/tests/rollback): audit harness with
  deterministic evidence matrix; rollback via tempdir + no repo mutation.
- C (proposal only): taxonomy/EvidenceKind/prompt-injection fixes listed as
  FUTURE work in UNKNOWN-REGISTRY.md — NOT implemented in E50.
- D (prohibited / user gate): NOT triggered (no formal write, no merge, no
  credentials, no scope expansion).

## Exploration Budget

- primary delivery (canonical audit D1-D12 + evidence matrix): ~80%
- active discovery (3 blocking gaps reported + DigestBundle placeholder
  finding): ~15%
- system opportunity (CI workflow qclaw-e50-preproduction-audit.yml): ~5%

## Engineering Correctness

- 6 unit tests pass on Python 3.13.3 (`tests/test_audit.py`)
- Canonical head bound: `06474d7386db5a4e416e48d8c81cf0dd327328b3`
- Determinism verified (content_hash sort_keys order-independent)
- Resource postflight: no orphan children, no unrelated terminations

## Recommendation (risk-critical)

`NOT_READY` — 3 critical gates are PARTIAL (D3 taxonomy, D5 evidence-kind,
D10 prompt-injection generalization). Production candidate learning is never
self-issued; `READY_FOR_BOUNDED_REAL_SOURCE_PILOT` requires GPT acceptance of
E50 after all critical gates PASS.

## Next Action

Publish Issue #243 R2 handoff comment with the evidence matrix + recommendation.
Stop. Await GPT R2 review.
