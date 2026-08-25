# R150 Trusted Task-Release Observation Binding

Status: `IMPLEMENTED_CANDIDATE / INDEPENDENT_REVIEW_REQUIRED`

Issue: `#454`

Base canonical main: `a9c47fa037f0c4e41848dee7adfad09f1aee3fd5`

Branch: `gpt/r150-trusted-task-release-observation-binding`

## Purpose

R149 Slice 1 deliberately accepts caller-supplied current-state fields only as contract/eval fixtures. R150 adds a narrow repository-bound materialization seam so a future governed Task-release decision can use current Control Tower state and an existing R145 domain-authority result instead of trusting caller claims about the present system.

R150 extends R149. It does not create a second Control Tower, active-work registry, domain resolver, live-observation provider, Task authority or release store.

## Flow

`TaskReleaseProposal/v1`
→ exact coordinator checkout binding
→ `control_tower.scan_repository`
→ `lane_claims.validate_claims`
→ canonical active/reserved claim materialization
→ existing R145 `resolve_candidate_domain_authority`
→ existing R145 Signal/Task/Route/writeback domain guard
→ existing R149 `evaluate_release_candidate`
→ `TrustedTaskReleaseImpactReceipt/v1`

The outer receipt is evidence only. Its nested R149 receipt remains `TaskReleaseImpactReceipt/v1`.

## Caller boundary

Caller may describe intent, desired effect, proposed write surface, capability reuse analysis, dependency/consumer analysis, composition decision and bounded change sets.

Caller may not provide:
- current observations;
- current active work items;
- authority compatibility;
- collision result;
- final disposition;
- trusted context.

Those fields are materialized by R150 or computed by existing R149/R145 logic.

## Trusted observations

R150 binds:
- exact local Git `HEAD` against an expected coordinator main supplied by the governed invocation;
- clean worktree before and after evaluation;
- exact Git blob identities for canonical Work Claims, GPT worker registry and Program Control Tower projection;
- full `control_tower.scan_repository` error state;
- canonical `lane_claims.validate_claims` result;
- active/reserved Work Claim surfaces only;
- a process-local `VerifiedR145DomainBinding` minted only by calling the existing R145 resolver.

No raw caller mapping can mint the R145 binding capability.

## Active work semantics

Only `ACTIVE_IMPLEMENTATION` and `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` claims become current collision inputs. `CLOSED_NO_ACTIVE_IMPLEMENTATION` claims retain history but contribute no current collision surface.

The existing R149 evaluator still owns O0-O4 collision behavior by reusing `control_tower.classify_collision`.

## Domain semantics

R150 does not invent domain truth.

`VerifiedR145DomainBinding` is only an authenticated process-local wrapper over an accepted result from the existing R145 `resolve_candidate_domain_authority` function. Non-legacy domains still require the same exact-read, semantic-authority and live-observation proof chain that R145 already requires.

The R145 compatibility guard evaluates Signal primary domain, proposed Task target domain, resolved authority domain and writeback-domain identity. A mismatch fails closed before any later normal release gate.

## Authority lock

`TrustedTaskReleaseImpactReceipt/v1` always states:

```yaml
evidence_only: true
creates_task: false
creates_route: false
creates_work_claim: false
creates_worker_slot: false
grants_execution_authority: false
grants_domain_write: false
grants_signal_write: false
grants_w3_write: false
grants_merge_authority: false
```

R150 performs no Task/Route/Claim/worker/Signal/W3/domain mutation and no merge.

## Acceptance

R150 regressions prove:
- same-domain current repository evaluation;
- caller current-state injection rejection;
- forged R145 capability rejection;
- cross-domain mismatch fail-closed;
- stale expected main rejection;
- Control Tower scan failure blocks;
- Work Claim validation failure blocks;
- canonical active path collision wins over caller omission;
- canonical authority collision becomes O4;
- incomplete canonical active surface fails closed;
- repository state change during evaluation fails closed;
- outer receipt remains evidence-only;
- deterministic exact-state replay and input binding.

Retained R149 23-test and full Control Tower suites must remain green on Python 3.11 and 3.13.

## Hard locks

- `NO_SECOND_CONTROL_TOWER=true`
- `NO_SECOND_ACTIVE_WORK_REGISTRY=true`
- `NO_SECOND_DOMAIN_AUTHORITY=true`
- `NO_SECOND_LIVE_OBSERVATION_PROVIDER=true`
- `NO_CALLER_TRUSTED_CURRENT_STATE=true`
- `NO_AUTOMATIC_TASK_ROUTE_CLAIM=true`
- `NO_EXECUTION_AUTHORITY=true`
- `NO_DOMAIN_WRITE=true`
- `NO_SIGNAL_OR_W3_WRITE=true`
- `NO_AUTOMATIC_MERGE=true`
- `NO_SELF_REVIEW=true`
- `NO_SELF_MERGE=true`

Stop signal:

`R150_TRUSTED_TASK_RELEASE_OBSERVATION_BINDING_READY_FOR_INDEPENDENT_REVIEW`
