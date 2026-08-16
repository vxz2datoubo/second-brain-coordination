# R137 Authority-bound Live Observation Provider Architecture v1.0

Status: `GPT_ARCHITECTURE_CANDIDATE / PLANNING_ONLY / NOT_EXECUTABLE`

Issue: #358  
Owner: USER  
Architecture owner: GPT  
Predecessor canonical main at planning start: `16f158e1123fa6b52c1a489ddd53093a91270624`

## 1. Purpose

R136 deliberately fails closed when formal task release lacks a fresh `AuthorityBoundLiveObservationProof`. R137 supplies the first governed provider that can independently observe current public GitHub and coordination control-plane state and produce mechanism-backed evidence for that proof.

R137 is not a second Control Tower, a second Signal truth, a W3 authority, a domain authority, a merge authority, or a general network client.

Initial trust class:

`PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1`

## 2. Non-goals and hard boundaries

R137 v1 does not provide:

- malicious same-process Python code isolation;
- private-repository reads requiring credentials;
- generic URL fetch;
- daemon, watcher, webhook, scheduler or polling service;
- Harness runtime activation, H2 or H7;
- W3/private-chat ingestion or write;
- AI Film or any domain write;
- production service deployment;
- repository permission, secret, environment or branch-protection change;
- Formal Skill promotion;
- account/order/fund/trading capability.

The trusted-process boundary must be stated explicitly. Python underscore names, object identity and module-private registries are API integrity controls, not cryptographic protection from hostile same-process code.

## 3. Authority model

### 3.1 Caller authority

The caller may provide only an observation request:

- target repository from a canonical allowlist;
- expected branch, normally `main`;
- optional PR number;
- required canonical control-plane paths;
- required domain-freshness targets;
- expected task/route identity for binding;
- requested maximum evidence age within provider policy.

The caller may not supply trusted values for current main, PR head/base/state, review state, merge state, route, Work Claim, Program Lane, lease, pending approvals/revocations or domain freshness.

### 3.2 Provider authority

The provider is authorized only to observe and attest what it actually fetched. It cannot decide whether a review is sufficient, whether a task may execute, whether a Signal is satisfied, or whether a merge is allowed.

### 3.3 Control Tower authority

Control Tower remains the policy/authorization layer. It consumes an accepted provider proof plus the rest of the reconciliation state. A provider proof is necessary evidence, never execution authority by itself.

## 4. Provider components

### 4.1 `LiveObservationRequest`

Minimum fields:

- `request_id`
- `provider_contract_revision`
- `target_repository`
- `target_branch`
- `pull_request_number | null`
- `expected_task_id | null`
- `expected_route_epoch | null`
- `required_control_plane_paths[]`
- `required_domain_freshness_targets[]`
- `required_review_scope`
- `requested_max_age_seconds`
- `requested_at`

The provider rejects unknown repositories, paths, endpoint families or over-broad requests.

### 4.2 `LiveObservationEvidenceBundle`

The durable/public-safe mechanism evidence object must include at least:

- `provider_id`
- `provider_contract_revision`
- `provider_code_ref`
- `provider_code_digest`
- `observation_id`
- `request_id`
- `started_at`
- `completed_at`
- `github_api_version`
- `target_repository`
- `initial_main_sha`
- `final_main_sha`
- `main_tree_sha`
- exact canonical path/blob/content-digest records
- PR number/state/head/base/merged/merge-commit fields when applicable
- raw review observation records: review id/state/commit id/submitted_at/actor identity refs
- route fingerprint and exact route source identity
- Work Claim fingerprint and exact source identity
- Program Lane fingerprint and exact source identity
- lease/control-tower fingerprint and exact source identity
- domain freshness refs and exact source identities
- pending approval/revocation refs observed from canonical state
- request/response evidence metadata needed for attribution and completeness
- pagination completeness markers
- warnings and unknowns
- freshness policy and `fresh_until`
- invalidation keys
- canonical evidence-bundle digest

No raw private body may be persisted in this public repository.

### 4.3 Compact `AuthorityBoundLiveObservationProof`

The compact proof is derived only after the full evidence bundle validates. It binds the existing R136 interface fields and must additionally reference the evidence bundle identity/digest.

A compact proof without a valid mechanism-evidence bundle is `UNVERIFIED`.

## 5. GitHub observation transport

Initial transport is public, read-only, on-demand and serial.

Required properties:

1. Fixed `https://api.github.com` host and allowlisted endpoint templates only.
2. Explicit REST API version header. The planning reference version is `2026-03-10`; implementation must treat version as a contract input and regression surface, not an eternal constant.
3. No redirects.
4. Bounded timeout and response size.
5. Exact expected media type and UTF-8/JSON validation.
6. No generic caller-provided URL.
7. No credentials in v1. Public-only resources must remain usable without introducing secrets.
8. Requests are serial, not concurrent.
9. Pagination must be followed mechanically where an endpoint may paginate; incomplete pagination is a hard failure.
10. API errors, rate-limit ambiguity, 404 ambiguity or truncated/incomplete response are fail-closed.

Official design references:

- GitHub REST branch endpoint: https://docs.github.com/en/rest/branches/branches?apiVersion=2026-03-10
- GitHub REST pull requests: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2026-03-10
- GitHub REST pull request reviews: https://docs.github.com/en/rest/pulls/reviews?apiVersion=2026-03-10
- GitHub REST repository contents: https://docs.github.com/en/rest/repos/contents?apiVersion=2026-03-10
- GitHub REST best practices: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

## 6. Observation sequence and TOCTOU defense

Minimum serial sequence for a formal-task observation:

