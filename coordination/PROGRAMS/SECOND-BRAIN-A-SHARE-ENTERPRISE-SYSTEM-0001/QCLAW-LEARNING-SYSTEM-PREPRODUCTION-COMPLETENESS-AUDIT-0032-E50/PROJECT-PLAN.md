# E50 — Learning-System Preproduction Completeness Audit + Generalization Hardening

**Project plan mode**: deliverable is this document + project skeleton + reuse/adapt ledger, followed by bounded evaluation harness, then D1–D12 evidence matrix, then explicit readiness recommendation.

**Repository**: `vxz2datoubo/second-brain-coordination`
**Branch**: `qclaw/learning-system-preproduction-completeness-audit-0032-e50` (from exact `origin/main` `d00c1068469433e648f69c926a3b55510dbe8717`)
**Completion signal**: `QCLAW_E50_LEARNING_SYSTEM_PREPRODUCTION_COMPLETENESS_READY_FOR_GPT_REVIEW`
**Recommendation will be exactly one of**: `NOT_READY` / `READY_FOR_BOUNDED_REAL_SOURCE_PILOT` / `READY_FOR_PRODUCTION_CANDIDATE_LEARNING`

## 1. Objective

Independently judge whether the second-brain learning system is **sufficiently complete** to support real/private high-value source learning. Build and run a bounded public-safe generalization/adversarial evaluation across the full learning lifecycle.

**Do not treat E48 canary success as production readiness.** E48 proved a narrow semantic/provenance foundation. E50 audits the complete lifecycle before any real/private source pilot.

## 2. Foundation credit (accepted by GPT, review_id 4915512021)

E48 head `e018fc1a85fccb85eccb7274ba672bbb54dc66db` — accepted for:
- L0 immutable raw evidence
- L1 auditable semantic reconstruction
- Bounded E47-style L2 atomization
- L3 graph projection
- Ambiguity / UNKNOWN fail-closed
- Truthful conditional relation direction (DEPENDS_ON, MECHANISM→CONDITION)

**NOT accepted** (explicit): private/real user samples.

E50 must build on this foundation and audit the dimensions E48 did not cover (cross-source mastering, user cognition, skill promotion, retrieval/reuse/correction, Codex promotion boundary, generalization/adversarial, determinism CI, resource safety).

## 3. Predecessor correction

- E48: `ACCEPTED` (foundation)
- E49 (real-source pilot): `SUPERSEDED_BEFORE_EXECUTION` (issue 242) — "do not equate a passing narrow candidate pipeline with a complete learning system"

E50 must close the gap that triggered the E49 supersession.

## 4. Hard boundaries (must not violate)

- No private/high-value user source ingestion during E50
- No authoritative PROJECT/GLOBAL persistence
- No automatic formal skill/trading-rule promotion
- No fabricated coverage quotas or invented relations (coverage failures are valid findings)
- No merge/rebase/force/amend/history rewrite unless separately authorized
- No secrets / credentials / accounts / trading
- `formal_persistence: BLOCKED`, `merge_authorized: false`, `authoritative write: false`

## 5. Source policy

`PUBLIC_SAFE_GENERALIZATION_ONLY`:
- PUBLIC_SAFE synthetic fixtures
- publicly distributable non-sensitive real-world text fixtures
- sanitized/generated ASR/OCR/chat-style fixtures

Required source classes (≥ 6):
1. clean article / research prose
2. noisy ASR / oral transcript
3. chat / dialogue with speaker roles
4. OCR / typo-heavy text
5. cross-source contradiction / version pair
6. method / skill material containing conditions + failure cases

Plus for adversarial/generalization:
7. prompt-injection style text (treated as content, not instructions)
8. heterogeneous mutation set (reordering, paraphrasing, omission markers)

## 6. Architecture (reuse vs adapt vs new)

### 6.1 Reuse (E48 foundation, vendored as frozen snapshot v1.0)

Copy E48 source modules into `src/qclaw_e48_foundation/` (NOT importing across branches — vendored for reproducibility):
- `digests.py` — 6-digest bundle contract (raw_artifact / canonical_semantic / l0_provenance / l0_source / view / projection)
- `l1_schema.py` — `NormalizedSemanticView` / `NormalizedSegment` / `NormalizationEdit` / `AmbiguityCandidate` / `UnknownMarker`
- `l1_reconstruct.py` — bounded ruleset, fail-closed arbitration, `_is_low_confidence`
- `l2_derive.py` — semantic atom + relation derivation from L1 view (DEPENDS_ON source=MECHANISM, target=CONDITION)
- `l3_project.py` — graph projection with provenance edges
- `l3_schema.py` — `KnowledgeGraphProjection` / `NodeType` / `EdgeType`

