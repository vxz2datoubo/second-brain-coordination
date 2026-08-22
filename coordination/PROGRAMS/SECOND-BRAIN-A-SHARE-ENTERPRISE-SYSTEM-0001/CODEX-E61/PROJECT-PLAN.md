# E61 Project Plan: Real Production Durable Authority and Formal Knowledge-Write Gate

## 1. Lease, purpose, and immutable boundaries

| Field | Value |
|---|---|
| Task | `CODEX-REAL-PRODUCTION-DURABLE-AUTHORITY-EXTERNAL-ISSUANCE-VERIFICATION-KNOWLEDGE-WRITE-GATE-0057-E61` |
| Route epoch | `63` |
| Canonical main at claim | `f33ba3f698570a39b933f67fcb6f0f95810365c2` |
| Branch | `codex/real-production-durable-authority-0057-e61` |
| Predecessor evidence | E60 receipt `e06675f9faf17abf04d7774e42743f64dc008c00` |
| Operating state | `research_only / NO_TRADE / formal_write_disabled` |

E60 establishes a useful **synthetic** verifier, source/span, Provider, and resource-cleanup proof. It does not establish production durable authority and must not be imported wholesale. E61's purpose is to specify, implement where safe, and independently test the narrow gate through which an existing E47 `CandidateKnowledgePackage` can eventually receive a formal `PROJECT` or `GLOBAL` knowledge certification.

No task artifact may itself enable a formal knowledge write. No credential, private key, GitHub App installation, repository setting, environment, branch protection rule, deployment permission, market interface, account, order, or trading capability may be created, read, changed, or requested by this task without the route's explicit user-approval stop.

## 2. Verified starting facts

The following facts were read through the canonical GitHub repository/API at plan time, not inferred from local configuration:

| Fact | Evidence | Consequence |
|---|---|---|
| Repository is public; default branch is `main`. | GitHub repository API. | Public repository contents cannot carry a private issuer or formal authority secret. |
| `main` branch-protection endpoint reports `404 Branch not protected`. | GitHub branch-protection API. | A workflow or branch alone is not an independently protected production authority. |
| No deployment environments exist. | GitHub environments API: `total_count: 0`. | There is no existing reviewer-gated production environment to reuse. |
| Actions default workflow permission is `read`; PR review approval is disabled. | GitHub Actions permissions API. | This is favorable as a baseline but insufficient to confer formal write authority. |
| OIDC subject customization is default and `use_immutable_subject` is false. | GitHub OIDC customization API. | Any future OIDC trust policy needs explicit immutable repository/ref/environment conditions. |
| E47 is a parallel candidate-only task and its formal persistence remains blocked. | Active route contract. | E61 consumes a content-addressed candidate; it must not redigest or rewrite it. |

These observations are current-state evidence, not a recommendation to change settings. Their exact API responses will be retained in the later public-safe audit without values that could become sensitive.

## 3. Authority design decision process

E61 will compare these two viable control-plane families before selecting an implementation target. Neither is treated as configured or accepted today.

### Option A — protected GitHub environment plus OIDC to an external issuance/verifier service

1. A workflow executes only from a protected ref and a protected `knowledge-certification` environment.
2. GitHub issues a short-lived OIDC token bound to immutable repository identity, ref, workflow, environment, SHA, run, and audience conditions.
3. An externally administered issuer/verifier service validates those claims, validates a candidate content/provenance digest, records a single-use certification identifier, and issues a short-lived scoped capability.
4. The adapter verifies the issuer identity and exact grant before asking the future formal store to write.

