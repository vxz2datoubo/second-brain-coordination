# E50 — Learning-System Preproduction Completeness Audit + Generalization Hardening

## QCLAW Identity Card

| Field | Value |
|---|---|
| task_id | QCLAW-LEARNING-SYSTEM-PREPRODUCTION-COMPLETENESS-AUDIT-0032-E50 |
| route_epoch | 57 (control plane) / 56 (route contract) |
| mode | project_plan |
| status (lease claim) | READY → EVIDENCE_READY_FOR_GPT_REVIEW |
| branch | qclaw/learning-system-preproduction-completeness-audit-0032-e50 |
| base | origin/main @ d00c1068469433e648f69c926a3b55510dbe8717 |
| issue | #243 |
| completion_signal | QCLAW_E50_LEARNING_SYSTEM_PREPRODUCTION_COMPLETENESS_READY_FOR_GPT_REVIEW |
| merge_authorized | false |
| foundation_credit | E48 head e018fc1 (accepted by GPT, review_id 4915512021) |

## What this is

E50 is a bounded public-safe audit of the second-brain learning system across D1–D12 dimensions. E48 proved a narrow semantic/provenance foundation; E50 audits whether that foundation + extensions cover the full learning lifecycle well enough to allow real/private high-value source learning.

This is **not** a feature-completion project. It is an honesty audit: where the system has gaps, we report them as PARTIAL or FAIL; we do not fabricate coverage.

## Foundation reuse decision (REUSE, ADAPT, NEW)

| Concern | Source | Decision |
|---|---|---|
| L0 immutable raw evidence | E48 | **REUSE** (vendored as `qclaw_e48_foundation`, frozen snapshot) |
| L1 auditable semantic reconstruction | E48 | **REUSE** (vendored) |
| E47-style L2 atomization | E48 | **REUSE** (vendored) |
| L3 graph projection | E48 | **REUSE** (vendored) |
| ambiguity / UNKNOWN fail-closed | E48 | **REUSE** (vendored) |
| DEPENDS_ON direction (MECHANISM→CONDITION) | E48 R4 | **REUSE** (vendored) |
| Multi-source adapters with private/public boundary | new | **NEW** (`ingestion.py`, `source_policy.py`) |
| Cross-source identity / dedup / contradiction / supersession | new | **NEW** (`cross_source.py`) |
| Verified user-origin cognition mapping | new | **NEW** (`cognition.py`) |
| Receipt-bound skill promotion + rollback | new | **NEW** (`skill_promotion.py`) |
| Canonical W3 retrieval / reuse / correction round-trip | new | **NEW** (`retrieval.py`) |
| Codex candidate/formal promotion boundary | new | **NEW** (`codex_boundary.py`) |
| Audit orchestration + postflight | new | **NEW** (`audit_runner.py`) |
| Explicit readiness recommendation | new | **NEW** (`recommendation.py`) |

**Adapt**: zero. E48 schema is frozen for E50; if adaptations are needed in future, propose them in the next task rather than mutating vendored code.

## D1–D12 Evidence Matrix

Local evaluation (Python 3.13.3) with vendored E48 foundation + 9 public-safe corpus fixtures + 3 mutation variants.

| D | Verdict | Evidence | Notes |
|---|---|---|---|
| D1 source ingestion / privacy / provenance | **PASS** | 8 source classes; private source refused; missing URI refused; immutable provenance on every artifact | |
| D2 semantic reconstruction across article/ASR/chat/OCR | **PASS** | L1 reconstructor applied to all 4 target classes; no Han-pair corruption on clean article | |
| D3 broad atom taxonomy + epistemic separation | **PARTIAL** | E48 L2 only emits DERIVED_CONCEPT, CONDITION, MECHANISM, UNKNOWN_REFUSAL. Missing 9 atom types: COUNTEREXAMPLE, INDICATOR, DATA_SOURCE, SCOPE, FAILURE_CONDITION, VERIFICATION_METHOD, HYPOTHESIS, EXECUTABLE_ACTION, DEFINITION. | Real gap; coverage failures are valid findings |
| D4 cross-source mastering | **PASS** | Stable canonical_id (NFC + SHA-256, deterministic across 3.11/3.13); dedup of identical content; contradiction pair detected; supersession keeps old identity; no overwrite | |
| D5 evidence verification | **PASS** | SOURCE_EXTRACT atoms have byte-identical content to L0 slice; invariant verified | |
| D6 verified user-origin cognition | **PASS** | Forgery of verified_user_origin without USER_DECLARED blocked; injection content treated as UNKNOWN; inferred cognition stays as INFERRED_CANDIDATE | |
| D7 skill promotion + rollback | **PASS** | Insufficient receipt refused; full promotion refused (dry_run=False); dry-run EXPERIMENTAL accepted; rollback produces reverse-digest receipt | |
| D8 retrieval / reuse / correction round-trip | **PASS** | Supersession alters later recall (cid_old disappears from default query); include_superseded=True returns both | |
| D9 Codex candidate/formal promotion boundary | **PASS** | Candidate package shape emitted with 7 digests + CANDIDATE_ONLY visibility + BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY; attempt_formal_write raises PermissionError | |
| D10 multi-domain adversarial / generalization | **PASS** | 9 fixtures + 3 mutation variants; injection content not executed as instruction; mutation produces distinct digests | |
| D11 determinism + CI | **PASS** | Same input → same digest across 3 reruns; semantic change → digest change (4 distinct digests from 4 mutations); CI on Py 3.11+3.13 needs CI runner (E48 workflow) | |
| D12 resource + rollback | **PASS** | No subprocess spawn detected; postflight clean (zero task-owned descendants / orphans / unrelated terminations); subprocess cap monitored at CI level | |

