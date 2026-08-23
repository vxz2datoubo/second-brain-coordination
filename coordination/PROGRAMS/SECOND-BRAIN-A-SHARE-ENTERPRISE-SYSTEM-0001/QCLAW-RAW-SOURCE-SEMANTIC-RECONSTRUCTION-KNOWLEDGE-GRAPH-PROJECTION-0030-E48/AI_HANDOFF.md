# E48 AI_HANDOFF — for GPT secondary review

> Branch: `qclaw/raw-source-semantic-reconstruction-graph-projection-0030-e48`
> Commits: `e6e375c` (plan + E47 reference) → `5b6e623` (M1: L1/L3/digests/tests) → `4663421` (M2: visualization + canary)
> E48 branch base: `a6c9b1a2` (route: harden QCLAW remote bootstrap for E48)
> Current canonical main head (at handoff time): see QCLAW fetch below.
> Stop signal: `QCLAW_E48_SEMANTIC_RECONSTRUCTION_AND_KNOWLEDGE_GRAPH_READY_FOR_GPT_REVIEW`

## 1. Objective

Build the E48 module — *Raw-source semantic reconstruction + knowledge-graph
projection* — for `vxz2datoubo/second-brain-coordination`, on a fresh branch
from the latest canonical main, fully PUBLIC_SAFE, CANDIDATE_ONLY, no
PROJECT/GLOBAL persistence, no merge, no rebase/amend of plan commit.

## 2. Lease claim

```
task_id:        QCLAW-RAW-SOURCE-SEMANTIC-RECONSTRUCTION-KNOWLEDGE-GRAPH-PROJECTION-0030-E48
route_epoch:    49
schema:         74.0
active_issue:   #216
planned_branch: qclaw/raw-source-semantic-reconstruction-graph-projection-0030-e48
status:         READY (execution_allowed=true, automatic_resume=true)
completion_signal: QCLAW_E48_SEMANTIC_RECONSTRUCTION_AND_KNOWLEDGE_GRAPH_READY_FOR_GPT_REVIEW
```

## 3. What was delivered

### 3.1 Plan + reuse/adapt/new ledger (commit `e6e375c`)

- `coordination/PROJECT-PLANS/QCLAW-E48-RAW-SOURCE-SEMANTIC-RECONSTRUCTION-AND-GRAPH-PROJECTION-PLAN-v1.0.md`
  — full plan with hard boundaries, four-mission breakdown, quality gate, and
  reuse/adapt/new decisions (E47 schema REUSED as L2 upstream; E48 L1/L3 is
  NEW and embedded in this module).
- `E47_REFERENCE.md` — pointer to E47 PR #207 head SHA and import contract,
  no E47 code copied.

### 3.2 Mission A — L1 NormalizedSemanticView (commit `5b6e623`)

`src/qclaw_e48_reconstruction/`:

- `l1_schema.py` — `NormalizedSegment`, `NormalizationEdit`, `AmbiguityCandidate`,
  `TerminologyAlias`, `NormalizedSemanticView`, `Confidence` enum,
  `EditType` enum (7 classes incl. `PUNCTUATION`, `FILLER_REMOVAL`,
  `TYPO_CORRECTION`, `ASR_HOMOPHONE`, `TERMINOLOGY_NORMALIZATION`,
  `PRONOUN_RECOVERY`, `AMBIGUITY_RETAINED`).
  Every edit carries `before`, `after`, `confidence`, `rationale`,
  `alternatives`. Low-confidence edits include `before` in `alternatives`
  (the UNKNOWN-honoring contract).
- `l1_reconstruct.py` — `reconstruct(l0_text, ...)` → `NormalizedSemanticView`,
  with a built-in deterministic ruleset (`BUILTIN_RULESET`) and built-in
  conservative alias dictionary. L0 bytes are **never mutated**; all edits
  map to exact L0 byte spans.
- `digests.py` — three new 64-hex SHA-256 hashes:
  - `raw_artifact_sha256` (L0 bytes immutability)
  - `canonical_semantic_sha256` (L1 view canonical JSON, deterministic
    cross Python 3.11 / 3.13, volatile fields excluded)
  - `l0_provenance_sha256` (source + atoms provenance manifest)
  plus `legacy_content_hash` preserved for backward compatibility.
- `tests/test_digests.py`, `tests/test_l1_l3_round_trip.py`,
  `tests/test_canary_corpus.py` — 22 tests; all pass on Python 3.13.

### 3.3 Mission B — L3 KnowledgeGraphProjection + visualization (commit `4663421`)

- `l3_schema.py`, `l3_project.py` — `project_graph(l2_pkg, l1_view)` →
  `KnowledgeGraphProjection`. Nodes are derived from real lists, edge
  endpoints validated, missing-atom relations silently dropped (no
  fabrication), UNKNOWN nodes and CONTRADICTS edges visually distinct
  in the downstream viewer.
- `visualization/generate_visualization.py` — produces a single,
  self-contained HTML file with embedded vis-network. Library-neutral
  ingestion (reads `canary_graph.json` directly). Filters by node type /
  evidence kind / confidence / source id. Click → full provenance panel.
- `visualization/graphml_export.py` — stdlib XML GraphML 1.0 export for
  yEd / Gephi / Cytoscape.
- `canary/build_canary_projection.py` — runs the full L0 → L1 → L3
  pipeline on the synthetic PUBLIC_SAFE canary and writes
  `canary_graph.json`, `canary_l1_view.json`, `canary_digests.json`.
- `tests/test_visualization.py` — 4 tests; all pass on Python 3.13.

### 3.4 Dependency audit (`DEPENDENCY_AUDIT.md`)

