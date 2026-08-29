# Realtime Interactive Film Game 0002 — Project Plan

agent_id: CODEX

## Goal

Extend the canonical offline creative runtime into a deterministic, synthetic
multi-scene interactive-film game. This task never reads credentials, calls a
network/provider, deploys a service, promotes canonical knowledge, or imports
local/WorkBuddy/Eustia material.

## Fixed delivery order

| Slice | Status | Deliverable | Acceptance boundary |
| --- | --- | --- | --- |
| S07 | executor_verified_only (checkpoint `62fb0a4`) | Manifest-driven three-scene graph, v2 save slots, explicit v1 migration, transcript and branch comparison | Deterministic, root-confined, corrupt/incompatible saves fail closed |
| S08 | in_progress | Accessible terminal presentation and deterministic logical pacing | No model/network execution path |
| S09 | planned | Multi-beat director packets and continuity diagnostics | Diagnostics do not alter story authority or generate media |
| S10 | planned | Offline demo fixtures, golden snapshots, review packet | Fresh-clone reproduction |

## S07 design decisions

- One `SceneGraph` indexes a `SceneManifest/v1`; it does not create a second
  ledger or story authority.
- Each action has stable scene, beat, action and transition identities. A
  declared target is checked against the resulting state.
- New sessions use `CreativeSession/v2`, bind to the manifest SHA-256, and are
  persisted only beneath the user-selected workspace `saves/` directory.
- `CreativeSession/v1` is upgraded only through the registered, auditable
  `CreativeSession/v1->v2` migration. A legacy record whose replay state cannot
  be represented by the manifest is rejected rather than guessed.
- The graph fixture is newly authored synthetic adult/non-explicit text; it is
  not a reuse of Eustia, WorkBuddy, or unregistered external material.

## Next slice

S08 begins only after this checkpoint is pushed and the handoff records the
exact commit and test receipt. It will add a human-friendly terminal loop on
top of the existing JSON command API, not a network UI or model interpreter.
