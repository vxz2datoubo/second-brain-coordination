# AWS A1 IAM and OIDC Boundary

agent_id: `CODEX`

The GitHub requester is an OIDC-federated workload identity, not an approval authority. A future trust policy must bind only documented, supported GitHub/AWS claim conditions: the intended repository identity, exact workflow reference, `refs/heads/main`, audience, and the configured immutable subject form where available. It must not rely on invented AWS IAM condition keys.

The requester role's sole positive permission is invocation of the exact issuer boundary. It has no permission to create an approval, update a ledger, call KMS `Sign`, deploy or modify Lambda, alter IAM/KMS/DynamoDB policy, administer a key, or retrieve a secret. The issuer is separately permissioned to conditionally transition a pre-approved ledger record and request KMS signing of the canonical payload only.

The human AWS control identity is an activation-time external prerequisite with MFA; it is not represented by a repository credential, test fixture, or callable local API. Its approval record identifies exact digests, target, scope, expiry, nonce, and policy version. A second GitHub reviewer can add defense-in-depth but is not the independent authority claim.

AWS documents constraining GitHub OIDC trust to specific repository/branch identity values and recommends protected environments when environments are used: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html>.
