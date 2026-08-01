# P0/P1/P3 Implementation Notes

## Data-flow boundary

```text
redacted GitHub review metadata or local fixed-command inventory
  -> typed contracts
  -> shadow reconciliation / SQLite audit metadata
  -> loopback GET-only console
```

There is deliberately no arrow from a decision to a command runner, process,
service controller, App Automation trigger, GitHub mutation, market route, or
trading action.

## Control-plane objects

| Object | Purpose | P1/P3 behavior |
|---|---|---|
| `ServiceManifest`, `PortManifest` | Describe a manual local component | Rejects executable paths, arguments, and non-loopback bind hosts |
| `DesiredState`, `ObservedState` | Separate request from observation | Does not change either state |
| `ActivationManifest` | Captures a specific route/epoch/idempotency request | Validates only; no activation write or dispatch |
| `Lease` | Fences one route epoch to one owner | SQLite unique active lease; direct metadata tests only |
| `AppAutomationIdentity`, `CliSession` | Describe possible execution surfaces | App claims require local evidence; CLI auth is `NOT_INSPECTED` |
| `ReviewRequestEvent` | Redacted GitHub event input | In-memory shadow observer only |
| `ShadowDecision` | Counterfactual decision evidence | `actual_dispatch_performed` is structurally forbidden |

## Status semantics

`WOULD_DISPATCH` is only emitted when a **hypothetical** context has all gates
open. The E35 route itself has `automatic_dispatch_allowed: false`, therefore
its real decision is `WOULD_BLOCK(automation_disabled)`. This distinction lets
tests cover a ready route without misrepresenting the current permission.

## Deferred work

- Verify a supported App Automation surface, schedule semantics, review queue,
  app-awake requirement, and an official external activation interface.
- Approve a real port registry entry before a manual control-console start.
- Add an allowlisted executor only after an explicit route, a security review,
  a user approval contract and an independent test plan.
- Integrate a future MaiBot component only through its own port/ownership
  manifest. The registry in this delivery is `INTERFACE_ONLY`.
