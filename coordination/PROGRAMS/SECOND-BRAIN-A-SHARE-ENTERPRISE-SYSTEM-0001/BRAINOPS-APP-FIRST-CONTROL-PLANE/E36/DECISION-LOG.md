# E36 Decision Log

## D-001: E35 is immutable input

E36 imports the reviewed E35 source chain into its own branch. PR #110 and its
historical E35 receipt remain unchanged. E36 is permitted only to harden the
trigger evidence path.

## D-002: A supported surface is not authority to execute

The host exposes an automation-management interface and the local CLI exposes
noninteractive mode. Neither fact is a bound approval for this exact canary.
Until an approval binds canary ID, task ID, epoch, scope, expiry, and nonce,
the only valid runtime result is `BLOCKED_APPROVAL_NOT_BOUND`.

## D-003: No execution mechanism is invoked in E36 development

The implementation models and verifies gates. It does not invoke the CLI,
App Automation management API, browser automation, private IPC, a service, or
any trading surface.
