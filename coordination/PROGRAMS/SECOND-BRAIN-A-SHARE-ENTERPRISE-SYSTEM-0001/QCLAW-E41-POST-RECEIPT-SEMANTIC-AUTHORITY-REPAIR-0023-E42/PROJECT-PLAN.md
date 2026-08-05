# E42 PROJECT-PLAN — Semantic Authority Repair

## Epoch 42: Clean Successor to E41

**Source**: E41 (PR #176, frozen at 24eed791)
**Base**: main 7d11c596
**Branch**: qclaw/e41-post-receipt-semantic-authority-repair-0023-e42
**Completion Signal**: QCLAW_E42_SEMANTIC_AUTHORITY_TRACEABILITY_EVALUATOR_PROVIDER_CLOSURE_READY_FOR_GPT_REVIEW

## Architecture

All 13 E41 blockers addressed through deep-immutable evaluator-derived authority:

### Q1: Deep-Immutable Semantic Authority
- Atom created only via AtomFactory with verified source evidence
- Confidence, verification_state, evidence_layer derived from evidence records
- Atom identity = sha256(full canonical payload, domain-separated)
- All nested collections deep-frozen; snapshots returned, never aliases

### Q2: Exact Source Traceability
- Immutable SourceDocument(bytes, length, digest)
- SourceSpan verified against legal document offsets
- No strip/reconstruction; whitespace/separators retained as STRUCTURE
- Terminology mappings are versioned rule sets

### Q3: Master Records & Contradictions
- Semantic object identity ≠ content hash; stable across versions
- One master with immutable chronological version history
- Every transition requires exact previous/current identity + evidence
- Conflict classification evidence-based; default UNRESOLVED
- Silent overwrite rejected on EVERY transition

### Q4: Evidence-Derived Cognition
- CognitionEntry created via CognitionEngine from evidence records
- Explicit user fact requires user-origin evidence
- Memory destination evaluator-derived, cross-checked

### Q5: Evidence-Bound Skill Lifecycle
- Transitions controlled, recorded in immutable history
- Gates derived from test receipts, case IDs, counterexamples
- Direct FORMAL construction rejected; candidate→experimental→formal only via evaluator

### Q6: Schema-Consistent Corpus & End-to-End Evaluator
- All expected types in AtomType enum
- Corpus identity includes full ground truth in digest
- Run full pipeline on every case; compare canonical outcomes to ground truth

### Q7: Real Copied-Production Mutations
- Copy production code → anchored replacement → run evaluator → nonzero fail → restore → rerun green
- 14 mutation families covering all authority surfaces

### Q8: Exact-Head Provider CI
- Workflow: qclaw-e42-semantic-authority-evaluation.yml
- 6 matrix jobs (3.11/3.13 × seeds 0/1/777)
- Each: full tests + mutations + corpus evaluator
- Canonical evaluation artifact per job + separate environment evidence
- Compare job: byte-for-byte 6-artifact comparison

### Q9: Independent-Review-Grade Report
- Exact heads/parents/trees, all commands/exits/hashes
- Every corpus result, mutation anchor/restoration
- Provider run/job/artifact identities

## Phase Order
Q0(SETUP) → Q1(ATOM) → Q2(SOURCE) → Q3(MASTER) → Q4(COGNITION) → Q5(SKILL) → Q6(CORPUS) → Q7(MUTATIONS) → Q8(PROVIDER) → Q9(REPORT+RECEIPT)

## Hard Bounds
- Synthetic/public-safe only; no real secrets/credentials
- E41 frozen/read-only; E54/Codex parallel untouched
- No merge/main write/rebase/force-push/config/private-access/trade
