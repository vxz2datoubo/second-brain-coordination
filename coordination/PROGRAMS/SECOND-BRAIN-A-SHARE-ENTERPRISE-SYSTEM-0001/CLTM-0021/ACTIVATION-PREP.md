# CLTM-0021 Activation Preparation

This directory prepares `CONVERSATIONAL-LONG-TERM-MEMORY-0021` for a future ACTIVE Codex route.

## Canonical baseline

- latest main at preparation: `d240f91ce5992036898cb393d69be36159e8b601`
- E66 / PR #230: merged and GPT accepted with nonblocking follow-up
- E66 accepted head: `36595402caca05364a73cbd170e1b914f0c9de5a`
- CLTM activation issue: #231
- design-source blueprint: PR #229

## Why PR #229 is not merged directly

PR #229 was authored from canonical main `75524ef88ff7c3d4a0ecc0e084194fe584ec5ec2`. After E66 merged, it is diverged from main and still contains stale execution-control references from an earlier route epoch. The architecture remains valuable, but its control-plane state must not be treated as current truth.

Therefore PR #229 is retained as a design source. The future Codex activation-prep stage must reconstruct the CLTM blueprint and registration from the latest canonical main rather than mechanically rebasing stale route state.

## Activation-prep objective

Before any Session A-E implementation, Codex must answer:

1. What already exists in W3 and must be reused?
2. Which PR #229 concepts remain valid unchanged?
3. Which parts are stale because E66/E48/current control plane moved?
4. What minimum schema/adapter/runtime extensions are actually required?
5. Which parts remain blocked by formal-write authority, E48 R3, private-data-plane permissions or current ChatGPT integration limits?

## Required audits

- PR #229 blueprint compatibility audit
- canonical W3 runtime audit
- explicit W3 reuse ledger
- current control-plane verification
- privacy/authority boundary audit
- exact Session A-E minimal vertical-slice plan

## Architecture invariants

CLTM is not a sidecar database. It is the conversational/mobile human interface into W3 long-term memory.

Target loop:

`ChatGPT conversation -> ConversationEpisode -> candidate LearningPacket / memory -> existing W3 runtime -> MemoryRouter -> hybrid retrieval -> Memory Trust Gate -> MemoryContextBundle -> ChatGPT -> correction / new episode -> W3`

The raw/historical Episode remains distinct from evolving derived memory. Current and historical queries must behave differently. User corrections must create explicit correction/supersession chains. Projects consume scoped memory rather than owning separate copies of the user's canonical long-term memory.

## Current locked boundaries

- formal `PROJECT/GLOBAL` production knowledge write remains locked
- live E48 producer integration remains blocked pending E48 R3 acceptance
- production GitHub resolver / real marker writer require a future authorized route
- no real private conversation body in public GitHub
- no credential or secret persistence
- no private-repository creation or permission/visibility change without explicit authorization
- no CLTM implementation before activation-prep GPT acceptance

## Preparation completion signal

`CODEX_CLTM_0021_ACTIVATION_PREP_READY_FOR_GPT_REVIEW`