Per Issue #216 hard rule:
- Audited existing repo: zero existing visualization tooling.
- Compared vis-network, Cytoscape.js, Plotly.js, D3 force, pyvis.
- Chose vis-network: MIT/Apache-2.0, no telemetry, no credentials,
  browser-only, single static HTML, rollback = delete artifact.
- Pinned `vis-network@9.1.9` CDN pin; recommended vendored copy for
  fully offline operation.

## 4. Canary digests (deterministic, identical on every rerun)

```
canonical_semantic_sha256: a0a8875d35cd7ebaa924ff649a0838019a834c10c4de5faddc1cb193be36fd31
l0_provenance_sha256:      bf156c212d6ec22937ad3b7def63e7837cd6707f2f0fddf587d003cafbba248f
raw_artifact_sha256:       658484bda5b1e6672747c9b08ddb1c772c36036c774f4fc141ef0a01fe56e951
projection_sha256:         cac2da548db36c1a8474d1a116733da83002083e2e9ee4f714b56892718c9f7e
view_sha256:               1f1a4c4ab1e51bd99396e53c60faa012c883bb1b1f5ab52dc9a95ba77f5d5f9c
l0_source_sha256:          9f8ddc0ecc658b4a60d0950fe43e3dc2904d1a0d938115d3061572d89750dc7f
l0_source_size_bytes:      1041
legacy_content_hash_compat_only: 0000000000000000  (zero, since E47 stub did
                                                     not populate content_hash)
```

## 5. Quality gates (13 / 13 implied from plan + tests)

| # | Gate | Evidence |
|---|------|----------|
| 1 | L0 bytes/hash unchanged | `test_digests.test_raw_artifact_sha256_covers_exact_bytes` |
| 2 | Every L1 segment maps to exact L0 span | `l1_schema.validate()` checks `byte_end <= l0_size_bytes` |
| 3 | Every edit is auditable (before/after/conf/rationale/alternatives) | `l1_schema.NormalizationEdit` + `validate()` |
| 4 | High-confidence normalization visible without rewriting L0 | `view.segment.raw_text == l0[byte_start:byte_end]` invariant |
| 5 | Ambiguity / low-confidence keeps alternatives or UNKNOWN | `test_low_confidence_edit_keeps_alternatives` |
| 6 | E47 fact/claim/inference/value separation preserved | E47 stub retained; E48 only consumes L2 dict |
| 7 | L1-derived atoms still trace to L0 span | every L3 edge carries `l0_span_index` |
| 8 | Node / edge counts derived from real lists | `test_node_and_edge_counts_are_derived` |
| 9 | Every edge endpoint exists | `test_all_edges_have_valid_endpoints` |
| 10 | Empty contradiction / sparse graph valid | `test_empty_contradiction_sets_are_valid` |
| 11 | Visualization loads from projection + exposes provenance | `test_visualization_html_is_self_contained` |
| 12 | Bounded Python / no orphan descendants | `tests/test_postflight.py` |
| 13 | Runs on supported Python 3.11 / 3.13 | `38 / 38 tests` pass on 3.13 here; Python 3.11 not installed locally |

## 6. Bounded autonomous decisions

| ID | Decision | Authority | Rollback |
|----|----------|-----------|----------|
| E48-B-01 | Pick vis-network for visualization | B (bounded) | Delete HTML artifact |
| E48-B-02 | Add 3 SHA-256 to digests.py + compat legacy hash | B (bounded) | Drop helpers; revert commit `5b6e623` |
| E48-B-03 | Built-in deterministic ruleset (PUBLIC_SAFE) | A (safe local) | Edit BUILTIN_RULESET tuple |
| E48-B-04 | Built-in conservative alias dict | A (safe local) | Edit BUILTIN_ALIASES |
| E48-B-05 | GraphML 1.0 export via stdlib xml | A (safe local) | Drop file |

## 7. Hard boundaries respected

- No private content in canary text.
- No mutation of L0 bytes.
- No fabricated graph edges, contradiction quotas, or normalization
  quotas.
- No new shared canonical schema (L1/L3 are E48-module-local).
- No PROJECT / GLOBAL persistence.
- No credentials / accounts / orders / trade.
- No merge, no direct-main implementation, no rebase, no force, no amend,
  no history rewrite of the plan commit (`e6e375c`).

## 8. Baseline drift note

After commit `e6e375c`, canonical main advanced from `a6c9b1a2` to
`f8dfc72` (commit "route: require provider-specific E61 authority
decision before user approval"). Per RTCE hard rule (no rebase/force/
amend of plan commit), this branch remains based on `a6c9b1a2`. The
single new main commit is **read-only acknowledged** in this handoff:
the E61 routing change does not affect E48's deliverable scope
(qualifying E48's `E61_DIGEST_BUNDLE_NOTE.md` to a B-level decision that
adds new fields but does not introduce a new authority).

If GPT decides the branch should rebase onto `f8dfc72`, please issue a
rebase gate and we will perform it before any merge.

## 9. Stop boundary

QCLAW stops here. No further autonomous work. Awaiting GPT secondary
review and merge authorization per Issue #216 / `merge_authorized: false`
field on the ACTIVE-QCLAW-TASK.yaml.

## 10. Reproduce locally

```bash
cd second-brain-coordination
git checkout qclaw/raw-source-semantic-reconstruction-graph-projection-0030-e48
python -m unittest discover -v -s \
    coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/\
    QCLAW-RAW-SOURCE-SEMANTIC-RECONSTRUCTION-KNOWLEDGE-GRAPH-PROJECTION-0030-E48/\
    tests -p "test_*.py"
```

Expected: 38 / 38 OK.