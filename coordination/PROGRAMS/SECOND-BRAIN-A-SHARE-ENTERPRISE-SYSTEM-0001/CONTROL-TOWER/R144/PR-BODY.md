## R144 — GPT Engineering Worker First-Class Control Tower Extension — R2

- canonical task_id: `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144`
- route_epoch: `144`
- issue: `#406`
- Draft PR: `#408`
- canonical activation executor authorized on main: `CODEX`
- **R1 actual implementation executor: `WORKBUDDY`**
- R1 WorkBuddy authority status: `NOT_CANONICALLY_RELEASED_FOR_R144 / CANDIDATE_IMPLEMENTATION_ONLY`
- **R2 corrective maintainer: `GPT_ARCHITECTURE_OWNER` under the user's explicit current instruction**
- R2 corrective-maintenance status: `DRAFT_BRANCH_REPAIR / NOT_A_RETROACTIVE_EXECUTION_LEASE / NOT_ACCEPTANCE_AUTHORITY`
- independent reviewer required after R2: `SEPARATE_GPT_INDEPENDENT_REVIEWER`
- mode: `project_plan`
- canonical base at R1 preflight: `97a067037c9812deabc4da8e2e0450a7ffbf8300`

### Provenance correction

R1 text and handoff incorrectly stated that the real executor was CODEX. The user subsequently confirmed that the implementation was actually produced by WorkBuddy. Canonical Control Tower evidence at that time authorized CODEX for R144 while `ACTIVE-WORKBUDDY-TASK.yaml` remained paused/non-executable. R2 therefore does **not** retroactively claim that WorkBuddy was authorized. The R1 code is retained as candidate implementation evidence and is being corrected on the same Draft PR under the user's explicit instruction to GPT.

Git commit author/committer metadata is treated as repository provenance only and is not automatically equated with Control Tower execution identity.

### R2 objective

Keep the useful R1 implementation, but close the executor-authority and fail-closed gaps identified by Independent Review `4973557016`:

1. malformed worker registry input must fail closed instead of silently becoming an empty slot set;
2. ACTIVE and RESERVED slots require complete route/provenance/reviewer-separation binding;
3. a RESERVED slot can never be executable;
4. every ACTIVE/RESERVED GPT worker slot must have **exactly one** matching Work Claim;
5. slot identity and Work Claim must agree on slot/task/epoch/issue/PR/branch;
6. slot execution surface/resource class must exactly match the Work Claim;
7. one task cannot hold multiple active worker slots while `nested_parallelism=FORBIDDEN`;
8. registry top-level authority/policy material participates in authorization witness invalidation;
9. CODEX/QCLAW/WORKBUDDY backward compatibility remains intact;
10. R143/#405 stays frozen until R144 is independently accepted and merged, followed by a fresh preflight.

### Target architecture

- canonical agent type: `GPT_ENGINEERING_WORKER`;
- canonical active source: `coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml`;
- worker identity: bounded `worker_slot_id` / lease, not `GPT_WORKER_1/2` pseudo-agent species;
- one active slot = exact execution identity + exact Work Claim + exact authorization witness;
- non-overlapping slots may coexist only inside WIP/resource policy;
- same canonical object / authority collision remains fail-closed;
- execution identity != independent acceptance authority.

### R2 changed implementation areas

- `coordination/CONTROL-TOWER/worker_slots.py`
  - strict registry schema/policy validation;
  - invalid slot entries no longer silently disappear;
  - `activation_state == ACTIVE` is required for executability;
  - RESERVED + executable lease fails;
  - complete live binding checks;
  - reverse slot → exact Work Claim cardinality and binding checks;
  - slot/claim surface and resource-class equality;
  - nested-parallelism guard.
- `coordination/CONTROL-TOWER/authorization_witness.py`
  - adds `worker_registry_fingerprint`;
  - top-level worker-registry authority material enters authorization/policy fingerprints.
- `coordination/CONTROL-TOWER/tests/test_worker_slots.py`
  - updates canonical test fixture schema;
  - adds R2 adversarial tests for malformed registry, orphan slot, surface drift, missing PR, reserved-executable, nested same-task parallelism and registry-policy witness invalidation.

### Existing R1 implementation retained

R1 still provides the multi-slot registry, worker-slot normalization/fingerprints, Work Claim forward binding, collision/WIP checks, claim projection, Control Tower projection, workflow trigger coverage and backward-compatibility tests. R2 is a bounded repair, not a rewrite.

### Workflow filename inventory correction

The task brief referenced `.github/workflows/program-control-tower-foundation.yml`, but the actual repository workflow is `.github/workflows/program-control-tower.yml` with `name: Program Control Tower foundation`. The implementation correctly uses the real file and records the mismatch as inventory evidence rather than inventing a non-existent workflow.

### Hard locks

NO_TRADE · NO_W2_RUNTIME · NO_W3_WRITE · NO_SIGNAL_TOWER_RUNTIME_WRITE · NO production/private data · NO secret/permission expansion · NO validator weakening for R143 · NO executor impersonation · NO self-review · NO self-merge · NO rebase/reset/force-push/history rewrite.

### Review gate

This PR remains Draft. R2 code written by GPT must be reviewed by a **separate independent GPT reviewer**. The current GPT window must not approve its own R2 changes or merge them.

**R2 completion signal after fresh exact-head CI:** `R144_R2_GPT_CORRECTIVE_PATCH_READY_FOR_INDEPENDENT_REVIEW`