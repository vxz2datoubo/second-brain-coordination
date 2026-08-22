# QCLAW-E48 Raw-source semantic reconstruction + knowledge-graph projection — PROJECT PLAN v1.0

> **Status:** plan-first delivery for `mode: project_plan`
> **Source task:** `coordination/ACTIVE-QCLAW-TASK.yaml` (schema 74, route_epoch 49, status READY, execution_allowed true)
> **Predecessor evidence:** E47 PR #207, head `476d2a287cffb084c01b54c1d5e5eaf22016aac7`, semantic canary `ce4a259faf5e0b8fd5a6f6a498fe92b62f398c04`, content hash `379ccafdf592ac75`
> **Branch:** `qclaw/raw-source-semantic-reconstruction-graph-projection-0030-e48` (forked from canonical main `a6c9b1a22086120576b309c610dfd93d98edbb8a`)
> **Completion signal:** `QCLAW_E48_SEMANTIC_RECONSTRUCTION_AND_KNOWLEDGE_GRAPH_READY_FOR_GPT_REVIEW`
> **Boundary:** `CANDIDATE_ONLY / PUBLIC_SAFE / NO_TRADE / NO_MERGE / NO_FORMAL_PERSISTENCE`

---

## 0. Scope statement

This project adds two derived projections to the existing W3 knowledge chain:

- **L1 NormalizedSemanticView** between L0 RawSourceSnapshot and the E47 L2 CandidateKnowledgeAtoms layer.
- **L3 KnowledgeGraphProjection** on top of the E47 L2 atoms, plus a first locally-viewable force-directed / neuron-like graph visualization.

Both layers are derived, audited, and reproducible. They must never replace or rewrite L0; they must never substitute for W3 formal records (which remain under Codex E61 + `GPT_ACCEPTED_REAL_PRODUCTION_DURABLE_AUTHORITY_BINDING` gate).

This project does **not**:

- ingest any private user text into the public repo (canary fixtures are synthetic PUBLIC_SAFE),
- invent graph edges, contradictions or normalization corrections,
- merge, push to main, or change repo permissions / protections,
- introduce a second authority for knowledge,
- run a destructive migration or formal GLOBAL/PROJECT write.

## 1. Architecture summary

```
L0 RawSourceSnapshot (immutable, hash-pinned)  ←──────────── from user / GPT / Codex
            │  byte-stable, hash-stable, no mutation
            ▼
L1 NormalizedSemanticView (derived, auditable) ←─ THIS PROJECT: schema + reconstructor
   - NormalizedSegment           (per corrected span)
   - NormalizationEdit[]         (every change audited)
   - AmbiguityCandidate[]        (low-confidence kept as alternatives, NOT silently chosen)
   - TerminologyAlias[]          (controlled vocab)
   - explicit UNKNOWN for unsolvable pronouns / homophones
            │
            ▼  E47 reuse: CandidateKnowledgeAtoms + relations (UNCHANGED)
L2 CandidateKnowledgeAtoms (E47 PR #207) — reuse, do not regenerate
            │
            ▼
L3 KnowledgeGraphProjection (derived, deterministic) ←─ THIS PROJECT: schema + exporter + first viz
   - node / edge types from E47 + provenance
   - library-neutral JSON exporter
   - GraphML exporter (interoperable)
   - local force-directed / neuron-like viz (audited external dep OR stdlib)
```

## 2. Reuse / Adapt / New ledger

For each candidate capability, decision + reason + safety check + verification.

