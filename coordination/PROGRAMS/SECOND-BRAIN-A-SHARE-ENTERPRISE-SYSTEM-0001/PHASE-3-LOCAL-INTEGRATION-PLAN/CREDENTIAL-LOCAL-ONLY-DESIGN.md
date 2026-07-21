# Credential Local-Only Design

## Correct authority

The governing repository files are `coordination/AUTHORIZATION/CREDENTIAL-SECRETS-LOCAL-ONLY-v1.0.md` and `.yaml`. The task's alternate filename was not present in the verified remote tree; this plan deliberately uses the corrected path.

## Design

1. Authorized knowledge is eligible for full semantic reading, atomization, relationship mapping, and retrieval through the private/local gateway.
2. Credential values are a narrow exception. They remain in a local credential store or existing local configuration and are never copied into datasets, public Git, logs, context bundles, test fixtures, exception text, or handoff artifacts.
3. A public-safe `CredentialReference` contains only `reference_id`, category, purpose, owner, last-updated metadata, verification digest, and local location hint.
4. Runtime adapters request a reference ID; a local resolver supplies the value only inside the local process boundary. Missing configuration fails closed with a secret-free error code.
5. Reports classify an item as `environment_variable_reference`, `local_config_reference`, `placeholder_or_example`, or `unknown_requires_user_review`; they never reproduce values.

## Non-goals for Phase 3 planning

- No reading of existing credential files or environment values.
- No authentication test, credential migration, rotation, deletion, or provider call.
- No addition of a new secret manager dependency.

## Acceptance evidence for later implementation

Static scan of modified code, missing-reference fail-closed test, placeholder resolution test, log-redaction test, and a manual check that no public artifact contains a credential value.
