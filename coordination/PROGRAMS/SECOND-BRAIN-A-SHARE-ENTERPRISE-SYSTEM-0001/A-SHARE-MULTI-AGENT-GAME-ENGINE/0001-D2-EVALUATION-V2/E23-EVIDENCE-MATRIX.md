# E23 Evidence Matrix

| Route requirement | Implemented evidence | Verification | Result |
| --- | --- | --- | --- |
| Callable D2 semantics are mutated | `shadow_sut.py` exact source replacements and in-memory compilation | 8 same-fixture baseline/mutant executions | PASS |
| Post-hoc output mutation is forbidden | registry validation rejects output-only seams | focused negative registration test | PASS |
| Every family has a semantic killer | 8 family-specific oracle IDs, no generic digest-only outcome | focused mutation tests and runner | PASS |
| MUT-008 weakens an actual boundary | exact checks become `isinstance` only in shadow source | tuple-subclass baseline/mutant differential | PASS |
| Catalogs are distinct | normalized input-plus-relation signatures | six duplicate-family fail-closed tests | PASS |
| Metamorphic rows are transformations | 8 distinct input transforms paired with mutants | focused property tests and runner | PASS |
| Determinism is clean-root based | Git archive roots at seeds 1, 7, and 97 | stable full-report SHA-256 `b8ed8929...` | PASS |
| CI invokes E23 | permitted workflow step | GitHub run 30493601388, Python 3.11 and 3.13 | PASS |
| Public safety holds | public-safe scanner plus changed-file pattern scan | 57 Phase 3 files and 15 E23 files, 0 issues/matches | PASS |

## Boundary Confirmation

The matrix provides synthetic evaluator evidence only. It does not authorize
market-data activation, replay, backtest, model fitting, performance claims,
participant identification, accounts, orders, trades, Gate C, or Gate D.
