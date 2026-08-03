# E46 Test Matrix

## Local tested matrix

Exact command:

```text
python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -p "test_e*.py"
```

- Python: 3.13.13
- Imported E44/E45 regressions: 96
- E46 focused tests: 52
- Total: 148
- Result: PASS
- Live requests: 0

Captured local evidence:

| Python | Exit | stdout SHA256 | stderr SHA256 |
|---|---:|---|---|
| 3.13.13 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `88e72bb8a3649346e297a99a7bd9dfa1619a563f2ae388f245e4a3cabb0ba83b` |
| 3.12.10 compatibility | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `74be335ae5c5ca212542c31348a317458f1ef49dbb73beaa801f443604505298` |

The local host does not expose Python 3.11. Python 3.11 remains an explicit
GitHub Actions acceptance gate rather than an unverified local claim.

## E46 coverage groups

| Group | Evidence |
|---|---|
| Lease monotonicity | versions 1-5, replay, skipped/repeated transitions, expiry |
| Binding isolation | holder, target, provenance, claim, invocation, transport, source |
| Legacy bypass closure | old effect permit, direct attach, direct finalize, old terminal validator |
| Identity | Manual App, Automation, CLI, direct-constructor and copied-string negatives |
| Terminal evidence | raw evidence rejection, CLI exit semantics, one-shot attestation |
| Terminal mutation | sealed authorization, claim terminal CAS, committed receipt, idempotent reread |
| Recovery | claim-CAS response loss, lease-CAS response loss, restart, not-applied classification |
| Tamper detection | lease record hash, operation journal record and hash chain |

## CI matrix

`.github/workflows/brainops-e46.yml` runs compile and all 148 tests on Python
3.11 and 3.13. It is required to pass once at the substantive tested head and
again at the receipt-only head.