| # | Capability | Decision | Reason | E47 reuse / external dep / stdlib | Verification |
|---|------------|----------|--------|-----------------------------------|--------------|
| R1 | E47 CandidateKnowledgePackage (L2 atoms) | **REUSE** | E47 PR #207 already accepted as the upstream of L2; semantic_regression_forbidden = true | E47 module: `coordination-canonical/.../candidate_knowledge.py` (will read after checkout) | Re-run E47 tests unchanged + new E48 tests must not break E47 properties |
| R2 | E47 fact / claim / inference / value separation | **REUSE** | Quality gate 6 requires E47 separation to still pass; we add L1, never flatten L2 | E47 | New test that E47 package produced from L1 + raw still passes E47 separation |
| R3 | E47 evidence object (`kind`, `source`, `span`) | **REUSE + ADAPT** | L1 needs to attach edits back to **exact** L0 spans; we adapt the evidence object with `kind ∈ {raw_span, normalized_segment, normalization_edit, ambiguity, alias}` | E47 | New tests |
| R4 | ACTIVE-QCLAW-TASK route contract / remote recovery protocol | **REUSE** | Already running and required by `remote_control_plane_recovery` block | governance | Recovery packet published; canonical main SHA verified |
| R5 | AMED receipts (AgentExecution / Research / Unplanned / Discovery / WPDCR) | **REUSE** | Required by AMED enterprise policy for STRATEGIC tasks | governance | Issue #216 comments + final PR body |
| R6 | W3 blueprint four-layer chain (L0→L1→L2→L3) | **REUSE** | Blueprint is the canonical architecture | blueprints | Plan sections map 1:1 |
| N1 | `NormalizedSemanticView` schema | **NEW** | E47 has no L1; blueprint requires it | none (pure Python dataclasses + JSON schema draft) | Tests + audit-trail example |
| N2 | `NormalizedSegment`, `NormalizationEdit`, `AmbiguityCandidate`, `TerminologyAlias` | **NEW** | Required L1 building blocks | none | Tests |
| N3 | Reconstruction pipeline (deterministic, hash-pinned) | **NEW** | Implements L0→L1 | none (no ML) | Deterministic rerun test |
| N4 | PUBLIC_SAFE synthetic noisy Chinese fixtures (canary) | **NEW** | Required by Mission body | none | Manual review + tests |
| N5 | `KnowledgeGraphProjection` schema + library-neutral JSON exporter | **NEW** | L3 derived projection | none (stdlib only) | Edge/endpoint validation |
| N6 | GraphML exporter | **NEW** (optional, low cost) | Interop with yEd / Gephi / Cytoscape | stdlib `xml.etree` | XML round-trip test |
| N7 | First locally-viewable force-directed / neuron-like visualization | **ADAPT candidate choice** | We MUST audit repo for existing viz, then choose. Reuse > low-maintenance > no-telemetry | Decision deferred until audit complete (see §4) | Doc + dependency audit |
| N8 | UNKNOWN registry | **NEW** | Honest gap log | none | Tests + report |
| N9 | Resource policy FOREGROUND_PRIORITY enforcer | **NEW** | Bounded Python/CPU policy must be testable | stdlib `psutil` only if available; otherwise stdlib only | Tests + postflight |

External dependencies are admitted only after the audit in §4, and must satisfy: (a) no hidden telemetry, (b) no credential, (c) reversibly installable.

## 3. Mission A — Provenance-preserving semantic reconstruction (L0 → L1)

### 3.1 L0 RawSourceSnapshot (input contract, no mutation)

A snapshot is `{id, text, source_meta, raw_bytes_hash, raw_text_hash, captured_at}`. We MUST:

- never mutate it,
- capture `raw_text_hash = sha256(text_utf8)` at intake,
- re-hash after any operation; mismatch → abort with `L0_INVARIANCE_BROKEN` and no L1 produced.

### 3.2 L1 NormalizedSemanticView (derived)

A view contains:

- `view_id`, `view_schema_version`, `view_hash` (separate from L0 hash),
- `segments: list[NormalizedSegment]`, each with `{segment_id, start_offset, end_offset, normalized_text, raw_text_slice, confidence, edits: list[NormalizationEdit]}`,
- `ambiguities: list[AmbiguityCandidate]`,
- `aliases: list[TerminologyAlias]`,
- `unknowns: list[UnknownMarker]`.

`view_hash` is computed over canonical JSON of the view (sorted keys, no raw embedding). It MUST be reproducible.

### 3.3 Edit types (`NormalizationEdit.edit_type`)

`punctuation`, `sentence_break`, `filler_removal`, `typo_correction`, `asr_homophone_correction`, `terminology_normalization`, `alias_remap`, `reference_recovery`, `paragraph_split`, `ambiguity_alternative`, `unknown_marker`.

Each edit has: `edit_id`, `edit_type`, `before`, `after`, `alternatives`, `confidence ∈ [0,1]`, `rationale`, `evidence_refs`.

### 3.4 Hard rules

- L0 bytes & hash never change.
- Every `NormalizedSegment` carries exact `start_offset`/`end_offset` over L0 `text`.
- No silent semantic invention: if `confidence < 0.7` for a typo/ASR edit, the original MUST remain in `alternatives` and MUST NOT become a L2 atom fact unless an explicit confidence threshold + audit evidence.
- ASR homophone corrections MUST carry `alternatives` when confidence is below `ASR_HIGH_CONFIDENCE = 0.9`.
- Explicit `UNKNOWN` for unresolved pronouns / homophones / structure.

