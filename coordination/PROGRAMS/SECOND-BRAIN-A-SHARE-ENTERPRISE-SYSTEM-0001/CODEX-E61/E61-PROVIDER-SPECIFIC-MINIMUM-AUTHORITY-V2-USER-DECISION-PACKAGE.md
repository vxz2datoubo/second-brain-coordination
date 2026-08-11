# E61 Provider-Specific Minimum Authority V2: User Decision Package

agent_id: `CODEX`

## The one decision

After GPT reviews this package, choose one:

1. **APPROVE_RECOMMENDED_ARCHITECTURE** — authorize a later, separately routed implementation of **AWS A1: serverless external human-preapproval authority**; or
2. **DEFER_AND_REMAIN_CANDIDATE_ONLY** — make no cloud or repository change and retain the present fail-closed state.

This is a design-only document. No AWS/GCP account, billing profile, GitHub setting, environment, ruleset, OIDC policy, App, secret, key, permission, repository, or formal write was created or changed.

## Recommendation: AWS A1

### What it is

AWS A1 uses GitHub Actions OIDC only as a limited requester identity. It is **not** trusted to create approvals, issue grants, sign directly, deploy issuer code, alter IAM/KMS/Lambda policy, or mutate arbitrary ledger records.

The independent authority is a separate human AWS control identity/session protected by MFA and unavailable to Codex, QCLAW, and ordinary workflow callers. That human pre-approves one exact certification request. A narrow issuer Lambda then atomically consumes the pre-approval in DynamoDB and asks an asymmetric AWS KMS key to sign an exact `ProductionCertificationGrant`.

```text
human AWS MFA control identity
  -> creates exact one-use approval record
GitHub Actions OIDC requester role
  -> InvokeFunction only
issuer Lambda
  -> conditional DynamoDB consume + KMS Sign
  -> scope-bound, expiring grant
future private-Git write path
  -> not part of this stage; remains disabled
```

### Why ordinary callers cannot self-issue

- The GitHub OIDC trust policy must bind the immutable repository identity, exact `main` ref, named certification workflow, audience, and protected environment where enabled. AWS recommends limiting the GitHub OIDC `sub` condition to specific repository/branch values rather than allowing broad identities.
- The requester role gets only `lambda:InvokeFunction` for the one issuer function. It receives **no** `dynamodb:PutItem` approval permission, no KMS `Sign`, no IAM/KMS/Lambda deploy or policy mutation, and no permission to create a pre-approval.
- The Lambda itself only accepts a validated request with a complete digest bundle, uses a conditional update to consume an already-approved record once, and signs only the matched scope/target/expiry/nonce grant.
- A human pre-approval record contains the exact raw-artifact SHA-256, canonical-semantic SHA-256, L0 provenance SHA-256, candidate package identifier, requested scope, target, expiry, nonce/grant ID, and policy version. The legacy E47 16-character compatibility hash may be carried but can never authorize alone.
- Crash/retry behavior is fail-closed: the conditional ledger transition is idempotent for the same request ID and rejects a second grant after consumption. Issuer timeout, KMS denial, unexpected digest, expired approval, or unknown state creates no grant.

### Does this require a second GitHub reviewer/account?

**No, not for the primary independence claim.** The separate human AWS MFA identity is the approval authority outside the ordinary caller path. A GitHub protected environment, required reviewer, self-review prevention, ref restriction, and no-bypass policy are valuable defense-in-depth when later approved, but the current single-collaborator observation means they cannot be presented as the only independent boundary. A distinct GitHub reviewer can be added later if one is genuinely independently administered; a cosmetic second identity is not security.

### User prerequisites and manual setup after a later approval

1. Create or use an AWS account with billing enabled; enable MFA for the human control identity. This identity must stay unavailable to agents and workflow callers.
2. Choose one AWS Region and an owner responsible for billing, revocation, and incident response.
3. Create one asymmetric KMS signing key, one DynamoDB approval/consumption table, and one issuer Lambda. Keep KMS key administration and Lambda/IAM deployment out of the requester role.
4. Configure GitHub OIDC federation to an invoker-only AWS role constrained to the exact repository/ref/workflow/audience and immutable identity policy supported by the configured GitHub OIDC subject.
5. Configure later-approved GitHub supporting controls (protected certification workflow path; optional protected environment restricted to `main`; no bypass where available). None of these are authorized by this document.
6. Have the human control identity create a small number of explicit approval records and test reject/retry/revocation cases before any formal store path is enabled.

Codex can later write and test public-safe workflow, verifier, request-schema, and fail-closed adapter code only after a new route authorizes it. The user or the designated AWS owner must personally perform all account, payment, MFA, IAM, KMS, Lambda, DynamoDB, and GitHub security-control actions.

### Estimated low-volume cost and maintenance

**Assumptions:** one AWS Region, one customer-managed asymmetric KMS key, a tiny number of grants/month, short Lambda invocations, small DynamoDB records, and no provisioned concurrency, API Gateway, NAT gateway, cross-region replication, backups/PITR, or unusual logging retention. Prices are USD list prices and region/account taxes or related services can change the estimate.

| Component | Low-volume estimate | Basis |
|---|---:|---|
| KMS asymmetric key | about **USD 1.00/month** | AWS lists USD 1/month per KMS key. |
| KMS signing | about **USD 0.15 per 10,000 signs** | AWS file-signing example uses this rate; at tiny volume it is negligible but not in KMS free-tier operations. |
| Lambda | likely USD 0 within free tier | AWS lists 1 million requests and 400,000 GB-seconds/month free. |
| DynamoDB ledger | likely USD 0 within free tier for a tiny table | AWS lists a provisioned free tier including 25 RCUs, 25 WCUs, and 25 GB. Choose capacity/mode deliberately; backups and optional features may cost more. |
| Logging/network/other | **not included** | avoid NAT/API Gateway/retention expansion unless separately justified. |