**Vendor attribution**: each file carries a header pointing to E48 head SHA + review_id.

### 6.2 Adapt (extend E48 with E50-specific hooks)

- `digests.py` — keep unchanged (still the canonical 6-digest contract)
- `l1_schema.py` — keep schema; allow E50 callers to add `lifecycle_origin` / `source_class` tags without breaking existing fields
- `l2_derive.py` — keep derivation logic; E50 may add **test hooks** for adversarial inputs (e.g., prompt-injection-style content) without changing default behavior

### 6.3 New (E50 audit-only modules under `src/qclaw_e50_audit/`)

| Module | Purpose | D coverage |
|---|---|---|
| `ingestion.py` | multi-source adapter with immutable provenance, source-class tag, private/public boundary enforcement | D1 |
| `cross_source.py` | stable semantic object identity, dedup, near-duplicate, contradiction classes, temporal/version supersession | D4 |
| `cognition.py` | user-origin mapping (verified / inferred candidate / UNKNOWN) | D6 |
| `skill_promotion.py` | receipt-bound candidate→experimental→formal transitions; no caller-authored promotion; rollback hook | D7 |
| `retrieval.py` | canonical W3 query/context path; correction feedback alters later recall; supersession precedence | D8 |
| `codex_boundary.py` | compatible interface for Codex candidate/formal promotion; no formal write | D9 |
| `corpus.py` | public-safe corpus loader + adversarial mutation generator | D2, D10 |
| `audit_runner.py` | orchestrator: D1–D12 evidence matrix, coverage report, postflight | all |
| `recommendation.py` | explicit NOT_READY / READY_FOR_BOUNDED_REAL_SOURCE_PILOT / READY_FOR_PRODUCTION_CANDIDATE_LEARNING | output |

### 6.4 Forbidden (out of scope, must NOT build)

- Any producer / consumer that ingests real/private user transcripts
- Any module that promotes a candidate to formal GLOBAL/PROJECT state without separate authorization
- Any trading-rule generation / order placement / credential handling
- Coverage-fabrication (e.g., padding atoms/relations to look "complete")

## 7. D1–D12 evaluation matrix

Each dimension gets:
- a **bounded evaluation** (no full production; bounded public-safe inputs)
- a **PASS / PARTIAL / FAIL** verdict with explicit evidence pointers
- **coverage report**: correctly extracted / missed / distorted / unsupported atoms-relations
- **postflight check** (zero task-owned descendants / orphans / unrelated terminations)

### D1 — Source ingestion / privacy / provenance

PASS criteria:
- multi-source adapter ingests ≥ 6 source classes (article / ASR / chat / OCR / contradiction pair / method)
- every adapter emits immutable provenance (source URI / class / hash / byte range)
- private/public boundary enforced by tag (no private tag allowed in E50; refusing must close the input)
- absence of source_uri → fail-closed, no silent default

### D2 — Semantic reconstruction across article/ASR/chat/OCR

PASS criteria:
- E48 L1 reconstructor applied to all 4 source classes
- no semantic corruption on clean article (no filler/punctuation split in normal words)
- ambiguity / UNKNOWN preserved
- bounded punctuation only at un-terminated line ends
- ASR homophone correction keeps low-confidence alternatives, not silently applied

### D3 — Broad atom taxonomy + epistemic separation

PASS criteria:
- L2 atoms cover: concept / definition / mechanism / causal_chain / condition / counterexample / indicator / data_source / scope / failure_condition / verification_method / hypothesis / executable_action
- epistemic separation: SOURCE_EXTRACT (byte-exact from L0) vs USER_CLAIM vs EXTERNAL_CLAIM vs INFERENCE vs VALUE_JUDGMENT
- terminology / alias / cross-sentence mechanism / condition covered

### D4 — Cross-source mastering

PASS criteria:
- stable semantic object identity (canonical SHA-256 across reruns + reorderings)
- dedup detects identical / near-identical atoms (configurable threshold)
- contradiction classes: explicit `CONTRADICTS` edge between versioned variants
- temporal / version supersession: later source supersedes earlier with provenance retained
- no silent overwrite (earlier content never destroyed)

### D5 — Evidence verification and gap handling

