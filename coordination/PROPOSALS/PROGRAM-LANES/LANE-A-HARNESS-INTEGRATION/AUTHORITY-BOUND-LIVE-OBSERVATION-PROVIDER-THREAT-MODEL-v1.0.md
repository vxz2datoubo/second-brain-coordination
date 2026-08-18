# R137 Authority-bound Live Observation Provider Threat Model v1.0

Status: `GPT_ARCHITECTURE_CANDIDATE / FAIL_CLOSED`

Issue: #358

## 1. Protected decision

The protected decision is not “is GitHub reachable?” It is whether a downstream Global Reconciliation / TaskRelease process may rely on a specific observation as fresh evidence of current repository and control-plane state.

Security goal:

> No caller-authored, stale, partial, drifted or ambiguously observed GitHub/control-plane state may be promoted into a valid `AuthorityBoundLiveObservationProof`.

## 2. Trust boundary

V1 trust class: `PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1`.

Trusted:
- checked-out R137 provider code at an exact accepted commit;
- provider's fixed endpoint/allowlist logic;
- GitHub HTTPS API response reached through the provider's bounded transport;
- exact object identity checks and deterministic parser inside the trusted process;
- Control Tower's separate policy interpretation.

Not cryptographically trusted against:
- arbitrary malicious Python code already executing in the same process and able to monkeypatch module state;
- compromised OS/runtime/network root trust;
- compromised GitHub itself.

The implementation must not disguise this limitation with underscore variables, object seals or an in-memory registry and call that cryptographic isolation.

## 3. Assets

- current `main` identity;
- current PR state/head/base/merge state;
- exact review evidence;
- exact canonical route;
- Work Claim;
- Program Lane;
- Control Tower/lease state;
- domain freshness identities;
- pending approvals/revocations;
- provider code revision;
- evidence bundle/proof lineage;
- freshness and invalidation semantics.

## 4. Threats and mandatory responses

| ID | Threat | Example | Required response |
|---|---|---|---|
| T01 | Caller self-certification | caller fills a perfect-looking proof dataclass | reject unless provider mechanism evidence validates |
| T02 | Mutable provider registry | caller registers a verifier that always returns true | no caller-accessible production registration path |
| T03 | Forged provider attribution | fake `provider://...` string | attribution must bind accepted provider id/code/evidence bundle |
| T04 | Replay | yesterday's valid proof reused | TTL + invalidation + current target binding; expired/replayed proof BLOCKED |
| T05 | Stale main | provider reads old main | first/final main re-read; exact commit binding |
| T06 | PR head/base drift | code changes after observation | final PR re-read; mismatch BLOCKED |
| T07 | PR merge-state drift | unmerged becomes merged or vice versa | merged + merge_commit in invalidation set |
| T08 | Review drift | review state/commit changes | bind review ids/states/commit ids/times and re-evaluate freshness |
| T09 | Review semantic overreach | any review object counted as approval | provider records raw state only; Control Tower decides policy |
| T10 | Route drift | ACTIVE task/route changes | exact file at exact main + fingerprint invalidation |
| T11 | Work Claim drift | lease surface changes | exact claim object/fingerprint invalidation |
| T12 | Program Lane drift | lane state changes | exact lane object/fingerprint invalidation |
| T13 | Lease expiry/change | execution lease no longer valid | exact lease/control-tower fingerprint invalidation |
| T14 | Domain freshness drift | AI Film or other domain head changes | exact domain authority ref/commit/blob binding |
| T15 | Approval/revocation drift | approval revoked after observation | bind pending/current approval and revocation refs |
| T16 | TOCTOU | state changes during multi-call observation | serial snapshot protocol + final rechecks |
| T17 | Partial pagination | only first review page fetched | page/link completeness required or BLOCKED |
| T18 | 404 ambiguity | absent vs unauthorized vs transient | no optimistic interpretation; UNKNOWN/BLOCKED |
| T19 | Rate limit/transport ambiguity | 403/429/5xx | UNKNOWN/BLOCKED; no stale fallback as PASS |
| T20 | Redirect/host confusion | API redirects to another host | reject redirects; exact host/scheme |
| T21 | Oversized payload | resource exhaustion | strict byte ceilings |
| T22 | Media/type confusion | HTML returned instead of JSON | strict expected media and schema |
| T23 | JSON ambiguity | malformed/unexpected object shape | strict parse + closed schema checks |
| T24 | Path substitution | same filename from wrong tree | resolve exact commit tree/path/blob |
| T25 | Blob substitution | returned content differs from blob id | recompute Git blob identity/content digest |
| T26 | Provider code drift | proof produced by unexpected code version | provider code ref/digest in bundle/invalidation |
| T27 | Evidence truncation | proof omits one required surface | completeness map; missing required field => BLOCKED |
| T28 | Private data leakage | private chat/body copied into public evidence | public-safe metadata/digests only; private body forbidden |
| T29 | Credential creep | implementation adds token/secret for private repos | stop and require separate user permission architecture gate |
| T30 | Write-capability creep | provider can PATCH/POST/merge | no write endpoint/client method in v1 |
| T31 | Continuous-monitor creep | daemon/polling/webhook introduced | forbidden; on-demand invocation only |
| T32 | Authority creep | provider decides merge/release | forbidden; evidence only |
| T33 | Same-process monkeypatch | hostile code changes verifier registry | outside V1 cryptographic guarantee; no false claim; later external attestor gate if required |
| T34 | Provider compromise | accepted provider emits false evidence | independent exact-head tests, source provenance, evidence digest, bounded authority; downstream challenge remains possible |
| T35 | Bootstrap circularity | provider authorizes its own creation | one-time GPT root bootstrap using direct connector observation, never provider self-proof |
| T36 | Bootstrap replay | R137 bootstrap reused for R138 | task/epoch/scope/expiry/nonce bind + consumed/retired state |
| T37 | Frozen-source contamination | wholesale merge old provider branch | exact path/blob source selection only; adapt and retest |
| T38 | Resource explosion | concurrent requests/process pools | serial HTTP, one worker default, no nested pools |

