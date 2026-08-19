# R144 R5 Terminal Maintenance Authority Repair Receipt

## Scope

R5 addresses only Independent Review `4974860616` blocker:

`CHANGES_REQUIRED_R5_TERMINAL_MAINTENANCE_AUTHORITY_REACTIVATION_GAP`

Already-closed R4 checks ① authority-first chronology, ② exact binding, ③ R3 predecessor RELEASED, ⑤ bounded scope, plus B02/B03/B04, are retained and not reopened.

## Reviewed input

- R4 reviewed exact head: `8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1`
- Independent Review: `4974860616`
- Issue: `#406`
- PR: `#408`
- branch: `codex/r144-control-tower-gpt-worker-first-class`
- canonical main during R5: `97a067037c9812deabc4da8e2e0450a7ffbf8300`

## Authority-first chronology

R5 created a new authority identity before any R5 substantive repair:

1. `6a6f1ccf6b2ce52334abe1c353790894d7f9c401`
   - added only `R144-GPT-MAINTENANCE-ADOPTION-R5.yaml`
   - parent is exact reviewed R4 head `8a2eb5c41f9b67328211569ac7c8d4c71d0cf6d1`
   - new authority ID: `R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R5-0001`
   - predecessor R4 authority remains RELEASED
2. authority-only CI before substantive repair:
   - Program Control Tower `32281552132`: SUCCESS
   - Phase 3 integrated offline memory `32281552145`: SUCCESS
3. `5ed329414cb7c0ea7bf414d434183e83e4139c02`
   - added monotonic terminal-authority tombstone registry
4. `cb60cce93d435c893913e678c19876460aa12bae`
   - validator consumes tombstones and rejects tombstoned authority IDs becoming ACTIVE
5. `9e549da84cb336a9c72e58f60c8086f61f35a8d2`
   - adversarial regressions, including the exact Reviewer bypass
6. `9754b972c9b2c3063903be655db4def623b99adb`
   - narrowed tombstone requirement to repositories with maintenance history, preserving generic fixture compatibility without weakening canonical R144 behavior

No history rewrite, reset, force-push, self-review or merge was performed.

## Monotonic tombstone mechanism

Canonical tombstone registry:

`coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-TERMINAL-TOMBSTONES.yaml`

A terminal record is authority material independent of mutable release receipt fields inside the authority artifact. Validator behavior:

- tombstone registry missing when maintenance history exists => FAIL CLOSED
- expected terminal authority ID removed => FAIL CLOSED
- exact tombstone fields drift => FAIL CLOSED
- tombstoned authority artifact missing or identity mismatched => FAIL CLOSED
- tombstoned authority `state: ACTIVE` => `MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION`
- this check does not depend on `release_reason`, `released_scope_status`, or `release_transition` still being present
- tombstone material is included in worker authorization witness material, so mutation invalidates/refuses authorization

## Exact Reviewer bypass regression

`test_r5_review_exact_bypass_released_to_active_and_delete_all_receipts_fails`

Mutation:

1. start with R4 authority RELEASED and R4 tombstoned;
2. set R4 `state: ACTIVE`;
3. delete all three mutable release receipt fields:
   - `release_reason`
   - `released_scope_status`
   - `release_transition`
4. validate.

Required/observed test expectation:

- `MAINTENANCE_TERMINAL_AUTHORITY_REACTIVATION` present
- `maintenance_write_allowed == false`

Additional regressions prove the R4 tombstone cannot be deleted or exact-binding-mutated.

## Interim failed CI and correction

R5 intentionally records the failed intermediate run rather than hiding it.

At `9e549da84cb336a9c72e58f60c8086f61f35a8d2`, Control Tower run `32282397127` failed because the first tombstone implementation required the tombstone registry even in generic unit-test repositories with **no maintenance history**. The exact Reviewer bypass test itself passed in that run.

The correction at `9754b972c9b2c3063903be655db4def623b99adb` changed only the applicability guard: no-maintenance repositories are unaffected; repositories containing R3/R4/R5 maintenance history still require tombstones and fail closed if they are absent or malformed.

This preserves the security property while restoring backward-compatible generic fixtures.

## Green substantive evidence

Exact substantive head before final terminal release:

`9754b972c9b2c3063903be655db4def623b99adb`

Program Control Tower run `32282833075`: SUCCESS

- Python 3.11 job `96165336167`: SUCCESS
- Python 3.13 job `96165335834`: SUCCESS
- merge-ref checkout: `a7f5d2f20e9b16d35df4d036cf5ec2d175079ed9`
- merge binding: `Merge 9754b972c9b2c3063903be655db4def623b99adb into 97a067037c9812deabc4da8e2e0450a7ffbf8300`
- full Control Tower suite: `93/93 OK`
- exact Reviewer bypass regression: PASS
- Control Tower `errors=[]`
- `foundation_structural_check=PASS`
- Work Claims PASS
- claim projection MATCH
- authorization witness roundtrip `fresh=true / MATCH`

Phase 3 integrated offline memory run `32282833064`: SUCCESS.

## Final release design

The final modifier commit must be atomic and must be the last branch-file write under R5 authority. In that one commit it will:

1. transition R5 authority `ACTIVE -> RELEASED` with complete release receipt fields;
2. append the R5 authority ID to the terminal tombstone registry;
3. extend validator expected terminal records to require both R4 and R5 tombstones;
4. extend regression coverage so the same `RELEASED -> ACTIVE + delete all release receipts` bypass is rejected for R5 itself.

The R5 tombstone will bind `release_parent_head` to this receipt commit rather than attempting an impossible self-referential final commit SHA.

After that atomic release commit, only read-only CI/reconciliation and modifier handoff comments are permitted.

## Hard gate

`KEEP_DRAFT / NO_MERGE / NO_SELF_REVIEW / R143_REMAINS_FROZEN`