This is the preferred target because issuer control, key management, revocation, and single-use state are outside ordinary repository caller code. It requires a user-approved external service/control plane, repository protection/environment configuration, and a least-privilege trust policy. GitHub documents that OIDC exchanges short-lived job identity for cloud-provider access and that the provider must constrain trusted claims; environments can require reviewers and branch restrictions. [GitHub OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect), [OIDC deployment hardening](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers), [deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

### Option B — GitHub artifact attestation plus protected workflow

GitHub artifact attestation can bind build provenance and a digest to a workflow identity. It is useful evidence, but it is not by itself a complete formal-write authority: it does not supply independent issuer state, a revocation record, a one-time certification ledger, or a protected write capability. This option is therefore an evidence input to Option A, not a standalone production authority unless an independently controlled verifier and write gate are added. [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

### Explicitly rejected as production authority

- Repository-local signing fixtures, environment variables, Python private imports, or any issuer code importable by the candidate caller.
- A mutable branch label, a human-readable PR comment, or a single CI green result with no protected external issuer.
- An artifact attestation treated as a direct write permit without single-use, revocation, and formal-store checks.

## 4. Proposed fail-closed contract boundary

The implementation phase may introduce only public-safe contracts and verifier behavior. In the absence of an approved real provider, all certification requests must fail closed with a non-promotable `EXTERNAL_AUTHORITY_NOT_CONFIGURED` state.

```text
CandidateKnowledgePackage (existing, content-addressed)
  -> CandidateCertificationRequest
  -> ExternalAuthorityEvidence (provider-issued; not caller-issued)
  -> ProductionAuthorityVerifier
  -> SingleUseCertificationGrant (scoped, expiring, revocable)
  -> FormalWriteGate (still disabled until independent GPT acceptance)
```

Mandatory bindings:

- candidate package content hash, source/provenance digest, schema version, and semantic digest;
- authority provider identity and key/issuer fingerprint, immutable route/task/ref/SHA/run/approval context, audience, issued/expiry time, and nonce or grant identifier;
- intended scope (`PROJECT` or `GLOBAL`), target record identifier, and a single-use ledger key;
- exact verifier policy version and an explicit revoke/unknown status;
- no raw bytes, aliases, caller-selected issuer keys, self-created receipts, or mutable branch names as authority substitutes.

The certification adapter is a translator and gate consumer. It must neither atomize source material nor alter the candidate package. A formal store adapter remains denied until GPT independently accepts this exact E61 gate.

## 5. Work packages, checkpoints, and stop conditions

| Package | Delivery | Validation | Stop condition |
|---|---|---|---|
| WP0 | This plan-only commit and Draft PR. | Exact fresh main base, one-path diff, no runtime changes. | Branch/base mismatch. |
| WP1 | Current-authority audit, reuse ledger, E47 interface audit, official-source research ledger, and ADR. | Reproduce repository-control-plane reads; compare Options A/B and rejected designs. | Required current state cannot be observed. |
| WP2 | Public-safe production-authority and candidate-certification contracts; fail-closed verifier skeleton. | Schema round trips; unavailable-provider and caller-bootstrap failures. | Contract implies an issuer secret, private key, or formal write. |
| WP3 | Narrow E47 candidate certification adapter and adversarial/mutation registry. | Self-issuance, stale/replay, wrong provider/key/actor/route, semantic/source tamper, duplicate-use, and bypass tests. | E47 interface is unavailable or requires cross-agent branch modification. |
| WP4 | Only if a real external control plane can be configured without unauthorized change: provider integration plan and exact `USER_APPROVAL_REQUIREMENTS.yaml`. | Verify that every required protection, service, and trust claim is externally controlled. | Any app, secret, private key, repo/environment/protection/permission action is needed: stop at `USER_APPROVAL_REQUIRED`. |
| WP5 | Provider tests for the executable head, public-safe evidence aggregate, and independent audit packet. | Two-version remote CI; exact head, parent, tree, job, artifact, and digest binding. | Matrix/artifact/topology mismatch. |
| WP6 | GPT-authorized receipt-only direct child and final handoff. | Receipt scope allowlist and receipt-head provider run. | No explicit GPT receipt authorization. |

No package promotes formal write authority. WP4's likely output is a precise approval requirement rather than a settings change; that is a successful, safe outcome when no approved external control plane exists.

## 6. Adversarial model and acceptance tests

Every proposed provider/verifier must reject, with an object-derived reason and preserved evidence:

1. ordinary caller self-issuance, private-import bootstrap, or local fixture substitution;
2. alternate key, alternate provider, mutable alias, invalid audience, wrong repository/ref/workflow/environment/SHA/run;
3. stale, expired, replayed, duplicate-use, or revoked grant;
4. altered candidate content hash, semantic field, source span, provenance digest, or intended scope;
5. wrong approval actor/reference, missing independent approval, or approval after expiry;
6. raw-byte admission or bypass of the certification adapter;
7. attempted formal write before `GPT_ACCEPTED_REAL_PRODUCTION_DURABLE_AUTHORITY_BINDING`.

The test oracle must not call an in-runtime issuer. Test evidence may use fixed public vectors only and must distinguish `SYNTHETIC_TEST_VECTOR` from a real external issuance. Heavy test matrices run remotely; local tests remain sequential, foreground-first, and keep task-owned Python at or below two processes.

## 7. Evidence, reporting, and rollback

Every executable phase will retain:

- source URL/API evidence classification, retrieval date, and counterevidence;
- selected/rejected reuse by exact path/blob/content hash rather than whole-branch import;
- deterministic public fixture seeds and mutation diffs/restoration evidence;
- exact tested head/parent/tree, CI run/job/artifact identifiers and content digests;
- cumulative AMED execution/research/improvement/discovery, WPDCR, UNKNOWN, approval, and handoff records.

Rollback is branch-local until a later, separately approved production control-plane deployment. Candidate packages remain unchanged and candidate-only. If a contract implementation is rejected, revert its branch commit; do not delete evidence, relax the formal-write gate, or rewrite history.

## 8. First implementation decision

The first substantive post-plan action is a read-only audit of the current authority, E47 candidate interface, and observable GitHub control plane, followed by a design decision record. It will not create an external provider or change repository settings. If that audit confirms the observed lack of protected external authority, the next implementation can safely build only the fail-closed contracts and a precise user-approval package.
