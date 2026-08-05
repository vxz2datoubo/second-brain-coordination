# E48 Research Ledger

## Scope and sources

| Source | Role | Status |
| --- | --- | --- |
| Issue #152 and its active route | Authorization and completion requirements | Read and applied |
| Draft PR #154 review history | Returned defects and expected evidence | Read and applied |
| E46/E48 authority modules and tests | Reuse boundary and executable behavior | Read and tested |
| GitHub Actions runs for `00c2e805a5e74354698c2c47822c59b83d219566` | Exact-head Python 3.11 and 3.13 evidence | Green |

No live authority, credential, market, broker, or external data source was used.

## Research questions and results

| Question | Result | Evidence class | Boundary |
| --- | --- | --- | --- |
| Can a post-apply response loss be recovered without a second effect transition? | Yes, under a purpose-bound durable stage journal and matching live lease. | VERIFIED_CODE_OR_TEST | Synthetic file-CAS only. |
| Can cross-record claim/lease partial writes be recovered without duplicate claim mutation? | Yes, for claim-only and lease-applied response-loss paths. | VERIFIED_CODE_OR_TEST | Does not prove production storage semantics. |
| Can an identical delayed capability attestation recover a current continuation? | Yes when binding fields match and the current lease remains valid; changed binding and expiry fail closed. | VERIFIED_CODE_OR_TEST | Not a production capability grant. |
| Does the release gate remain fail closed when generated evidence dirties the checkout? | Yes; the earlier CI failure was reproduced from its log. The workflow now writes generated evidence to the runner temporary directory. | VERIFIED_CODE_OR_TEST | Final provider conclusion remains independent-review pending. |

## Non-results deliberately preserved

- No production trust root, transport, or identity-provider claim was tested.
- No live authorization action or irreversible effect was attempted.
- No final provider conclusion is self-certified by the workflow.
- No conclusion is promoted beyond `research_only / NO_TRADE`.

## Reproduction commands

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
python -m brainops_control_plane.release_gate --repository-root . --base-commit ac17da81f3c632014ae9ca7e0420707fb5de4312 --tested-commit 00c2e805a5e74354698c2c47822c59b83d219566
python -m brainops_control_plane.mutation_harness --repository-root . --base-commit ac17da81f3c632014ae9ca7e0420707fb5de4312
```

The exact stdout and stderr artifact hashes are recorded in `TEST-RUN-RECEIPT.json`.
