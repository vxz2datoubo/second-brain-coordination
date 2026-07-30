# Decision Log

## D-001: Do not import the raw capture

**Decision:** Store only hashes, size, line count, links, and a mechanism
disposition matrix.

**Reason:** Authenticity and license are unknown. Reproduction is unnecessary
for the project outcome.

## D-002: Integrate under PEOS 0010

**Decision:** Treat this as a runtime protocol, not a new cognitive operating
system.

**Reason:** W3, W8, W10, and Phase 3 already own memory, capabilities, task
context, and learning.

## D-003: Preserve eight provenance lanes

**Decision:** Separate user assertion, user adoption, tool observation,
inference, hypothesis, decision, outcome, and unknown.

**Reason:** A learning system must support inference without disguising it as
user memory or observed fact.

## D-004: Keep project integrity, exclude vendor worldview

**Decision:** Exclude vendor promotion, commercial preference, proprietary
identity, and normative consumer persona from the common kernel. Retain
evidence truthfulness, authority, rollback, auditability, idempotency, and
credential isolation.

**Reason:** The former are vendor policy choices; the latter are required for a
correct multi-agent engineering system.

## D-005: Route by capability, not brand

**Decision:** Rank providers using semantic fit, evidence quality, freshness,
reliability, latency, quota, cost, and side effects. The display name cannot
affect score or hash.

**Reason:** Brand preference creates lock-in and weakens evidence quality.

## D-006: Candidate-only memory proposals

**Decision:** The kernel can create `MemoryWriteProposal` with
`authority_write=false` and cannot promote itself.

**Reason:** Canonical memory remains owned by W3 and Phase 3 governance.

## D-007: Separate model profile from authority

**Decision:** Model-specific behavior belongs in `ModelBehaviorProfile`, whose
`authority_overrides` must be empty.

**Reason:** Model quirks should be replaceable without changing project facts or
permissions.

## D-008: Keep the official active route isolated

**Decision:** Implement on a separate user-authorized candidate branch and do
not modify the E24 branch or PR #106.

**Reason:** The user authorized completion before GPT review, but existing
official work must remain untouched.

## D-009: Replace precedence ranking with a layered authority model

**Decision:** Treat hard restrictions as cumulative denials, W1 as the active
lease owner, and user instructions as objective/narrowing/approval input that
cannot expand the lease without a W1 route bridge.

**Reason:** A highest-rank model could silently let natural language, a tool,
or a model profile select authority it does not own.

## D-010: Make approval executable only after W1 verification

**Decision:** Preserve approval requirements separately from allowed actions;
only verified approval actions supplied by the active W1 route make the action
executable.

**Reason:** An allowed action is not the same as an approved action.

## D-011: Require clean-archive evidence

**Decision:** Add an independent CI verifier that runs the complete suite,
schema instances, static gates, all changed-file scans, and three archive roots
under different hash seeds.

**Reason:** A normal worktree can hide dependencies on `.git`, local files, or
non-deterministic process state.
