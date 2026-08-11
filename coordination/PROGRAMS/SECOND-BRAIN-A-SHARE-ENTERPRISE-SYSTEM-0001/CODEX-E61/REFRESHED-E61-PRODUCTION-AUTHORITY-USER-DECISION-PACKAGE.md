# Refreshed E61 Production-Authority User Decision Package

agent_id: `CODEX`

## Status and decision requested

**Status:** `USER_APPROVAL_REQUIRED`; this is a read-only refresh under route epoch 66. No repository setting, environment, ruleset, OIDC configuration, GitHub App, external service, secret, key, permission, or formal knowledge write was changed.

The decision is whether to establish a genuinely independent production certification authority for future formal `PROJECT`/`GLOBAL` knowledge writes. Declining or deferring it is safe: E47 and E48 remain candidate/derived only, and E61 continues to fail closed with `EXTERNAL_AUTHORITY_NOT_CONFIGURED`.

## Refreshed facts

| Surface | Read-only observation | Consequence |
|---|---|---|
| Canonical route | `origin/main` `e3b03c6096a3a7e981004088ac72abf3b51549e1`, E61 epoch 66 | This package supersedes the coarse prior request; it does not rebase PR #210. |
| Branch control | `main` protection endpoint returns `404`; ruleset count is zero | A repository ref is not an independent authority boundary. |
| Deployment control | Environment count is zero | No reviewer-gated certification route exists. |
| OIDC | Default subject template; `use_immutable_subject: false` | A future provider must not assume immutable subject binding until it is explicitly enabled and validated. |
| Independent review | Direct collaborator count is one | No independently verifiable environment reviewer is currently available. |
| E47 input | Accepted PR #207 head `476d2a287cffb084c01b54c1d5e5eaf22016aac7` has exact spans and a full `source_hash`, but a 16-character `content_hash` | Certification must require full raw-package, canonical-semantic, and L0-source/provenance SHA-256 values. |
| E48 pipeline | L0 raw -> L1 normalized -> L2 candidate atoms -> L3 graph projection | Only immutable L0 and an L2 package with complete provenance can be candidates; L1/L3 remain derived and are never authority. |

## Three control-plane families

### A. Protected GitHub environment + OIDC + independently operated issuer/verifier and single-use ledger — recommended minimum viable design

GitHub Actions supplies short-lived workload identity. A protected `knowledge-certification` environment and protected certification workflow narrow when that identity can be minted. An independently operated issuer/verifier validates fixed GitHub OIDC claims, verifies all full candidate digests, records a single-use grant in a ledger outside ordinary repository caller code, and returns a short-lived scope-bound certification result. The local adapter only verifies and consumes that result.

**What ordinary Codex/QCLAW cannot mint:** the issuer identity, issuer signing key, ledger entry, revocation state, independent deployment approval, or an accepted grant outside the allowed workflow/environment/ref/subject policy.

**Required manual/user changes:** protect the authority-policy and workflow paths; create the environment; establish a genuinely distinct reviewer and prevent self-review; restrict deployments to `main`; prohibit bypass where available; opt in to immutable OIDC subject claims after the external trust policy is ready; select the independent issuer/ledger owner and configure its trust policy outside this repository.

**Secrets and cost:** no secret belongs in this repository. The selected external operator owns any key/KMS/ledger credentials. Cost and maintenance depend on the chosen operator; budget, retention, revocation on-call, and service ownership must be selected before activation.

**Failure, replay, revocation, rollback:** fail closed on unavailable issuer, wrong claim, expired grant, duplicate nonce, or revoked policy. The ledger consumes the grant once. Rollback disables the environment/workflow route and revokes the external policy; it does not delete candidates or assert retroactive writes.

**Why this meets E61 if configured:** the durable issuer and single-use state are external to ordinary caller code, while GitHub controls are supporting admission constraints rather than the sole trust root.

### B. Independently controlled GitHub App deployment-protection service — viable but higher operational burden