### 3.5 Reconstruction pipeline

A pure deterministic function:

```
reconstruct(snapshot, ruleset, options) -> NormalizedSemanticView
```

Inputs frozen. Output deterministic. `view_hash` must match across reruns byte-for-byte (canonical JSON, sorted keys).

## 4. Mission B — Knowledge graph projection (L2 → L3) + first visualization

### 4.1 L3 projection (derived, deterministic)

Node types (minimum): `source`, `document`, `normalized_segment`, `knowledge_atom`, `unknown`, `candidate_memory`, `candidate_skill` (memory/skill only when evidence supports).

Edge types (minimum): `SUPPORTS`, `DEPENDS_ON`, `REFINES`, `CONTRADICTS`, `RAISES_UNKNOWN`, `VERIFIED_BY` (from E47), plus provenance edges: `atom→segment`, `segment→raw_span`, `raw_span→source`.

Node and edge counts derived from the actual E47 package + L1 view; never hard-coded.

### 4.2 Library-neutral exporter (required)

JSON exporter: nodes/edges arrays, each entry with `{id, type, attributes}` and `{source, target, type, attributes, confidence}`. Every edge endpoint MUST exist in `nodes`.

### 4.3 GraphML exporter (optional, low cost)

Use stdlib `xml.etree.ElementTree`. Decide Go/NoGo after the dependency audit in §4.4.

### 4.4 Visualization dependency audit (must precede choice)

Before any external dep is admitted:

1. Inventory existing repo for any graph UI / D3 / vis-network / Cytoscape / PyVis / networkx_drawing / streamlit graph / plotly graph code. If any exists, REUSE.
2. If not, choose **between at least two** candidates. For each:
   - read official docs (NOT random blogs) for: telemetry, transitive deps, license, install size, ability to render purely locally,
   - confirm: no credential, no telemetry, no mandatory cloud,
   - confirm: rollback is one `pip uninstall`.
3. Document the comparison and rationale in `coordination/RESULTS/QCLAW-E48-viz-dep-audit.md`.
4. If both candidates fail, fall back to a stdlib HTML+SVG force layout (small Python simulator) — this is the lowest-cost, fully auditable option and is acceptable as the "first" viz.

The visualization MUST:

- load nodes/edges from the projection JSON,
- support filter by atom type, relation type, evidence kind, confidence, source,
- on click: show content + confidence + evidence + source + raw + normalized context,
- visually distinguish `UNKNOWN` and `CONTRADICTS` (color/shape).

## 5. Canary / validation corpus (PUBLIC_SAFE)

Required fixtures (synthetic, no real user content):

- (a) filler words and repetitions,
- (b) missing punctuation,
- (c) one obvious typo,
- (d) one high-confidence ASR homophone correction,
- (e) one mid-confidence correction with `alternatives` retained,
- (f) one UNKNOWN pronoun / homophone we refuse to resolve,
- (g) one terminology alias,
- (h) at least one cross-sentence mechanism / conditional relation.

Fixtures live under `coordination-canonical/tests/fixtures/e48_canary/*.txt` + a paired expected-normalized JSON. They MUST NOT contain real private text. A `.gitignore` or filename prefix confirms `synthetic_canary`.

## 6. Quality gates (13)

1. L0 bytes & hash unchanged after any pipeline run.
2. Every L1 segment has valid exact L0 span (`start_offset < end_offset ≤ len(text)`, slice equals `raw_text_slice`).
3. Every edit is auditable (`before`, `after`, `confidence`, `rationale`, `alternatives`).
4. High-confidence edits may normalize display text but never rewrite original evidence.
5. Ambiguous corrections keep `alternatives` or UNKNOWN; no silent guesses.
6. E47 fact / claim / inference / value separation still passes after L1 + L2.
7. Atoms derived from L1 still trace back to L0 span.
8. L3 node/edge counts derived from real package lists (no fixed quotas).
9. Every L3 edge endpoint exists.
10. Empty contradiction sets and sparse graphs are valid (no crash).
11. Visualization exposes provenance of any selected node.
12. Resource policy stays bounded: ≤2 QCLAW Python processes, ≤4 combined, ≤1 CPU-bound worker combined, no nested parallelism, zero task-owned descendants / orphans at postflight.
13. Tests run on supported Python 3.11 and 3.13 (where installed). Python 3.12 is also acceptable.

## 7. Anti-Goodhart / anti-hallucination

