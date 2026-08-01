# ADR-001: App-first, read-only BrainOps architecture

## Decision

Use the Codex view in the unified desktop application as the preferred
human-visible surface. Model `APP_AUTOMATION` as the first ownership candidate,
then `CLI_FALLBACK`, then `MANUAL_APP`, then `NONE`. E35 does not invoke any of
them. It only evaluates a shadow outcome and keeps the task route itself blocked
because automatic dispatch is disabled.

Use a standard-library Python web console rather than ASP.NET Core/Blazor in
this delivery. P0 found a Windows desktop host and a discoverable `dotnet`
command, but no usable SDK listing; the repository also has no established .NET
application. The chosen implementation is loopback-only and introduces no
runtime dependency.

## Consequences

- The console is visible and testable without claiming background service
  installation or a production App interface.
- Any later automation must supply an official supported trigger or a local
  capability observation. It cannot inherit authority from this schema.
- `WOULD_DISPATCH` is counterfactual evidence only. The decision object prohibits
  `actual_dispatch_performed=true`.
- P1 uses polling as the live-status equivalent. The page re-fetches current
  state every five seconds and presents a reconnect state when offline.

## Rejected alternatives

- CLI-first hidden executor: violates App-first visibility and risks duplicate
  ownership.
- UI mouse/keyboard automation or private IPC: unsupported, brittle and outside
  the task boundary.
- Binding `0.0.0.0` or a LAN address: rejected by the `PortManifest` contract.
- Adding a service scheduler now: requires capability and user approval not in
  this route.
