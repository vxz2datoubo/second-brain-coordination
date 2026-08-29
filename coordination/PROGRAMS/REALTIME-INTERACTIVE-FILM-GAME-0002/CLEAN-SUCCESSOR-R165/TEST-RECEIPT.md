# R165 Local Test Receipt

`agent_id: CODEX`

Baseline: `0665cc0147fe7efae7e9498c36f9a87566ad036c`
Implementation commit: `41bd859aa3d8c9d598bec8456c95e30853a562bc`

## Executed locally

```text
python -m unittest discover -s tests -v
Result: 29 tests passed (Python 3.13)

python -m compileall -q creative_runtime apps/cli tests
Result: PASS

git diff --check 0665cc...HEAD
Result: PASS before commit
```

The local environment does not include `pytest` or Python 3.11. The task-owned
workflow requires a GitHub exact-head Python 3.11/3.13 matrix before review.

## Evidence covered

- Original S00–S06 suite: 22 tests.
- R165 adversarial suite: 7 tests, including caller-hash state-patch rejection,
  source-bound terminal bridge, provenance durability across play and slots,
  native-v2 non-labelling, legacy byte preservation, and fail-closed migration.
