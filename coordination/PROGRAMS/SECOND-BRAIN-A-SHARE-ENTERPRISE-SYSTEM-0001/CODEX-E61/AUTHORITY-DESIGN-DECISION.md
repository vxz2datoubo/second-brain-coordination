# E61 Authority Design Decision

## Decision

E61 selects, subject to explicit user approval, **a protected GitHub deployment environment plus GitHub Actions OIDC federation to an externally operated certification issuer/verifier**.

The selected issuer must be outside normal repository caller code and retain its own public-key identity, replay/single-use ledger, revocation state, and formal-write capability policy. GitHub Actions is evidence and authenticated workload identity; it is not the issuer of record.

**Status:** `DESIGN_SELECTED_CONFIGURATION_NOT_APPROVED`.

## Evidence and rationale

GitHub documents that OIDC makes a short-lived token available per workflow job and that an external cloud provider can validate the token's claims before issuing a job-scoped credential. The documented claim set can bind repository, ref, SHA, workflow, environment, actor, run, and audience conditions. GitHub also documents environment-level required reviewers, self-review prevention, branch restrictions, and administrator-bypass controls.

- [OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)
- [OIDC deployment hardening](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers)
- [Deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

The actual repository currently has no protected `main`, no environment, and a default/non-immutable OIDC subject. Therefore the design is not configured and cannot issue anything today.

## Design comparison

| Design | External to ordinary caller? | What it proves | Missing control | Decision |
|---|---|---|---|---|
| A. Protected environment + OIDC -> external issuer/verifier | Yes, if environment, ref restrictions, OIDC trust, and issuer service are independently administered. | Authenticated workflow identity plus an issuer-controlled single-use capability. | Requires user-approved repository controls and external service configuration. | **Selected target.** |
| B. Protected environment + GitHub App deployment-protection service | Yes, if the App is independently hosted and its key/installation are outside caller control. | Human/deployment gate plus App-controlled policy decision. | Adds App registration, installation, private-key lifecycle, and protection-rule configuration. | Viable fallback; higher operational/key-management burden. |
| C. Artifact attestation alone | Partially. | Build provenance for an artifact digest. | No independent revocation, single-use issuance, or formal-write capability. | Evidence supplement only. |
| D. Repository-local signer, fixture, env var, or private import | No. | At most local test behavior. | Caller can self-issue or substitute. | Rejected. |

## Required production contract

The approved provider must issue a `ProductionCertificationGrant` only after it has verified all of the following:

1. GitHub OIDC issuer/audience/signature and immutable repository identity;
2. protected `main` ref, approved workflow identity and SHA, approved environment, deployment approval actor/reference, and run identity;
3. a full candidate raw-artifact SHA-256, full canonical-semantic SHA-256, full source/provenance SHA-256, and the E47 legacy short hash only as a consistency field;
4. requested `PROJECT` or `GLOBAL` scope, target identity, provider policy version, issue/expiry times, nonce/grant identifier, revocation epoch, and single-use ledger entry;
5. exact production verifier identity and a non-caller-controlled signing/verification key path.

The local adapter may verify a provider-issued public artifact and request a future formal write. It may not issue grants, alter candidate content, choose provider keys, or write before the independent GPT acceptance gate.

## Consequences and rollback

Until the controls exist, every certification attempt must return `EXTERNAL_AUTHORITY_NOT_CONFIGURED`; this is the intended fail-closed behavior. E47 remains candidate-only. No secret, key, GitHub App, environment, ruleset, external service, or formal-store connection is created by this decision.

If the user declines or later revokes the external service/control-plane arrangement, disable the environment/workflow route and revoke the external issuer policy. No candidate package is deleted and no formal write is retroactively asserted.
