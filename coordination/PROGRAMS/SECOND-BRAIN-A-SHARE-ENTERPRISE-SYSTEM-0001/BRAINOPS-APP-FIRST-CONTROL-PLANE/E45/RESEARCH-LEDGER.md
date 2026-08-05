# E45 Research Ledger

Mode: `project_plan`; scope: synthetic contracts only.

| Finding | Evidence | Decision | Status |
|---|---|---|---|
| Caller-built `CapabilityWitness` could be consumed | E44 source review and PR #139 review | Keep it as raw observation; require verifier-minted `TransportAttestedWitness` for ledger consumption | fixed in code, pending CI |
| Positive decision lacked Claim and invocation binding | PR #139 review | Add sealed `ClaimBoundCapabilityDecision` with provenance, storage, Claim, invocation, route tuple, holder and target | fixed in code, pending CI |
| Positive decision could be replayed | PR #139 review | Add durable `CapabilityDecisionUseLedger`; each bound decision is globally one-shot and expiry checked at use | fixed in code, pending CI |
| Old recovery path bypassed recovery ledger | PR #139 review | Make legacy recovery non-mutating; require consumed `RecoveryAuthorizationGrant` immediately before governed CAS | fixed in code, pending CI |
| Python seals are not an isolated trust root | source code and task boundary | Document synthetic-only limitation; no production trust claim | retained UNKNOWN |
