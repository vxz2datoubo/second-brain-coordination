# Continuous Architecture Synthesis — Interactive Film × AI Director × Second Brain

agent_id: CODEX

## Purpose

This document turns the owner's broad goal into a concrete, inspectable system:
an interactive-film runtime should remain playable; the director should only
see earned story facts; learning should remain a reviewable candidate; and the
owner should be able to understand what is known, assumed, testable, and safely
hidden without reading source code.

It is a design and evidence map, not a production-release approval.

## The system, in one picture

```text
User intent ──> Understanding cards ──> decision / risk boundary
     │                    │                         │
     │                    └── metric anchors ───────┘
     ▼
Player action ──> append-only ledger ──> graph-backed prefix replay
                                             │
                              ┌──────────────┼───────────────┐
                              ▼              ▼               ▼
                        CLI timeline   director input   knowledge candidate
                              │              │               │
                              └──── exact hashes / refs ──────┘
                                             │
                                    clean reproduction
                                             │
                                  concentrated GPT audit
```

## What is now implemented

| Concern | Implementation | Hard invariant | Owner-visible result |
| --- | --- | --- | --- |
| Story authority | `CreativeLedger` plus versioned `StoryGraph` | ledger hash chain and graph patch must both match | `creativectl timeline` lists each true historical state |
| Intermediate truth | prefix replay, not final-state backfill | every entry is reconstructed from `events[:n]` | consequences cannot quietly change in the middle of a route |
| Director boundary | `compile_verified_director` | malformed/forged timeline raises before a brief exists | `creativectl director` reports the source timeline hash |
| Director branch completeness | `creativectl director-coverage --scenario <name>` | every reachable route prefix must compile with its registered scene profile, asset, axis and zero hard findings | GitHub can prove the director at pauses and alternate consequences, not only at terminal demo states |
| Durable handoff | `CreativeSession/v2` migration envelope | legacy source remains byte-identical; envelope must re-verify graph/timeline | `creativectl migrate` is idempotent and never creates a shadow save on failure |
| Post-migration integrity | v2-to-v1 immutable-source verification | source bytes, event records, graph revision and timeline hash must agree | `creativectl verify-v2` is read-only and rejects a changed/missing source |
| Minimal session handoff | `creativectl session-receipt` | receipt is derived only after immutable v2-to-v1 verification and contains no event records or customer material | a second environment can compare exact session identity without receiving a restorable save |
| User understanding | `UnderstandingMap` | explicit boundary, inferred future intent, explainable replay guarantee, opaque hash mechanics, authority, evidence tier and hard anchors all validate | `creativectl understanding` emits the four-layer map with plain-language explanations and visible drift gates |
| Numeric anti-drift | `MetricAnchor` and `DriftAssessment` | hash/ID integrity uses `exact_match`, not an averaged score | an identity mismatch is a failure, not “mostly healthy” |
| Knowledge boundary | review packet bridge plus verified-timeline derivation | candidate never becomes canonical automatically; derived film candidate must reference validated final event, timeline hash, graph revision, final transition and final-state hash | `creativectl knowledge derive` prepares a human-review-only candidate |
| Offline generation evidence | deterministic receipt bound to verified director input | source timeline, graph, final event, shot and fixed metrics must reconstruct exactly | `creativectl generate-offline` records only a simulated URI; `verify-generation` is read-only |
| Offline scenario library | fixed multi-scenario package made of complete exact-head artifacts | all entries must share one head, complete registry, source-bound catalogue identity and the fixed no-network boundary | `experience_library.json` lets the static player switch only among precomputed verified catalogues; `verify_experience_library.py` rebuilds all package bytes |
| Feedback intake | immutable local feedback record plus review-only candidate | rating is integer 0–5; feedback must bind to a verified receipt; no canonical write | `creativectl feedback <receipt> <0-5> <note>` creates a pending candidate only |
| Lifecycle map | read-only workspace audit | every saved receipt and feedback item must still bind to the active verified story | `creativectl audit` reports the whole evidence chain in one JSON map |

The default `legacy_archive` scenario remains losslessly compatible with the
earlier single-scene records. New sessions may opt into `three_scene`; that
route crosses `archive_gate → interior_archive → dawn_courtyard`, records the
scene transition in the same canonical state patch, selects matching synthetic
scene references for the director, and is migrated using its own initial-graph
identity. A v1 record never silently changes graph merely because a newer graph
exists.

## Four information layers

The code and project skill use the following information partition. It answers
the owner's request to include stated knowledge, unstated assumptions, usable
explanations, and necessary-but-opaque engineering safeguards in one map.

| Layer | Example in this program | Allowed action | Presentation |
| --- | --- | --- | --- |
| `explicit_known` | “Do not use paid generation or credentials.” | hard boundary | report as a fixed requirement |
| `implicit_known` | “The owner wants long continuous build windows.” | process default; not a safety authorization | label it as an inference and record why |
| `explainable_unknown` | prefix replay prevents a correct final screen from hiding a bad intermediate state | implement/test when within scope | one paragraph, benefit/cost/risk/choice |
| `opaque_unknown` | exact serializer ordering inside a SHA-256 input | implement and expose output/hash | expose the guard, signal, and stop condition rather than needless internals |