- No minimum quota for corrections / contradictions / relation diversity / UNKNOWN / memory / skill.
- No guessing for unsure semantic edits.
- No cosmetic graph edges for "niceness".
- Confidence reflects evidence, not output completeness.
- Author / blogger claims stay external claims unless independently verified.
- L1 must NEVER promote a low-confidence ASR correction into a L2 fact silently.

## 8. Resource policy enforcement

- Cap QCLAW Python processes at 2 (combined cap 4 if Codex is active).
- No nested process pools, no multiprocessing for CPU-bound work that would exceed 1 worker combined.
- Never kill by executable name.
- Heavy matrix / dep fanout goes to remote CI or is bounded.
- Postflight: zero task-owned descendants / orphans; tracked by a `postflight_check.py` script.

## 9. Hard boundaries (verbatim)

- No private user transcript / content committed to public repo.
- No raw-source rewrite or silent correction.
- No fabricated graph edges / contradiction quotas / normalization quotas.
- No second knowledge authority competing with W3.
- No formal GLOBAL/PROJECT persistence before Codex E61 + `GPT_ACCEPTED_REAL_PRODUCTION_DURABLE_AUTHORITY_BINDING` gate.
- No credential / account / order / trade.
- No merge / direct-main implementation / rebase / force / amend / history rewrite.

## 10. Stop / approval boundaries (QCLAW must NOT self-approve)

Stop and report rather than proceed if the implementation requires:

- publishing private user data,
- new cloud services / accounts / secrets / tokens,
- new system of record or authority change,
- deletion / migration of existing formal knowledge,
- repo permission / protection changes,
- formal skill promotion,
- formal GLOBAL/PROJECT persistence.

## 11. Deliverables

- This plan (this file).
- Reuse / Adapt / New ledger (this file §2 + final PR body).
- L1 schema + reconstruction implementation.
- PUBLIC_SAFE canary fixtures + expected outputs.
- L1 audit-trail example output.
- L3 graph projection schema + exporter (JSON + optional GraphML).
- First locally-viewable visualization artifact.
- Tests + deterministic verification receipts (Pytest, JSON diff, hash equality).
- UNKNOWN registry file.
- AMED / WPDCR / discovery / handoff receipts.
- Exact list of changed files, commits, commands, failures and rollbacks.

## 12. Milestones (plan-first execution)

| M | When | Output | Status |
|---|------|--------|--------|
| M0 | now | Recovery packet + plan + reuse ledger (this file) | DONE |
| M1 | soon | L1 schema + reconstruction skeleton + unit tests + canary fixtures | TODO |
| M2 | soon | L1 audit-trail example + E47 regression test (L1+L2 still passes E47 separation) | TODO |
| M3 | soon | L3 schema + JSON exporter + node/edge endpoint validation tests | TODO |
| M4 | soon | Visualization dependency audit + viz choice memo + first viz artifact | TODO |
| M5 | soon | Optional GraphML exporter + interop test | TODO |
| M6 | soon | UNKNOWN registry + AMED/WPDCR receipts + postflight_check | TODO |
| M7 | soon | Full test run + deterministic verification + handoff PR description | TODO |
| M8 | end | Completion signal + stop for GPT audit (no merge, no formal persistence) | TODO |

## 13. Open questions / unknowns (to fill as we go)

- Best E47 reuse vs adapt path (resolved when we read E47 module surface in M1).
- Best low-cost visualization (resolved in M4 audit).
- Upper bound on pronoun-recovery determinism (UNKNOWN will be measured empirically).
- Whether GraphML adds value over the library-neutral JSON exporter (decision after M5 dry-run).
- Whether any existing repo path already implements force-directed rendering we can reuse (audit first).

## 14. Safety / privacy checklist (must hold at M7)

- [ ] No private user text in any committed file.
- [ ] Canary fixtures synthetic and marked `synthetic_canary`.
- [ ] No secret / token / credential / account / order / trade committed.
- [ ] No raw-source rewrite of any user fixture (only synthetic canary L0 inputs).
- [ ] Resource policy enforced, postflight zero orphans.
- [ ] No merge, no force-push, no rebase, no amend, no direct main write.
- [ ] No formal GLOBAL/PROJECT persistence written.
- [ ] No new system of record or authority change.

## 15. Reporting

- All AMED / WPDCR receipts, discoveries, UNKNOWN, handoffs and acceptance checkpoints go into:
  - Issue #216 comment thread (PUBLIC_SAFE), and
  - the future E48 PR body.
- I will stop at M7 → M8 completion_signal and explicitly hand off to GPT for the 9-gate second audit. No self-acceptance.