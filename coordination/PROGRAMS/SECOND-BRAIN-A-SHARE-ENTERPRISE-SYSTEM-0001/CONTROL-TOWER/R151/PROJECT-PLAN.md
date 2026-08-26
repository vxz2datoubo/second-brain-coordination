# R151 — Idle Signal Opportunity Auto-Release

Status: `IMPLEMENTATION_CANDIDATE / USER_STANDING_POLICY_BOUND / INDEPENDENT_REVIEW_REQUIRED`

Issue: #461

Base canonical main at branch creation: `4fac78c4fdc785bb47b408ec8434918b3deba73a`.

## Purpose

Convert the user's standing policy into a bounded startup/next-task decision seam:

1. urgent/current work wins;
2. when no P0/P1/P2 or active implementation exists, consider already-digested Signal opportunities;
3. pick at most one P3/P4 opportunity deterministically;
4. run the selected proposal through canonical R149 + R150;
5. mint a narrow `IdleSignalAutoReleaseAuthorization/v1` only for releaseable results;
6. allow the authorized GPT coordinator to create an Issue / Route / Work Claim / worker slot and begin bounded engineering;
7. independent exact-head review remains mandatory before merge.

## Authority model

R151 does **not** change S0C into an execution authority.

`Signal truth != Task authority` remains true.

The narrower successor rule is:

`digested Signal + user standing policy + fresh priority reconciliation + R149 + R150 -> bounded Control Tower execution authorization`.

The authorization is not a merge/deploy/secret/trading/destructive authority.

## Priority semantics

R151 reuses the IAGL priority vocabulary as semantics, not as a second production priority store:

- `P0_USER_OR_HIGH_RISK`
- `P1_EXACT_HEAD_REVIEW`
- `P2_BLOCKER_OR_DRIFT`
- `P3_BOUNDED_IMPROVEMENT`
- `P4_RESEARCH`

Any P0/P1/P2 observation blocks idle Signal promotion. Canonical active/reserved Work Claims and any active GPT Engineering Worker slot also block the idle path.

A startup coordinator must perform the fresh external priority scan (including Review Queue / blockers) before calling R151. The scan may add blockers; it cannot make canonical active work disappear.

## Digested opportunity contract

`DigestedSignalOpportunity/v1` is not a second Signal ledger. It is a transient task-release candidate projection with:

- stable Signal ref and evidence refs;
- desired effect / problem / success condition;
- current disposition and epistemic state;
- proof that the desired effect is still unmet;
- dependency readiness;
- P3/P4 class;
- deterministic value/materiality/readiness/age/cost ranking inputs;
- one complete existing `TaskReleaseProposal/v1`.

The proposal must bind the same Signal ref/domain/desired effect. `ALREADY_CANONICAL`, `ALREADY_SATISFIED`, `SUPERSEDED`, rejected/closed/done/cancelled or `UNKNOWN/NEEDS_REVALIDATION` opportunities cannot auto-release.

## Auto-release exclusions

Standing auto-release never covers:

- trading orders/funds;
- secrets/credentials;
- permission or visibility expansion;
- production deployment;
- destructive deletion/history rewrite/force push;
- major architecture beyond already approved scope;
- unresolved owner-domain authority or material conflict.

These return to a user gate.

## Apply seam

The scheduler is evaluation-only and emits an explicit side-effect plan:

1. `create_issue`
2. `create_route`
3. `create_work_claim`
4. `allocate_worker_slot`
5. `begin_bounded_engineering`

The authorized GPT coordinator applies these against **fresh current state**. Evaluation must not hide mutations. `apply_requires_fresh_recheck=true` is mandatory.

## Non-goals

- no daemon/background crawler;
- no autonomous merge;
- no production deploy;
- no Signal self-authorization;
- no second R149/R150/R145/S0C;
- no cross-domain write without owner authority;
- no bypass of independent review.

## Acceptance

- P0/P1/P2 and canonical active work block idle release;
- only P3/P4 eligible Signal projections are ranked;
- ranking is deterministic, value-aware and starvation-aware within priority;
- high-risk exclusions force user gate;
- selected proposal goes through actual R150, which retains R149;
- only releaseable R150 dispositions mint authorization;
- authorization is exact-main / Signal / opportunity / priority-observation / R150-receipt bound;
- authority schema mechanically forbids merge/deploy/secrets/trading/destructive powers;
- exact-head CI retains R149/R150/full Control Tower regressions;
- independent Reviewer accepts exact head.

Completion signal:

`R151_IDLE_SIGNAL_OPPORTUNITY_AUTO_RELEASE_READY_FOR_INDEPENDENT_REVIEW`
