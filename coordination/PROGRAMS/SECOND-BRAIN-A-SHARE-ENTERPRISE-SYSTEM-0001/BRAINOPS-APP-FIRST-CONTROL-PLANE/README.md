# BrainOps App-first control plane (E35)

This is the first local, visible control-plane foundation for the second-brain
program. It is intentionally a **read-only and shadow-only** delivery.

## What is present

- Strict contracts for service and port manifests, desired route state,
  activations, idempotency, leases, fencing generations and execution ownership.
- A loopback-only, GET-only local console with polling recovery.
- SQLite metadata/audit storage that redacts secret-like fields before writing.
- Fixed-command read-only host discovery.
- A shadow reconciler which explains `WOULD_DISPATCH` or `WOULD_BLOCK` without
  starting processes, sending a GitHub event, invoking Codex, or changing state.
- A 30-minute anti-entropy **fixture**, not a scheduler.

## Explicit non-capabilities

- No unattended App Automation or CLI execution.
- No App UI automation, private IPC, deep-link trigger, process/service control,
  scheduler setup, firewall change, external network bind or port reservation.
- No broker, account, order, market-data or trading operation.
- No modification of PR #107, PR #100, or the QQ authority route.

`APP_AUTOMATION` is modeled as the preferred ownership type, not declared
available. Local support for it, 30-minute schedules, review queues and external
activation remains in [UNKNOWN-REGISTRY.yaml](UNKNOWN-REGISTRY.yaml).

## Manual inspection only

Run tests from this directory's parent worktree:

```powershell
python -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -v
```

The following command can manually start a loopback-only console **only after a
separate port-registry check and user approval**. It is not run by E35:

```powershell
$env:PYTHONPATH = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src"
python -m brainops_control_plane.cli serve --port 32100
```

The management page exposes only `GET /`, `GET /api/v1/status`,
`GET /api/v1/services`, `GET /api/v1/ports`, and `GET /api/v1/audit`. Every
mutating verb fails closed with HTTP 405.
