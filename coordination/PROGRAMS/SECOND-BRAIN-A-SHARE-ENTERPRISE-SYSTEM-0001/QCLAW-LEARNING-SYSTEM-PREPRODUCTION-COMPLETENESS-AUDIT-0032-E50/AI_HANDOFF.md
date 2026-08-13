# E50 — Learning-System Preproduction Completeness Audit + Generalization Hardening

## QCLAW Identity Card

| Field | Value |
|---|---|
| task_id | QCLAW-LEARNING-SYSTEM-PREPRODUCTION-COMPLETENESS-AUDIT-0032-E50 |
| route_epoch | 59 (control plane) / R3 remediation |
| mode | project_plan |
| status (lease claim) | READY_REMEDIATION → EVIDENCE_READY_FOR_GPT_REVIEW |
| branch | qclaw/learning-system-preproduction-completeness-audit-0032-e50 |
| PR | #244 |
| issue | #243 |
| completion_signal | QCLAW_E50_R3_AUTHORITATIVE_PROVIDER_BOUND_COMPLETENESS_AUDIT_READY_FOR_GPT_REVIEW |
| merge_authorized | false |
| audited HEAD | eb9ce813c01169e7c925b9715354eec9ee96f716 (E50 branch) |
| foundation_credit | E48 head e018fc1 (accepted by GPT, review_id 4915512021) |

## What this is

E50 is a bounded public-safe audit of the second-brain learning system across
D1–D12 dimensions. E48 proved a narrow semantic/provenance foundation; E50
audits whether that foundation + the canonical subsystems (PHASE-3 offline
memory, local adapter, PHASE-2 offline research, CODEX-E66 promotion) cover the
full learning lifecycle well enough to allow real/private high-value source
learning.

This is **not** a feature-completion project. It is an honesty audit: where the
canonical system has gaps, we report them as PARTIAL or FAIL; we do not
fabricate coverage, and we do not award PASS credit to E50-local stand-ins.

## R2 → R3 correction (why this revision exists)

R2 was REJECTED (GPT review_id 4922729153) on five findings:

1. **P0-001 PROVIDER_CI** — hard-coded Windows clone path broke CI.
2. **P0-002 AUDIT_AUTHORITY** — copied `canonical/` snapshot earned PASS credit.
3. **B03 SKILL_LEARNING** — E66 promotion was misattributed as D7 skill learning.
4. **B04 RESOURCE_MEASUREMENT** — synthesized PASS when psutil unavailable.
5. **B05 CANONICAL_REF_BINDING** — no exact source-file/blob binding.

R3 resolves all five (see AMED_RECEIPT.md § "R2 → R3 correction").

## Audit method (authoritative direct-path)

The audit imports the authoritative modules **directly from the checked-out
repository tree** — no vendored copies:

- `PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/*` (MemoryStore, retrieval/QueryPlan/ContextAssembler, conversation_memory, learning_packet, contracts, canonical)
- `PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION/src/local_adapter/*` (contracts)
- `PHASE-2-OFFLINE-VERTICAL-SLICE/src/offline_research/*` (engine)
- `CODEX-E66/src/e66_promotion.py` (top-level module)

Each dependency group is bound to an exact per-file git blob SHA (deterministic
`sha1(b"blob <len>\0" + data)`, no git binary, no hard-coded path). The repo
root is computed by walking up from the package; HEAD is bound via
`git rev-parse HEAD` with a `.git`-file fallback.

## D1–D12 Evidence Matrix (R3, authoritative)

