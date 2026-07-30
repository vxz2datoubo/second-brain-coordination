# E25 Evidence Matrix

| Requirement | Evidence | Result |
| --- | --- | --- |
| Ten predicate registry | exact ten-ID `invariant_registry.py` | PASS |
| Real controlled violations | constructors derive malformed `GameRun` or episode artifacts | PASS |
| Valid and invalid execution | every 80 invariant row executes both paths | PASS |
| Named oracle reads object | reason codes and violating-artifact SHA retained | PASS |
| Decorative fixture rejection | identity constructor raises `DECORATIVE_OR_NON_VIOLATING_FIXTURE` | PASS |
| Orphan/incomplete registry rejection | focused tests fail closed | PASS |
| Episode provenance | call count is exactly 24; no catalog rerun | PASS |
| Counterfactual provenance | call count is exactly 32; no formula reconstruction | PASS |
| Signature sensitivity | consumed input and observed relation have separate tested signatures | PASS |
| Historical evidence preservation | cumulative E22-E25 records restored | PASS |
| CI | GitHub Actions `30577091133` | PASS |
| Fresh archive rerun | bounded local attempt | NOT_ACCEPTED |

This is synthetic evaluator evidence only, not market, identity, forecast,
profitability, or production evidence.