PASS criteria:
- SOURCE_EXTRACT atom content == exact L0 byte slice (byte-identical invariant)
- evidence_kind classifier deterministic
- evidence-gap explicitly recorded (not silently filled)
- external verification hooks present (URI + verification_method atom) but do not claim verification that hasn't happened

### D6 — Verified user-origin cognition

PASS criteria:
- "verified user-origin" requires explicit marker (e.g., `source_class=USER_DECLARED`) on the source, not inferred from text
- inferred cognition remains `candidate / confidence / UNKNOWN`
- no forgery path: caller cannot mark `verified_user_origin=true` without the source marker

### D7 — Receipt-bound skill learning/promotion + rollback

PASS criteria:
- promotion requires actual test receipts (test name + digest + pass count)
- no caller-authored promotion (`promote_to_formal(skill_id, dry_run=True)` is the only public API; full promotion gated)
- rollback path: each promotion has `rollback_receipt` with reverse digests
- distinct cases + failure conditions recorded

### D8 — Retrieval / reuse / correction round-trip

PASS criteria:
- ingested candidates recalled through canonical W3 query/context path
- corrections (newer / superseding source) alter later recall
- stale/superseded candidates NOT surfaced by default unless explicit `include_superseded=True`

### D9 — Compatibility with Codex candidate/formal promotion boundary

PASS criteria:
- E50 emits the same candidate-package shape Codex expects (digest bundle + manifest)
- no formal write attempted
- promotion gate emits `BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY`

### D10 — Multi-domain adversarial / generalization

PASS criteria:
- heterogeneous public-safe corpus (≥ 8 distinct fixtures)
- omission / distortion / unsupported-claim / relation-direction checks
- prompt-injection style text treated as source content, not instructions
- mutation checks (reordering / paraphrasing / omission markers) keep digests stable for non-semantic changes, change them for semantic ones

### D11 — Determinism + Python 3.11 / 3.13 exact-head CI

PASS criteria:
- all digests deterministic across Python 3.11 and 3.13
- mutation tests confirm: semantic change → digest change; volatile / non-semantic change → digest stable
- exact tested head recorded in evidence matrix

### D12 — Resource safety + rollback

PASS criteria:
- bounded processes (≤ qclaw_task_python_cap=2, combined_cpu_bound_workers_cap=1)
- no nested parallelism
- heavy matrix / fanout → REMOTE_CI_OR_BOUNDED_ONLY
- postflight: zero task-owned descendants / orphans / unrelated terminations
- rollback: failure of any D check → artifacts quarantined, no global state mutated

## 8. Coverage report (mandatory output)

For each corpus input, classify every atom / relation into one of:
- **correctly extracted** — present in expected set with matching span + content
- **missed** — present in expected set but absent from output (with reason)
- **distorted** — present in output but content / span / type differs from expected (with diff)
- **unsupported** — present in output but no evidence in input (flag as candidate, do NOT auto-accept)

## 9. Recommendation rule

- **NOT_READY**: any D returns FAIL OR > 2 return PARTIAL OR D4/D8 returns PARTIAL OR D1/D6/D9/D10 returns FAIL
- **READY_FOR_BOUNDED_REAL_SOURCE_PILOT**: all D1–D12 PASS or PARTIAL, no FAIL; D4/D8 ≥ PARTIAL; recommendation includes bounded source whitelist (e.g., user-approved public-domain articles only)
- **READY_FOR_PRODUCTION_CANDIDATE_LEARNING**: all D1–D12 PASS; D4/D8 PASS; D7 PASS with full receipts; recommendation includes promotion gate requirements

## 10. Schedule (additive commits on E50 branch)

1. `qclaw(E50): plan + foundation vendor + reuse/adapt ledger` — this document + vendor E48 foundation
2. `qclaw(E50): corpus + ingestion + D1/D2 evaluation`
3. `qclaw(E50): cross-source mastering + D4/D5 evaluation`
4. `qclaw(E50): cognition + skill + retrieval + D6/D7/D8 evaluation`
5. `qclaw(E50): codex boundary + generalization + D9/D10 evaluation`
6. `qclaw(E50): determinism CI + resource postflight + D11/D12 evaluation`
7. `qclaw(E50): D1–D12 evidence matrix + explicit readiness recommendation + handoff`

After each commit: run bounded local tests, push additive only.

## 11. Stop / handoff

After handoff commit:
- Publish Issue #243 handoff comment with: D1–D12 matrix + coverage report + recommendation + 6 SHA-256 digests + postflight receipts
- Stop. Do not poll. Await GPT review.