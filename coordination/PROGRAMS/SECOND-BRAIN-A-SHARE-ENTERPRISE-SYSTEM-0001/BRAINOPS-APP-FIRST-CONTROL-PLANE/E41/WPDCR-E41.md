# Work Package Development Change Report: E41

`agent_id: CODEX`
`status: SUBSTANTIVE_IMPLEMENTATION_PENDING_EXACT_HEAD_CI`

## Hypotheses

1. A revisioned CAS interface can express one-shot consumption without an
   external call in this task.
2. A synthetic file-backed CAS can test cross-process semantics without being
   promoted to production authority.
3. Explicit evidence classification prevents claim-only overstatement.

## Delivered paths

- `src/brainops_control_plane/durable_authority.py`
- `src/brainops_control_plane/route_terminalization.py`
- `src/brainops_control_plane/execution_evidence.py`
- `tests/test_e41_durable_authority.py`
- `.github/workflows/brainops-e41.yml`
- E41 decision, threat, evidence, status and import-accountability records.

## Commands and exits

The final substantive test receipt will record exact stdout/stderr hashes,
Python versions, and exit codes before the receipt-only commit. No App, CLI,
Canary, external GitHub write, credentials, or trading command is included.

## Residual risks

The production CAS client and the future route publisher are intentionally
outside E41. CI can prove the contracts and synthetic adversarial cases, not
live dispatch behavior.
