# E38 Trusted Authority Design

## Trust boundary

`github_transport.py` is the sole module that can create a fetched approval
document or route snapshot. It is fixed to the public canonical repository and
the GitHub API host, uses GET only, carries no credentials, rejects redirects,
media-type changes and oversized responses, and has no generic URL surface.

`proofs.py` has no HTTP client. Its VERIFIED result constructors are internal;
the public result types expose only `unknown` and `rejected` factories. A caller
cannot supply arbitrary bytes or an ordinary comment object and obtain a
VERIFIED result.

## Approval binding

The only accepted body form has exactly one block:

```text
```brainops-approval-v1
{"canary_id":"...","expires_at":"...","nonce":"...","route_epoch":39,"scope":"...","task_id":"..."}
```
```

The compact sorted JSON form, field set, duplicate-key rejection, comment
identity, actor, expiry, nonce and the candidate approval must all agree. The
actor must additionally be listed identically in both active route documents.

## Route proof

The transport reads `refs/heads/main`, the exact commit, the commit tree, both
canonical route paths and each blob. It validates Git blob identity and content
hash, rereads `main`, and rejects drift. The verifier separately parses both
YAML route files and requires task ID, epoch, READY, execution enabled and both
automation flags disabled to match. A missing actor policy is a rejection, not
a default actor selection.

## CI identity

The E38 workflow explicitly checks out
`${{ github.event.pull_request.head.sha }}` and runs `ci_identity.py`, which
compares `git rev-parse HEAD` with that expected exact SHA before tests run.
The historical default merge-ref workflow remains historical evidence only.