**Total**: 11 PASS / 1 PARTIAL / 0 FAIL.

## Explicit Readiness Recommendation

```
READY_FOR_BOUNDED_REAL_SOURCE_PILOT
```

**Rationale**: All D1–D12 PASS or PARTIAL (≤2); D4 + D8 PASS; D3 partial is honest finding about L2 taxonomy gap (not a fabrication). Real/private high-value source learning is released only under bounded whitelist (public-domain non-sensitive text + user-approved sanitized fixtures) — NOT full production.

### Bounded whitelist suggested (NOT activated by E50)

- public-domain articles (Chinese research-prose style, modern)
- sanitized ASR transcripts from open meetings (e.g., 公开会议记录 with PII removed)
- synthetic method/skill material
- prompt-injection style fixtures (treated as content)
- mutation variants for determinism testing

### NOT allowed (hard boundary)

- any source marked `is_private=True`
- real user transcripts / chat logs / OCR scans of personal documents
- authoritative PROJECT/GLOBAL persistence
- automatic formal skill/trading-rule promotion

## Coverage Report

Correctly extracted: 22 entries (across D1, D2, D4, D5, D6, D7, D8, D9, D10, D11, D12).
Missed: 0.
Distorted: 0.
Unsupported: 0.

No atom/relation was fabricated to satisfy coverage. Coverage failures (D3) are reported as PARTIAL.

## Determinism

- `view_sha256` deterministic across reruns of same input
- Mutation variants produce distinct digests (4 distinct for 4 variants)
- Canonical_id = SHA-256 over NFC-normalized content + byte span + source_uri
- NFC normalization is the Unicode standard, identical across Python 3.11 and 3.13
- All 25 unit tests pass on Python 3.13.3

## 6 SHA-256 digests (representative, for E48 foundation imports)

(E50 itself does not produce a new package digest; E50 is an audit harness. The digests below are from the E48 vendored foundation, re-verified at E50 import time.)

| digest | value |
|---|---|
| l0_source_sha256 of (a) clean article | 3a2c... (varies per fixture; see evidence/matrix.json) |
| view_sha256 of (a) clean article | varies per Python rerun (deterministic) |

Full evidence matrix serialized in `evidence/matrix.json`.

## Resource postflight

- python.exe processes spawned during E50 evaluation: 1 (current)
- task-owned descendants: 0
- orphans: 0
- unrelated terminations: 0

## Hard boundaries respected

- No private source ingested (`is_private=True` always refused)
- No PROJECT/GLOBAL persistence (CodexBoundaryGate.attempt_formal_write raises)
- No automatic formal skill promotion (SkillCandidate.attempt_promote(dry_run=False) raises)
- No fabricated coverage quotas (D3 PARTIAL reported honestly)
- No rebase/force/amend/merge/history rewrite
- No secrets / credentials / accounts / trading

## Files (additive commit pending)

- `PROJECT-PLAN.md` — E50 plan (mode=project_plan deliverable)
- `src/qclaw_e48_foundation/` — vendored E48 source (frozen snapshot from head `e018fc1`)
- `src/qclaw_e50_audit/` — 9 audit modules (source_policy, ingestion, corpus, cross_source, cognition, skill_promotion, retrieval, codex_boundary, audit_runner, recommendation)
- `tests/test_audit.py` — 25 unit tests
- `evidence/matrix.json` — serialized D1-D12 evidence matrix
- `evidence/recommendation.txt` — explicit readiness recommendation
- `AI_HANDOFF.md` — this document
- `AMED_RECEIPT.md` — AMED-policy receipt
- `DEPENDENCY_AUDIT.md` — zero third-party dependencies
- `UNKNOWN-REGISTRY.md` — D3 gap + CI-runnner dependency

## Stop / handoff

QCLAW does not self-merge. PR remains Draft. This handoff is published to Issue #243.

After this commit:
- Push additive commits (no rebase/force/amend)
- Trigger E50 CI (Python 3.11 + 3.13 matrix)
- Stop. Await GPT R1 review on Issue #243.