1. Read `main` branch and record `M0`.
2. Resolve commit/tree for `M0`.
3. Read all required canonical control-plane files at exact `M0`, not floating `main`.
4. If a PR is in scope, read PR state/head/base/merged/merge-commit.
5. Read all required PR review pages and bind each accepted raw record to its id/state/commit/time.
6. Read required domain-freshness targets by exact repo/ref/object identity.
7. Re-read `main` and require `M1 == M0`.
8. Re-read PR state/head/base/merged/merge-commit and require no material drift from step 4.
9. Verify all required surfaces are complete and no warning is material.
10. Emit evidence bundle.
11. Derive compact proof with bounded freshness.

Any drift produces `DRIFT_DETECTED / UNVERIFIED / BLOCKED` rather than a best-effort proof.

The provider must not infer that a review is acceptable merely because a review exists or because state text resembles `APPROVED`. It records evidence; Control Tower applies policy.

## 7. Freshness and invalidation

The provider contract must bind and invalidate on changes to at least:

- current main SHA;
- PR head SHA;
- PR base SHA;
- PR state;
- merged flag;
- merge commit SHA;
- review set/state/commit binding;
- route fingerprint;
- Work Claim fingerprint;
- Program Lane fingerprint;
- lease/control-tower fingerprint;
- domain freshness refs;
- pending approval/revocation refs;
- provider contract revision;
- provider code digest;
- evidence-bundle identity/digest.

TTL is policy-bounded. R137 architecture recommends a short formal-release freshness horizon, no more than five minutes by default, but implementation must keep the exact value in a versioned policy/contract and test expiry boundaries. A downstream release must still compare the expected task/route/claim/lane identities at use time.

## 8. Provider registration boundary

R136 currently contains a test-oriented verifier registry seam. R137 production must not expose a general caller API to register providers or verifiers.

V1 preferred pattern:

- one explicit provider id;
- one statically wired production verifier/adapter path under the authorized R137 module;
- test-only injection seam isolated to tests;
- provider identity and code digest bound into evidence;
- unknown provider ids fail closed.

If implementation requires a plugin registry later, that is a separate governed architecture decision.

## 9. Root-provider bootstrap ceremony

R137 cannot use itself as evidence for permission to create itself.

The one-time bootstrap protocol is:

### Phase A0 - architecture only

GPT publishes architecture, threat model, source selection and planning reconciliation. No active Codex route.

### Phase A1 - non-executable reservation

After Phase A0 is accepted and merged, GPT may publish:

- new R137 task id and route epoch;
- non-executable Work Claim;
- exact implementation allowlist;
- `ROOT_PROVIDER_BOOTSTRAP` reconciliation receipt generated from GPT direct GitHub connector observations of current main/control plane;
- expiry, revocation and one-time nonce/identity;
- `execution_allowed=false` until user release.

### Phase B - implementation

Only after explicit user and GPT release may Codex implement the provider. The bootstrap receipt authorizes only this bounded R137 implementation and cannot authorize another task.

### Phase C - provider acceptance and bootstrap retirement

After exact-head tests, independent GPT mechanism review and merge:

- bootstrap receipt becomes historical/consumed;
- bootstrap path must be disabled for ordinary tasks;
- regression proves it cannot be replayed;
- subsequent formal task release must use the accepted live provider.

This is a root-of-trust ceremony, not a bypass of Global Reconciliation.

## 10. Required validation matrix

At minimum:

1. valid public GitHub observation creates evidence bundle;
2. caller-filled compact proof fails;
3. caller cannot register production verifier;
4. wrong host fails;
5. redirect fails;
6. wrong media type fails;
7. oversized response fails;
8. malformed JSON fails;
9. branch identity mismatch fails;
10. commit/tree mismatch fails;
11. path substitution fails;
12. blob digest mismatch fails;
13. initial/final main drift fails;
14. PR head drift fails;
15. PR base drift fails;
16. PR state drift fails;
17. merged/merge-commit drift fails;
18. missing required review page fails;
19. review commit drift fails;
20. rejected/unknown review is not promoted to accepted policy;
21. route drift fails;
22. Work Claim drift fails;
23. Program Lane drift fails;
24. lease/control-tower drift fails;
25. domain freshness drift fails;
26. approval/revocation drift fails;
27. expired proof fails;
28. replay after invalidation fails;
29. provider code revision/digest drift fails;
30. unknown provider fails;
31. API rate-limit/transport ambiguity fails closed;
32. pagination incomplete fails closed;
33. public-only boundary rejects private/credential requirement;
34. no write endpoint exists;
35. no daemon/webhook/polling/scheduler exists;
36. no Control Tower/merge authority is granted;
37. R136 TaskRelease stays BLOCKED without provider;
38. R136 TaskRelease can consume a valid accepted-provider proof only after provider acceptance;
39. bootstrap receipt is task/epoch/scope/expiry bound;
40. bootstrap replay after retirement fails;
41. Python 3.11/3.13 exact-head CI;
42. placeholder/TODO/shadow/scope/public-safety audit;
43. bounded single-worker/resource cleanup;
44. rollback restores pre-R137 fail-closed behavior.

## 11. Source reuse rule

Historical frozen work is candidate source only. No whole PR/branch merge, cherry-pick or wholesale copy is authorized. Any reused path must be selected by exact source PR/head/path/blob identity, adapted to current R136 interfaces, reviewed for inherited defects and retested on the R137 exact head.

## 12. Exit criteria for architecture stage

Architecture stage is ready for a separate reservation decision only when:

- threat model is complete;
- source-selection ledger is exact-bound;
- current-main planning reconciliation is fresh;
- no active Codex lease exists;
- O0-O4 and permission/private/live boundaries are explicit;
- bootstrap ceremony is machine-checkable and non-reusable;
- implementation allowlist is bounded;
- no unresolved design issue can silently weaken provider provenance.

Until then: `NO R137 CODEX EXECUTION`.