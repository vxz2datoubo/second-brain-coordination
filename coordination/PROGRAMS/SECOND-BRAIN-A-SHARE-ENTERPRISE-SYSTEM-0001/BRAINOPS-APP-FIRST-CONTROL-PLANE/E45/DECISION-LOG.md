# E45 Decision Log

1. `CapabilityWitness` remains a raw compatibility observation, never a positive authority input. This preserves traceability while closing caller construction as a capability escalation path.
2. A verifier-minted `TransportAttestedWitness` is required to consume a durable challenge. Its tuple binds challenge, route tuple, holder, target and the verifier's fixed transport identity.
3. A consumed challenge is still only a preliminary fact. `ClaimBoundCapabilityDecision` binds it to immutable provenance digest, storage id, Claim id and invocation id.
4. `CapabilityDecisionUseLedger` consumes the bound positive decision once globally and repeats the expiry check at use time. A replay is blocked rather than silently re-evaluated.
5. Legacy holder recovery is deliberately non-mutating. The actual governed recovery transition consumes the separately issued grant immediately before its CAS write.
6. A lost response after grant consumption is intentionally unavailable and requires reconciliation. It must not become a successful recovery by inference.

These are synthetic contract decisions. They do not establish a production identity, transport, or GitHub authority root.
