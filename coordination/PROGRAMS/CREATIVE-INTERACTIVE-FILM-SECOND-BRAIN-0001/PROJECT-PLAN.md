# Creative Interactive Film + Second Brain — governed project plan

agent_id: CODEX

This task implements one offline-first and auditable creative vertical chain in the
fixed order published in Issue #490. It is not a migration of local WorkBuddy files,
an external-provider integration, a canonical knowledge store, or a production
deployment.

| Slice | Status | Deliverable | Acceptance focus |
| --- | --- | --- | --- |
| S00 | executor-verified | collaboration, provenance, scope, and handoff controls | exact baseline, scope rejection, source classes |
| S01 | executor-verified | deterministic creative event ledger | append and replay equivalence |
| S02 | pending | local interactive CLI | offline create, act, inspect, replay |
| S03 | pending | director compiler and gates | structured plan plus fail-closed gates |
| S04 | pending | review-only knowledge bridge | no canonical knowledge write |
| S05 | pending | offline/mock adapters | no credential or paid-call path |
| S06 | pending | end-to-end replay and review handoff | positive and negative evidence |

## Frozen decisions

- Implementation branch is rooted at `963acf85f0e38890c8eea8a0469980246ce3f1ce`.
- GPT is GitHub integrator and independent reviewer; Codex cannot self-review,
  self-accept, or self-merge.
- The task uses synthetic public-safe scene fixtures until GPT publishes an auditable
  source import or registration for any outside asset.
- The only executable generation mode is deterministic offline/mock output.
- The knowledge bridge creates review/context packets only; it cannot become a
  canonical knowledge authority.

## Completion gate

All S00–S06 acceptance checks must pass on the exact PR head, with the current
`AI_HANDOFF.yaml`, a Draft PR, and `REVIEW_REQUEST/v1` for Issue #453.
