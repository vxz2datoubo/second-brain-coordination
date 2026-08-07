# E56 Test Evidence

Local tested-head command: `python -m unittest discover -s tests -v` with task `src` and `tests` on `PYTHONPATH`; exit code `0`; 41 tests passed. The local runner was Python 3.13 and its source-mutation phase was serial.

Provider command: `python tools/provider_runner.py --output provider-evidence --branch codex/e55-post-receipt-canonical-authority-closure-0052-e56 --workflow .github/workflows/codex-e56-canonical-authority-closure.yml --seed <0|1|777> --job-name <matrix-slot> --run-id 31110242028 --run-attempt 1 --expected-head fd26669a5286be9d967f96afe363093189f26c8d`.

For every Provider authority artifact: test count `41`, mutation count `19`, test stdout SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, and every mutation returned `1` when mutated and `0` after exact restoration. Per-job stderr and mutation-payload hashes remain independently bound inside their named environment archives listed in `EXTERNAL-PROVIDER-ANCHOR.json`.

The rejected historical run `31108957207` is retained in `NEGATIVE-FINDINGS-LEDGER.yaml`; it is not counted as successful evidence.
