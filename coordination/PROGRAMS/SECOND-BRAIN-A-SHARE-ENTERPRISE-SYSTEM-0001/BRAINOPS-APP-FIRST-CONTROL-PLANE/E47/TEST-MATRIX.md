# E47 Test Matrix

## Local command

```text
PYTHONPATH=coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -p "test_e*.py" -v
```

The exact tested-head result is recorded only after the substantive commit and
its 3.11/3.13 exact-head CI matrix. This implementation-stage document does not
claim that later external CI evidence already exists.

## Coverage groups

| Group | Required result |
|---|---|
| Effect authorization | Post-apply response loss, restart, exact retry, changed request rejection, one mutation |
| Claim invocation | Claim CAS loss and durable recovery without a second claim mutation |
| Lease invocation | Lease CAS loss after the claim mirror, restart recovery, exact replay |
| Terminal attestation | Post-apply loss, restart, changed evidence rejection, one mutation |
| Terminal commits | Claim and lease CAS loss independently, restart recovery, exact replay |
| Cross binding | Claim, route, holder, target, invocation, and evidence substitutions fail closed |
| Journal | Phase skip/reversal, digest deletion, record tamper, immutable purpose |
| Receipt gate | Missing/wrong CI, incomplete Python matrix/stages, placeholders, invalid parent/scope |
| Legacy source | E44-E46 regressions remain green and legacy positive paths remain closed |

## CI contract

`.github/workflows/brainops-e47.yml` checks out the PR head SHA rather than a
merge ref, asserts that `HEAD` equals that SHA, checks parent availability and
diff whitespace, then compiles and runs the full synthetic suite on Python 3.11
and 3.13. It must be green once at the substantive tested head and again at the
receipt-only head.