## Numeric contract

Numbers become decision inputs only with a metric contract. The minimum fields
are metric ID, unit, direction, baseline, current value, target, source
reference, measurement time, formula version, and hard/soft gate class.

| Value class | Example | Correct comparison | Failure behavior |
| --- | --- | --- | --- |
| Identity | Git SHA, event hash, timeline hash, transition ID | exact string equality | fail closed |
| Ordered count | event count, finding count | explicit integer threshold | warning or block according to gate |
| Ratio | branch coverage, replay coverage | versioned numerator/denominator and bounded target | no cross-version comparison |
| Duration | a future replay latency measurement | seconds with hardware/input population stated | alert, then diagnose |
| Quality | future shot-continuity score | store sub-measurements and formula revision | do not substitute for a hard content/identity gate |

Composite “health” scores are deliberately not used for safety or provenance.
They can be added for prioritization only after their components and weights are
versioned, independently inspectable, and never allowed to override a hard
gate.

## Department / role handoff map

| Role or domain | Creates | Must not do | Receives |
| --- | --- | --- | --- |
| Product owner | objective, risk/budget/publication decisions | manually reconcile hashes | plain-language cards, option tradeoffs, stop conditions |
| CODEX continuous builder | code, deterministic tests, clean reproduction receipt | self-accept or merge | stated boundaries and active branch |
| GPT independent reviewer | independent evidence assessment and integration decision | write itself into the executor evidence | frozen head/base, commands, source catalog, risks |
| Story runtime | ledger events | infer legal outcomes from free prose | canonical graph transitions |
| Director compiler | brief and shots | consume an unverified state | verified story state and source timeline hash |
| Knowledge bridge | review-only candidate | write canonical knowledge without human review | event/artifact references and correction text |
| CI / clean worktree | reproducibility evidence | make product/authority decisions | exact commit and commands |

## Research-to-implementation decisions

| Research/practice | What it says | Decision here | Deliberate non-decision |
| --- | --- | --- | --- |
| GitHub provenance attestations | build provenance only helps when verified; it is not proof of secure code | exact commit, command, and clean-environment evidence are always recorded | no attestation for frequent source edits; reserve it for a future released artifact |
| Reusable workflows | stable deterministic checks should be reused rather than copied | treat the test matrix as a single contract; later centralize once stable | do not prematurely add CI abstraction while tests are still changing rapidly |
| Temporal agent memory research | append source episodes, preserve temporal provenance, supersede rather than delete | keep ledger authoritative; cards contain references and supersession | do not claim paper benchmark results as project results |
| Long-running agent harness practice | isolated worktrees plus executable validation make agent work legible | use long-lived isolated branch plus milestone clean reproduction | do not turn every save or test into a human/GPT review |
| Interactive state-machine practice | action space and transition semantics must be explicit for reproducibility | graph validates legal action, exact patch, and declared transition ID | no unconstrained model-driven state mutation in the offline runtime |

Source URLs and caution notes are maintained in
[`skills/creative-program-understanding-map/references/evidence-and-drift.md`](../../../skills/creative-program-understanding-map/references/evidence-and-drift.md).

## Verification strategy

### Deterministic (E1)

- same explicit ledger/graph inputs generate the same timeline hash;
- all event hashes are contiguous and valid;
- every action patch equals the canonical graph edge;
- each timeline row equals its independently replayed prefix;
- unknown action, wrong transition ID, and semantically forged patch fail
  closed;
- director compilation runs only after that validation;
- understanding cards reject unknown layers, missing references, impossible
  confidence values, and unsupported blocking evidence.

### Clean reproduction (E2)

At milestones, clone the committed branch into a separate worktree and run the
same standard-library test suite plus the single command
`python tools/verify_creative_runtime.py --expected-head <SHA>`. This checks
that the result
does not depend on this working directory, uncommitted cache, or chat history.
It is still executor-provided reproducibility evidence, not independent
acceptance.

The deterministic demonstration is intentionally a complete local lifecycle,
not an isolated unit: three-scene play → graph-backed timeline → verified
director → simulated offline generation receipt → receipt verification →
source-bound feedback → pending knowledge candidate → v1-to-v2 migration →
v2 binding check → workspace audit. Each identity comparison is exact; the
only variable owner input is the bounded feedback rating/note.

### Independent acceptance (E3)

Only when the owner says `收尾` will the exact branch head, baseline, test
matrix, negative cases, source catalog, visible behavior, known risks, and
rollback method be sent once to GPT for a genuinely separate audit. CODEX will
not mark its own branch ready, accepted, or merged.

## Next implementation frontier

The current branch now has a source-bound offline lifecycle, but remains
intentionally private and small. The next continuous-build tranche should
extend the same contracts across:

1. named local save-slot policy that cannot escape the workspace;
2. multi-route narrative fixtures with more than one safe ending;
3. per-profile cinematic review fixtures that show the human-visible lighting,
   sound and axis contract for every state;
4. a reusable CI workflow once the local verification surface has stabilized;
5. close-out evidence packaging only when the owner directs `收尾`.

All five are compatible with the existing safety boundary: no credentials,
paid generation, public deployment, or canonical knowledge write.
