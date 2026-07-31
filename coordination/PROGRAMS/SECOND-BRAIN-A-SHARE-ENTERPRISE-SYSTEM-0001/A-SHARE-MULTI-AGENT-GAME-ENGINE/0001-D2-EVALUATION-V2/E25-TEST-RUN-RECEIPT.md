# E25 Test Run Receipt

Tested commit: `5c10a31326eb873fd02233a445f9a5d6c17a1c3c`.

| Command | Exit | Result |
| --- | --- | --- |
| `python -B tests/test_evaluation_v2.py` | `0` | `Ran 49 tests` / `OK` |
| `python -B tests/run_evaluation_v2.py` | `0` | report SHA `85b734d1ea80b71869e6794a639f72cfa23b0664478adfcd42bb9cca3d6facb7` |
| `gh run watch 30577091133 --exit-status` | `0` | GitHub Actions success |

The runner captured stdout SHA-256 is
`31bec3448b929d1bd30069b348b5074a66a83ce136e934278475053af3d7c62a`; its
stderr SHA-256 is
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The direct unittest run passed. A separately redirected unittest capture
exceeded the bounded local timeout, so this receipt does not invent its stream
hash. That capture and fresh archive evidence are explicitly `NOT_ACCEPTED`.

Counts retained: `72` scenarios, `80` invariants, `10` negatives, `24`
episodes, `32` counterfactuals, and `24` cross-family interactions.
