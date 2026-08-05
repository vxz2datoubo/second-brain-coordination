# E46 Decision Log

## D-001: One lease, not another optional validator

Accepted. Capability evidence is persisted as state 1 of the same object that
authorizes effect, attaches invocation, attests terminal evidence, and records
terminal commit. A terminal validator cannot accept an unused capability
decision because the legacy validator is no longer a positive path.

## D-002: Claim and lease remain separate records

Accepted with a durable operation journal. The claim remains owner-state
authority inherited from E42-E45; the lease is authorization/evidence
authority. Cross-record uncertainty is explicit and recoverable rather than
hidden behind an in-memory transaction claim.

## D-003: Invocation identity appears only at state 3

Accepted. Capability is evaluated before invocation. `ClaimBoundCapabilityDecision`
now rejects `None`, but E46 lease creation consumes the earlier sealed
`ChallengeCapabilityDecision` and does not invent an invocation ID.

## D-004: Legacy positive methods fail closed

Accepted. Keeping positive compatibility would preserve the exact bypass E46
was assigned to remove. Historical tests now use explicit test-only fixture
seeding only where they test downstream classifiers, while authority tests
assert the old methods are blocked.

## D-005: Verifier identity is modeled, not claimed as production trust

Accepted. Direct constructors are sealed and tests prove copied caller strings
cannot cross the API boundary. The architecture explicitly records that Python
seals and synthetic factories are not a production trust root.

## D-006: Response-loss recovery covers both durable writes

Accepted as an unplanned B-level hardening. E46 separately proves recovery when
the claim terminal CAS response is lost and when the lease terminal-commit CAS
response is lost.
