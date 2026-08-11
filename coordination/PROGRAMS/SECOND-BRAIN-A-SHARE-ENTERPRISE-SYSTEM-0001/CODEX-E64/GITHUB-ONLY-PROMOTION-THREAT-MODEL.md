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

The later GitHub writer, if authorized by a future route, must use an atomic
expected-parent update and independently compare the receipt identity. It is
not part of E64.