| D | Verdict | Critical | Finding |
|---|---|---|---|
| D1 source ingestion / privacy / provenance | **PASS** | yes | secret regex + privacy-class denial + immutable provenance |
| D2 semantic reconstruction | **PASS** | no | E48 foundation L1 reconstruction (accepted foundation) |
| D3 broad atom taxonomy + epistemic separation | **PARTIAL** | yes | free-form atom_type; 13-type taxonomy not enforced |
| D4 cross-source mastering | **PASS** | yes | atom_id + content_hash dedup + supersession via packet |
| D5 evidence verification | **PARTIAL** | yes | 5-way EvidenceKind absent from main; gap-honesty holds |
| D6 verified user-origin cognition | **PASS** | yes | ConversationEpisode provenance; ASSISTANT_* rejected as user memory |
| D7 skill promotion + rollback | **PARTIAL** | yes | no executable promotion runtime on canonical main |
| D8 retrieval / reuse / correction round-trip | **PASS** | yes | CURRENT excludes superseded; HISTORICAL returns it |
| D9 Codex candidate/formal promotion boundary | **PASS** | yes | E66 approval-control binding; CANDIDATE_ONLY |
| D10 multi-domain adversarial / generalization | **PARTIAL** | yes | fixed 4-marker injection list; paraphrasing not caught |
| D11 determinism + CI | **PASS** | no | deterministic digests; HEAD + blob SHA bound; CI 3.11/3.13 |
| D12 resource + rollback | **PARTIAL** | no | descendant enumeration UNKNOWN (psutil unavailable) |

## Explicit Readiness Recommendation (risk-critical)

```
NOT_READY
```

**Rationale**: 4 critical gates are not PASS (D3 taxonomy, D5 evidence-kind,
D7 skill-promotion, D10 prompt-injection generalization). Per E50 hard
boundaries, any unresolved authority/provenance/privacy/stale-recall/
skill-promotion gap keeps the system NOT_READY. Production candidate learning
is never self-issued.

## Coverage Report (derived from D3 ground truth, not fabricated)

- fixture_total: 13 (the 13 required atom taxonomy types)
- correctly_extracted: 5 (rule/observation/strategy/contract/procedure)
- missed: 0
- distorted: 0
- unsupported: 8

The 8 unsupported taxonomy types are honest gaps (canonical `atom_type` is
free-form), not fabricated coverage quotas.

## Determinism

- `content_hash` / `canonical_json` use sort_keys (order-independent)
- git blob SHA algorithm is deterministic and Python-version-independent
- HEAD + per-file blob SHAs bound in `canonical_ref_bindings()`
- CI runs Python 3.11 + 3.13 with cross-version canonicalized matrix compare

## Hard boundaries respected

- No private source ingested (PUBLIC_SAFE_GENERALIZATION_ONLY)
- No PROJECT/GLOBAL persistence (formal_persistence all false)
- No automatic formal skill promotion
- No fabricated coverage quotas or invented relations
- No rebase/force/amend/merge/history rewrite (additive-only)
- No secrets / credentials / accounts / trading
- Did not touch Codex or E48 worktrees/branches

## Files (R3 revision)

- `PROJECT-PLAN.md` — E50 plan
- `src/qclaw_e48_foundation/` — frozen E48 foundation (accepted foundation credit only)
- `src/qclaw_e50_audit/` — audit harness:
  - `authoritative.py` — direct-path import + HEAD/blob-SHA binding (new)
  - `dimensions/d1_ingestion.py` … `d12_resource.py` — D1–D12 audit modules
  - `coverage.py` — ground-truth coverage report
  - `recommendation.py` — risk-critical recommendation
  - `runner.py` — orchestration
  - `evidence_matrix.py` — evidence schema
  - `_untrusted_test_double/` — R1 stand-ins (NO canonical PASS credit)
- `tests/test_audit.py` — 8 unit tests
- `canary/build_evidence_matrix.py` — regenerate evidence matrix
- `evidence/evidence_matrix.json` — serialized D1–D12 evidence matrix
- `AI_HANDOFF.md` — this document
- `AMED_RECEIPT.md` — AMED-policy receipt (R3)
- `DEPENDENCY_AUDIT.md` — zero third-party dependencies
- `UNKNOWN-REGISTRY.md` — blocking gaps + unknowns (R3)

## Stop / handoff

QCLAW does not self-merge. PR remains Draft. This handoff is published to
Issue #243.

After this commit:
- Push additive commits (no rebase/force/amend)
- Trigger E50 CI (Python 3.11 + 3.13 matrix)
- Stop. Await GPT R3 review on Issue #243.
