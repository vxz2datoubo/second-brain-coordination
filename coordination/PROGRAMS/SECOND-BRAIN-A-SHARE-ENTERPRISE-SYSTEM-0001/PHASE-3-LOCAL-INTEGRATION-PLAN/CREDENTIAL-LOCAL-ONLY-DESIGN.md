# Credential Local-Only Design

## Correct authority

The governing project rules are:

- `coordination/AUTHORIZATION/CREDENTIAL-SECRETS-LOCAL-ONLY-v1.0.yaml`
- `coordination/GOVERNANCE/LOCAL-CREDENTIAL-DIRECT-USE-AND-NON-EXPORT-PROTOCOL-v1.0.yaml`
- `coordination/CODEX-TASK-ROUTER.md`

The specific local-credential protocol overrides older generic wording that treated all credential access as denied. The prohibition applies to export and unauthorized privilege use, not to authorized reading inside the user's local machine.

## Design

1. Authorized knowledge is eligible for full semantic reading, atomization, relationship mapping, and retrieval through the private/local gateway.
2. Credential values remain in a local credential store, existing local configuration, environment, authenticated session or operating-system credential store. They are never copied into datasets, public Git, logs, context bundles, test fixtures, exception text or handoff artifacts.
3. A public-safe `CredentialReference` contains only `reference_id`, category, purpose, owner, last-updated metadata, verification digest and local location hint.
4. Runtime adapters may request a reference ID, or local Codex may directly discover the corresponding local secret under the approved discovery order. The resolver supplies the value only inside the local process boundary.
5. For an authorized WorkBuddy MCP, TongDaXin/TDX, TQ or other user-owned local adapter task, local Codex may directly read the existing credential value, inject it into the local process and perform authentication or connectivity tests without repeated user confirmation.
6. `LOCAL_ONLY` means the value must not leave the user's machine. It does not mean local Codex must pretend the value is unreadable.
7. Reports classify an item as `environment_variable_reference`, `local_config_reference`, `authenticated_session_reference`, `os_credential_store_reference`, `placeholder_or_example` or `unknown_requires_user_review`; they never reproduce values.
8. Missing configuration fails closed only after the approved local discovery order has been exhausted, using a secret-free error code.
9. Reading WorkBuddy-owned local MCP configuration for interoperability does not transfer WorkBuddy branch, task, history or canonical ownership to Codex.

## Approved local discovery order

1. Existing authenticated session.
2. Process or user environment variables.
3. Project-approved local configuration reference.
4. WorkBuddy or adapter-local configuration.
5. Already configured operating-system credential store.

## Efficiency rule

Local Codex should use the shortest reliable path. It should reuse existing sessions and credentials, avoid asking the user to paste values, and must not refuse an otherwise authorized local task merely because authentication requires a secret.

## Non-export controls

- Do not print secrets to stdout or stderr.
- Avoid command-line arguments that enter shell history or process listings.
- Prefer process environment injection, stdin, provider SDK session objects or OS credential APIs.
- Do not create new persistent plaintext copies.
- Redact subprocess errors before saving them.
- Never include values in Git, GitHub, PRs, issues, receipts, AI handoffs, tests, datasets, embeddings, knowledge graphs, chat or telemetry.

## Separately gated capabilities

This design authorizes local authentication and connection only. It does not by itself authorize:

- real-data admission into research pipelines;
- historical replay or backtesting;
- model fitting or performance claims;
- broker account access;
- order routing or trading;
- credential rotation, deletion or privilege expansion.

Those capabilities require their own active route or explicit user authorization.

## Acceptance evidence for implementation

- local credential reference resolution test;
- direct local read and authentication test using redacted output;
- missing-reference fail-closed test after all approved sources are attempted;
- log and subprocess redaction test;
- shell-history/process-list exposure test;
- static scan proving no public artifact contains a credential value;
- manual verification that only secret-free reference metadata appears in receipts.
