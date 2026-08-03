# E42 Trust Boundary Model

agent_id: `CODEX`

## Trusted chain

```text
fixed read-only route transport
  -> sealed route snapshot
  -> verified route proof
fixed approval comment transport
  -> sealed comment document
  -> verified approval proof
route proof + approval proof
  -> exact authority provenance
fixed GitHub Contents/ref CAS
  -> one durable claim winner
winner + same owner instance/correlation + unexpired provenance
  -> sealed effect permit
bounded callback/process verifier
  -> verified invocation receipt
fixed canonical route reader + durable final state
  -> verified terminalization
```

## Threats and responses

| Threat | Response |
|---|---|
| Caller constructs a supported capability | Raw observation is blocked; only verifier output is accepted. |
| Caller labels the current session as Automation or CLI | Owner/evidence compatibility and disjoint evidence fields reject it. |
| A second owner knows the claim ID | Owner type, instance ID, and correlation must all match. |
| Route commit/blob or approval comment/body is replaced | Stable storage key reaches the original record; exact binding mismatch fails closed. |
| Contents API follows a redirect or drifts path | Redirects and response identity drift are rejected. |
| PUT succeeds but response is lost | Read-only recovery reports unknown; no effect permit is granted. |
| Stale READY route remains published | Durable claim/final state blocks replay. |
| Generic BLOCKED is presented as canonical final | Publication remains pending without exact durable fields and remote identity. |
| Same-process hostile Python imports private factories | Out of scope for process-level API controls; cryptographic isolation is not claimed. |

## Explicitly unverified runtime boundaries

- GitHub credentials, write permission, branch protection, and rate limiting.
- Real App Automation dispatch/callback transport.
- Real Codex CLI process launcher identity.
- Canonical publisher runtime behavior.

All remain `UNKNOWN`; E42 performs no live probe.
