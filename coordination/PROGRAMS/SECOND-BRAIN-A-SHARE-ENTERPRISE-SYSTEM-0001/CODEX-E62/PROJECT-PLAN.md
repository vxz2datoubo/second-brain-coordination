# E62 Project Plan: AWS A1 Certification Authority and Private-Git Write Gate

agent_id: `CODEX`

## Goal and boundaries

E62 implements a PUBLIC_SAFE, deterministic candidate for AWS A1. It proves contracts, least-privilege templates, crash/retry behavior, verification, and a separate private-Git write gate without creating or modifying AWS, GitHub security controls, a private repository, credentials, or formal knowledge.

The current output must never be interpreted as a live authority. Every runtime path remains synthetic/local and fail-closed until a later exact activation route and independent GPT acceptance.

## Planned work packages

| Package | Deliverable | Validation | Boundary |
|---|---|---|---|
| Q0 | This plan-first commit and fresh E62 branch | Exact canonical parent; one plan file | No E61-lineage reuse or real control change |
| Q1 | AWS A1 contract, IAM/OIDC boundary, public-safe IaC | Static denial/allowlist assertions | No real AWS/GitHub configuration |
| Q2 | Approval/grant state machine | Crash/retry/concurrency/single-use tests | No real KMS call or ledger |
| Q3 | Typed E48 digest adapter | Reject legacy-short-hash-only input | E48 live bundle stays an explicit dependency |
| Q4 | Deterministic grant signer/verifier fixtures | Mutation/adversarial tests | No production key or external issuer |
| Q5 | Private-Git formal-write gate model | Grant consumption and expected-parent/CAS tests | No private repository or knowledge write |
| Q6 | Activation/cost/rollback package | Placeholder and permission review | User-only AWS/GitHub activation later |
| Q7 | Test, evidence, UNKNOWN and handoff records | Bounded local test run; public-safe report | Stop at GPT audit, no merge |

## Security model

The requester role can invoke exactly one issuer boundary and cannot create approvals, mutate arbitrary ledger records, sign directly, deploy code, alter IAM/KMS/Lambda/DynamoDB policy, administer keys, or retrieve secrets. A human MFA control identity is represented only as an external prerequisite and is never simulated as a caller-owned issuer.

Approval consumption and KMS signing are modeled as separate operations. Ambiguous sign outcomes enter a reconcilable state; they never cause blind re-signing. The private-Git gate consumes a verified grant independently, binds the expected parent, and rejects duplicate, revoked, expired, mismatched, or stale requests.

## E48 and private-Git interfaces

E62 accepts only `raw_artifact_sha256`, `canonical_semantic_sha256`, and `l0_provenance_sha256` as production digest inputs. The legacy E47 short hash is compatibility metadata only. E48 owns any canonical bundle production; E62 supplies a narrow adapter contract and uses public synthetic fixtures until that dependency exists.

`PRODUCTION_CERTIFICATION_AUTHORITY_BOUND` and `FORMAL_PRIVATE_GIT_WRITE_PATH_BOUND` are independent gates. The future private Git repository is not created or named here; formal persistence remains disabled until both gates and GPT acceptance are complete.

## Anticipated difficulties and stop conditions

- Cross-service crash windows make exactly-once issuance impossible to assume; the model must prefer explicit reconciliation and deny duplicate consumable grants.
- AWS OIDC claim support and IAM conditions must reflect official documentation, not invented condition keys.
- The missing E48 full-digest producer is an interface UNKNOWN, not an excuse to broaden into QCLAW work.
- Any real AWS account/billing/IAM/KMS/Lambda/DynamoDB, GitHub OIDC/environment/ruleset/protection, secret/key, private repository, merge, or formal-write operation is an immediate user/GPT gate.

## Completion evidence

E62 will publish a Draft PR with exact head, changed-file list, contract/state-machine/verifier/IaC/test evidence, resource postflight, E48 dependency state, private-Git gate evidence, and `CODEX_E62_AWS_A1_CERTIFICATION_AND_PRIVATE_GIT_WRITE_GATE_IMPLEMENTATION_READY_FOR_GPT_REVIEW`.