A separately administered GitHub App can act as a custom deployment protection rule. It receives deployment protection events, independently evaluates a candidate request, and approves/rejects the deployment. It can host or call the issuer/ledger in a separately controlled service.

**What ordinary callers cannot mint:** the App private identity, installation authority, externally hosted policy decision, and service-side replay/revocation state, provided those remain outside the ordinary caller path.

**Manual/user changes:** register/install an App, establish its externally managed private-key lifecycle and webhook verification, create and protect an environment, enable the custom rule, and host/operate the rule service. This is a high-risk operational change and is not approved by this package.

**Cost/maintenance:** highest of the three: App lifecycle, key rotation, hosted endpoint availability, webhook validation, incident response, and ledger operation. Rollback disables the rule/environment and revokes the App installation or service policy.

**Assessment:** can satisfy E61, but is not minimum complexity unless an existing independently operated App/service is already approved and available.

### C. GitHub artifact attestations / Sigstore keyless provenance — evidence supplement only

GitHub artifact attestations and Sigstore can bind an artifact digest to build provenance and a workflow identity. That is useful evidence for the future issuer/verifier to verify.

**What it does not supply by itself:** a distinct business authorization actor, an externally controlled formal-write capability, policy-specific one-time consumption, revocation state for certification grants, or a protected formal-store write path. An attestation therefore cannot itself authorize a `PROJECT` or `GLOBAL` write.

**Cost/maintenance:** low when used as provenance evidence; verification policy and artifact retention still require ownership. Rollback is to stop accepting the evidence as a provider input. It remains an optional supplement to A or B, not a substitute.

## Recommendation

Choose **A** only if the user can designate an independently operated issuer/verifier and a genuinely independent reviewer/control identity. It has the lowest added complexity that still separates issuance, replay state, and revocation from ordinary repository callers. Use attestations from **C** as optional additional evidence. Choose **B** only when an independently operated GitHub App/protection service is already justified; do not create one merely to add complexity.

## Exact approval checklist

1. Approve or reject family A as the target architecture.
2. Approve a distinct, independently administered reviewer/control identity; without it, required-reviewer controls do not demonstrate independent review.
3. Approve protected `main` ruleset/branch controls for the certification workflow and authority-policy paths.
4. Approve a `knowledge-certification` environment restricted to `main`, with required independent review, self-review prevention, and bypass disabled where available.
5. Select an independent issuer/verifier and ledger owner; approve its bounded trust policy, lifecycle responsibility, cost budget, revocation owner, and incident/rollback contact.
6. Approve immutable OIDC subject customization only after the provider trust condition is ready to accept it.

This checklist does **not** request any password, token, private key, API secret, cookie, account credential, formal-write unlock, market access, or trading capability.

## Official-source basis

- GitHub documents that environments can require reviewers, prevent self-review, restrict deployment refs, and block bypass; these controls are available for public repositories but create no independent signer by themselves: <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>.
- GitHub documents that OIDC provides job-unique, short-lived tokens whose claims must be checked by the external provider: <https://docs.github.com/en/actions/concepts/security/openid-connect>.
- GitHub documents immutable OIDC subject claims and the opt-in path for older repositories: <https://docs.github.com/en/actions/reference/security/oidc>.
- GitHub documents custom deployment protection rules as GitHub-App-powered and presently previewed: <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/configure-custom-protection-rules>.
- GitHub states artifact attestations provide provenance but must be verified and are not themselves a security guarantee: <https://docs.github.com/en/actions/concepts/security/artifact-attestations>.
- Sigstore describes signing/verification evidence; it does not replace the authorization, single-use, or formal-write policy above: <https://docs.sigstore.dev/cosign/signing/overview/>.

## No-change alternative

Do nothing now: retain E47 packages as `CANDIDATE_ONLY`, retain E48 L1/L3 as derived views, implement no external provider, make no repository changes, and keep all formal writes disabled. This is fully reversible and preserves existing evidence while preventing self-issuance.
