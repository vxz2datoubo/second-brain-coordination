# E64 practical threat model

## Claim boundary

The mechanism is application/workflow integrity inside the existing GitHub
control plane. It does **not** claim an independent cryptographic trust root,
HSM-level isolation, or protection from a malicious GitHub administrator.

## In scope

- a candidate changes after approval;
- a package uses the wrong complete digest or provenance digest;
- a stale route, repository ID, target, approval, or GPT-review reference;
- replay, concurrent duplicate claim, or two promotions from one approval;
- canonical `main` moving after approval; and
- an attempt to admit non-public user content to this public repository.

## Out of scope

- GitHub platform compromise or malicious administrator actions;
- external-cloud trust roots and repository-visibility migration; and
- any real-user formal knowledge persistence. E64 produces validation evidence
  and a candidate receipt only.

## Control mapping

| Risk | E64 control |
| --- | --- |
| Changed package | canonical identity includes all three typed E48 digests |
| Wrong control plane | exact repository ID/slug, task ID, and route epoch policy match |
| Bad approval | nonempty actor + GPT review refs, exact identity binding, expiry |
| Replay | lock-protected one-time APPROVED → CLAIMED → consumed transition |
| Concurrent main | expected-parent checked again at candidate-promotion time |
| Private content | admission class rejects non-`PUBLIC_SAFE` before registration |

## R1/R2 evidence, cross-run, and acyclic admission correction

R1 treats every caller-provided locator as untrusted. A read-only resolver must
retrieve a canonical GitHub approval-control object and verify its immutable
object hash, repository identity, task/route, exact candidate identity,
`APPROVE` decision, control-object identity, canonical-main commit and expiry.
An upstream admission decision is resolver-verified against an acyclic
pre-admission subject identity. That identity is computed before the admission
evidence reference and hash exist. The evidence object is then deterministically
serialized and hashed; only then may the final candidate include its reference
and hash. It never requires private raw source to be published.

The one-time claim is not an in-process lock. A future writer must atomically
create or advance a durable Git-backed marker only when canonical main is the
expected parent and the immutable marker is absent. E64 models this behind a
shared CAS interface for tests. A completed marker returns the same immutable
receipt idempotently; an unknown outcome must reconcile rather than retrying a
write. No actual GitHub write is part of E64.
