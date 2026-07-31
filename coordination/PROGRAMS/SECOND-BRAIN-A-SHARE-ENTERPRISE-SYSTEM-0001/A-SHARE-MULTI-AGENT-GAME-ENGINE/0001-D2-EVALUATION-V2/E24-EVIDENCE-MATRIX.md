# E24 Evidence Matrix

| Gate | Evidence | Result |
| --- | --- | --- |
| Execution-derived signatures | `catalog_validation.py` validates executed input plus observed relation | PASS |
| Named invariant dispatch | all 80 rows invoke predicate and registered oracle check | PASS |
| Metadata-only duplicates | renamed-only input is rejected | PASS |
| E23 regression | 8 mutations and 8 properties remain green | PASS |
| CI | GitHub run `30535795631`, Python 3.11/3.13 | PASS |
| Archive determinism | seeds 1/7/97 share output hash `075867a...d751` | PASS |

Truthful counts: scenarios 72, invariants 80, negatives 10, episodes 24, counterfactuals 32, cross-family 24.
