# E22-E25 System Discovery And Opportunity Report

## Retained E22 Discovery

E22 found that the workflow originally did not execute Evaluation V2. E23
added the focused runner, and E25 CI run `30577091133` is a successful current
confirmation.

## Retained E24 Negative Discovery

E24 used boolean inversion rather than a real violating artifact and partially
reran/reconstructed trace inputs. These are historical negative evidence, not
silent passes.

## E25 Discovery

Windows PowerShell corrupted a binary `git archive` tar stream. A ZIP retry
plus focused-suite capture exceeded the bounded timeout. This environment issue
does not invalidate the tested commit, but fresh E25 archive evidence remains
`NOT_ACCEPTED`.

## Non-claim

Synthetic evidence does not prove market behavior, identity, profitability, or
production readiness.

## E27 Discovery

GitHub pull-request events may assign `GITHUB_SHA` to a temporary merge
commit. The first green remote run therefore did not prove archive behavior for
`b45ab1...`; an exact branch `workflow_dispatch` was required and passed.
This is a reusable provenance rule: CI green status alone is insufficient when
the evidence carrier requires a particular commit object.

The current canonical repository identity is verified. The earlier E24 view is
best explained by local tracking-ref freshness lag, but that diagnosis remains
an inference rather than an infrastructure fact.
