# E38 Research Ledger

## Scope and source class

This is an L1 repository and protocol review. Sources were the active route,
Issue #116, PR #115 review disposition, imported source and deterministic tests.
No market, broker, account, credential, private session or external research
source was used.

## Result

The accepted E37 atomic nonce work could be reused, but the trust root could
not: public VERIFIED factories, caller-provided comment bytes and caller-
provided blob bytes made a green local result insufficient. E38 replaces only
that boundary and preserves the accepted transaction behavior.

## Counterevidence retained

The current active route has no non-empty actor policy. The new public GitHub
reader fetches it successfully but returns
`route_authorized_actor_policy_missing`; this is evidence of correct failure
closure, not approval or canary readiness.
