# Security, Trust and Permission Boundary v1.1

## First principle

Knowledge privacy classification and publication/storage permission are separate dimensions.

All user-authorized non-secret knowledge, including personal, private, internal, project and conversation knowledge, may be stored in the public GitHub repository, the local knowledge architecture, or both.

The only hard-sensitive values that must never enter repositories, knowledge atoms, embeddings, logs, issues, PRs, tests or AI handoffs are authentication, access and financial-security secrets, including API keys, tokens, passwords, cookies, sessions, private keys, recovery phrases, 2FA secrets and bank/broker authentication values.

Third-party ownership, copyright, entitlement and publication licenses remain a separate governance gate. A document may be non-secret but still not authorized for publication.

## Trust zones

| Zone | Permitted content | Prohibited content |
|---|---|---|
| Public coordination repository | User-authorized non-secret knowledge, source bodies, plans, schemas, atoms, evidence, task state, tests, backwrite deltas and hashes | Authentication/access/financial secret values; unauthorized third-party material; restricted raw market data without publication rights |
| Local candidate workspace | User-authorized non-secret knowledge, candidate packets, cognitive observations and reversible experiments | Secret values; automatic authority promotion; unapproved irreversible actions |
| Local or private knowledge repository | Approved or candidate knowledge, provenance, personal cognitive evidence, review history and source bodies | Authentication/access/financial secret values and unrestricted credential-bearing runtime logs |
| Raw evidence store | Entitlement-scoped raw artifacts, user-authorized personal artifacts and manifests | Secret values; public release when publication or license basis is absent |
| Serving projection | Rebuildable search indexes, embeddings, graphs, palace indexes and least-privilege read APIs | Source-of-truth mutation, arbitrary SQL exposure and secret values in indexes |
| Research runtime | Replay, simulation, cognitive calibration and controlled adapters | Broker order/control path and automatic irreversible decisions |

A `PRIVATE_KNOWLEDGE` label does not by itself block public storage. Storage is governed by explicit `storage_targets`, `transport_visibility`, user authorization and publication/license basis.

## Permissions

- USER: controls project direction, public-storage authorization, personal-model corrections, authority migration, cloud creation, credentials, real-money execution and irreversible actions.
- GPT: research, architecture, task routing, adversarial review and acceptance; no secret handling or real-trade control.
- CODEX: project planning, canonical contracts, code, tests, audits and integration; cannot access secret values, trade or self-approve high-risk authority changes.
- WORKBUDDY: local sources, file parsing, licensed capability, adapters, deployment and real-run evidence; cannot expose secrets or infer unverified capability.
- QCLAW: knowledge atomization, continuous digestion, long-term memory planning/building, cognitive-model candidates and adversarial epistemic testing; no secret handling, silent authority promotion, parallel canonical runtime or real execution role.

## Gates

1. User authorization and publication/license gate before public storage of source material.
2. Exact secret-value scan and redaction before storage, atomization, embedding, logging or commit.
3. Capability and entitlement gate before reading vendor or restricted data.
4. Schema, lineage, quality, context and time gate before normalization.
5. Evidence, counterevidence, conflict, UNKNOWN and abstention gate before assessment.
6. State/trait/context/domain and roleplay/humor gate before personal cognitive-model updates.
7. User review, correction, revocation and dependency-propagation gate for personal-model changes.
8. OOS, cost, A-share-rule, risk and probability-calibration gate before research maturity promotion.
9. Human approval gate before authority migration, cloud action, high-impact personal publication changes or execution-related scope.
10. Audit and rollback gate before destructive or irreversible change.

## Mixed documents

When a document contains useful knowledge and secret values:

1. identify the exact secret span;
2. replace or remove only the secret value;
3. preserve and process the remaining knowledge;
4. record secret type, location and redaction status without recording the original value;
5. do not reject the entire document merely because one secret was present.

## Current security finding

Historical files may contain superseded statements such as “private knowledge cannot enter the public repository.” Those files remain as audit history unless they are active authority documents. Current execution must follow this v1.1 boundary, PROGRAM-INDEX v1.1, the current QCLAW router and the latest issue comments.

The research and execution boundary remains `research_only / NO_TRADE`; LLMs are not permitted in the real-order critical path.