The practical baseline estimate is therefore **about USD 1/month plus negligible per-sign usage**, subject to Region, taxes, billing rules, and any optional AWS services. Maintenance is non-zero: approve/expire/revoke records, monitor issuer failures, rotate/review policy, test restore/rollback, and retain an operational owner.

### Revocation, rollback, and remaining blocks

Revoke by disabling the KMS key or issuer role/policy, stopping future approvals, and marking outstanding approvals/grants revoked in the ledger. Rollback removes the certification workflow's ability to invoke the issuer and leaves candidates untouched. No previously signed grant permits a write after expiry/revocation checks fail.

This stage does **not** enable formal persistence. It establishes only the design for `PRODUCTION_CERTIFICATION_AUTHORITY_BOUND`.

## Comparison: Google Cloud A2

Google Cloud A2 uses Workload Identity Federation to turn GitHub OIDC into an invoker-only principal for Cloud Run or a function. A separate human Google Cloud identity with MFA creates approval state; the issuer transactionally consumes Firestore state and invokes Cloud KMS. The GitHub principal must not create approvals, deploy the service, alter IAM/KMS policy, or sign directly.

| Dimension | A2 observation |
|---|---|
| Trust root | Human Google Cloud control identity + Cloud IAM/KMS/transactional approval record. |
| Non-self-issuance | Feasible if Workload Identity attribute conditions limit GitHub identity and IAM is invoker-only. |
| Account/billing | Billing is required for Cloud KMS. Cloud Run pricing/free quota depends on Region and billing configuration; Firestore offers a free quota but paid features require billing. |
| Low-volume estimate | One software KMS key version is about **USD 0.06/month**; cryptographic operations are USD 0.03/10,000. Cloud Run's published free tier is likely adequate at tiny volume; Firestore's one free database has daily read/write/storage quotas. |
| Setup/maintenance | More control-plane surfaces: Cloud project/billing, WIF pool/provider/attribute conditions, IAM, Cloud Run/function, Firestore, KMS, human approval path, logging and revocation. |
| Rollback | Disable the WIF principal/service invoker binding, revoke approval policy/key, and leave candidates unchanged. |

**Assessment:** lower KMS list-price baseline than AWS, but more unfamiliar services and billing/project setup for this repository. It is viable, but not recommended as the first minimum-complexity path unless the user already has an independently administered Google Cloud control plane.

## Comparison: GitHub App deployment-protection service B

An independently hosted GitHub App can operate a custom deployment protection rule and call an external ledger/issuer. It can satisfy E61 only if App private-key lifecycle, webhook verification, hosting, approval policy, revocation, and single-use state are independently controlled.

It requires App registration/installation, a private key held outside the repository, a publicly reachable and maintained webhook endpoint, deployment-environment configuration, and service operation. This is more operational work than AWS A1 and adds App-key and webhook attack surfaces. Do not choose it unless an independently operated App/service already exists and provides a clear advantage.

## Provenance-only evidence

GitHub artifact attestations/Sigstore can provide cryptographically verifiable build provenance and may be verified by the issuer as a supporting input. They do **not** independently create human pre-approval, single-use consumption, revocation for the certification grant, or a formal private-Git write capability. They remain evidence supplements, never the authority on their own.

## Formal private-Git write boundary

Phase-0 declares approved knowledge packets, atoms, relations, and skills authoritative only in a **future private Git knowledge repository**. The current repository and Supabase/local serving are not that authority.

Therefore E61 V2 deliberately separates two conditions:

1. `PRODUCTION_CERTIFICATION_AUTHORITY_BOUND`: a later approved AWS A1-style issuer can issue and verify a one-use certification grant.
2. `FORMAL_PRIVATE_GIT_WRITE_PATH_BOUND`: a separate routed task must bind that exact verified grant to a named private Git repository, least-privilege write identity, protected target ref, immutable receipt topology, commit/path policy, and rejection/revocation behavior.

Formal `PROJECT`/`GLOBAL` persistence remains disabled until **both** conditions and the independent GPT acceptance gate are satisfied. The full digest bundle is a cross-agent E48/QCLAW engineering requirement, not a user choice.

## No-change alternative

Choose defer: no account, billing, repository, provider, key, policy, or workflow change. E47 stays `CANDIDATE_ONLY`; E48 L1/L3 stay derived; all certification attempts return `EXTERNAL_AUTHORITY_NOT_CONFIGURED`; formal persistence remains disabled. This is safe, reversible, and does not discard candidate evidence.

## Official-source basis

- AWS recommends constraining GitHub OIDC role trust policies to specific repository/branch identities and protecting environments: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html>.
- AWS KMS lists USD 1/month per key and its file-signing example lists USD 0.15/10,000 signs: <https://aws.amazon.com/kms/pricing/>.
- AWS Lambda lists 1 million requests and 400,000 GB-seconds/month in its free tier: <https://aws.amazon.com/lambda/pricing/>.
- AWS DynamoDB lists its provisioned free-tier capacity and storage: <https://aws.amazon.com/dynamodb/pricing/>.
- Google documents Workload Identity Federation for GitHub and recommends restricting federated identity access with attributes/conditions: <https://cloud.google.com/iam/docs/workload-identity-federation>.
- Google Cloud KMS lists software key-version and cryptographic-operation prices and says billing is required: <https://cloud.google.com/kms/pricing>.
- Cloud Run lists its free CPU/RAM quotas and region/billing dependence: <https://cloud.google.com/run/pricing>.
- Cloud Firestore documents its free quota and that more quota requires billing: <https://firebase.google.com/docs/firestore/pricing>.