## 5. Failure taxonomy

The implementation should preserve typed reasons rather than one generic false:

- `PROVIDER_NOT_AVAILABLE`
- `PROVIDER_NOT_ACCEPTED`
- `TARGET_NOT_ALLOWLISTED`
- `TRANSPORT_UNAVAILABLE`
- `RATE_LIMIT_OR_REMOTE_AMBIGUITY`
- `REDIRECT_REJECTED`
- `UNEXPECTED_MEDIA_TYPE`
- `RESPONSE_OVERSIZED`
- `INVALID_JSON_OR_SCHEMA`
- `PAGINATION_INCOMPLETE`
- `OBJECT_IDENTITY_MISMATCH`
- `BLOB_CONTENT_MISMATCH`
- `MAIN_DRIFT`
- `PR_DRIFT`
- `REVIEW_DRIFT`
- `CONTROL_PLANE_DRIFT`
- `DOMAIN_FRESHNESS_DRIFT`
- `EVIDENCE_INCOMPLETE`
- `PROOF_EXPIRED`
- `PROOF_REPLAY_OR_INVALIDATED`
- `PROVIDER_CODE_DRIFT`
- `PRIVATE_OR_CREDENTIAL_SCOPE_REQUIRED`
- `BOOTSTRAP_NOT_AUTHORIZED`
- `BOOTSTRAP_CONSUMED_OR_EXPIRED`

All material failures resolve to `UNVERIFIED/BLOCKED`, never synthetic PASS.

## 6. Bootstrap threat controls

The R137 bootstrap receipt must bind:

- R137 unique task id;
- route epoch 137;
- exact current main after architecture merge;
- exact architecture/source-selection/threat-model blobs;
- exact future implementation allowlist;
- exact Work Claim reservation;
- explicit user/GPT release ref;
- issue #358 or successor implementation issue identity;
- issued_at and expires_at;
- nonce/receipt id;
- one-time consumption state;
- revocation rule;
- no successor authority.

A bootstrap receipt must never be accepted by ordinary `AuthorityBoundLiveObservationProof` validation.

## 7. Residual risks

### R1 malicious same-process code

Severity: HIGH if hostile code is assumed inside provider process.  
V1 disposition: `OUTSIDE_TRUST_CLASS / EXPLICIT_LIMITATION`.

Conservative measure: provider remains public-read-only and cannot directly execute or merge. If cryptographic separation becomes required, design an external attestor/signer or isolated service under a new user-approved security/secret/permission gate.

### R2 public unauthenticated GitHub rate limits

Severity: MEDIUM operational availability risk.  
Disposition: fail closed. No automatic token introduction. Authentication/private access requires a later explicit permission/secret decision.

### R3 GitHub API contract/version change

Severity: MEDIUM.  
Disposition: versioned header, schema tests, explicit UNKNOWN/BLOCKED on unexpected response.

### R4 stale proof inside short TTL

Severity: MEDIUM.  
Disposition: invalidate on known state keys and rebind expected task/route at consumption. High-risk release may request an even shorter freshness policy.

## 8. Security acceptance rule

R137 cannot be called a trusted provider merely because tests are green. Acceptance requires:

- exact source provenance;
- exact-head dual-Python CI;
- adversarial drift/replay/forgery tests;
- independent GPT code/mechanism review;
- proof that production has no caller registration/self-issuance bypass;
- proof that bootstrap cannot be replayed;
- proof that no write/private/secret/daemon authority was introduced;
- explicit scope-limited user/GPT approval before implementation and before merge.