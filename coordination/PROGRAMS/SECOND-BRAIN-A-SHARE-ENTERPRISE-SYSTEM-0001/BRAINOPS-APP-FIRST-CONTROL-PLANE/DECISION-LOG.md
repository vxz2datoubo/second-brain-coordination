# BrainOps Decision Log

## D-001: App-first remains a policy, not a claimed local capability

The installed desktop package proves only that the Codex desktop host is present. App
Automations, its schedule precision, external activation, and App/CLI session sharing
remain `UNKNOWN`. The control plane therefore models `APP_AUTOMATION` as an explicit
ownership option but never invokes it in P0/P1/P3.

## D-002: Use a standard-library Python console

The checked repository has no existing .NET solution and no usable .NET SDK was verified.
The implementation uses Python's standard library rather than adding a framework. This is
the task brief's permitted low-dependency equivalent, not a claim that Blazor is absent in
all future environments.

## D-003: Reconciliation is counterfactual only

`WOULD_DISPATCH` means all modeled preconditions are satisfied in a synthetic or future
authorized configuration. It never starts a process, calls the Codex app, writes an
activation, or claims that unattended execution is enabled. The live task route has
`automatic_dispatch_allowed: false`, so it is always represented as blocked.

## D-004: Port 32100 is a candidate, not a reservation

P0 observed the existing SuperBrain listener at port 8766 and no listener at 32100. This
delivery does not bind any port outside isolated tests, does not edit the service registry,
and requires a fresh registry check before any later manually approved console start.
