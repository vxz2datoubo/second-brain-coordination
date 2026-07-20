# Security, Trust and Permission Boundary

## Trust zones

| Zone | Permitted content | Prohibited content |
|---|---|---|
| Public coordination repository | Sanitized plans, schemas, task state, tests, backwrite deltas, hashes | Protected blueprint bodies, private knowledge, credentials, account data, licensed raw market data |
| Local candidate workspace | Candidate packets and reversible local experiments | Automatic promotion to cloud/authority |
| Future private knowledge repository | Approved knowledge, provenance, review history | Broker credentials and unrestricted runtime logs |
| Raw evidence store | Entitlement-scoped raw artifacts and manifests | Public release unless license/approval allows |
| Serving projection | Rebuildable search indexes and least-privilege read APIs | Source-of-truth mutation and arbitrary SQL exposure |
| Research runtime | Replay/simulation and controlled adapters | Broker order/control path |

## Permissions

- USER: changes to protected blueprints, authority migration, cloud creation, credentials, data upload, real-money/execution and irreversible actions.
- GPT: architecture, task routing and acceptance; cannot mutate production files.
- CODEX: contracts, code, tests, audits and plans; cannot access secrets, create cloud resources, trade or self-approve protected backwrite.
- WORKBUDDY: local environment, licensed source capability and deployment verification; cannot infer unverified data capability.
- QCLAW: offline candidate-package digestion only; no online authority, decision or execution role.

## Gates

1. Capability and entitlement gate before reading vendor data.
2. Schema/lineage/quality/time gate before normalisation.
3. Evidence, counter-evidence and abstention gate before assessment.
4. OOS/cost/A-share-rule/risk gate before research maturity promotion.
5. Human approval gate before protected-blueprint update, authority migration, cloud action or execution-related scope.
6. Audit/rollback gate before any destructive or non-reversible change.

## Security finding

The current shared local repository is dirty and contains generated/runtime-looking artifacts. It must not be treated as a clean security baseline for a new enterprise migration. Phase 0 writes are isolated in the public coordination branch only.
