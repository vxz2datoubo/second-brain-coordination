# R144 R4 Corrective Maintenance / Adoption Receipt

## Scope

This receipt records the bounded R4 closure attempt for the sole remaining blocker in Independent Review `4974621759` on PR #408.

R4 does **not** reopen B02/B03/B04, does not rewrite R3 history, does not retroactively authorize WorkBuddy, does not create a GPT runtime worker lease, and grants no merge or acceptance authority.

## Reviewed input

- R3 reviewed exact head: `af6be5ab72d5da2e7202cb8e587d53526c1ccc74`
- Independent Review: `4974621759`
- disposition: `CHANGES_REQUIRED_R4_MAINTENANCE_AUTHORITY_EXACT_BINDING_AND_RELEASE_STATE_MACHINE`
- Issue: `#406`
- PR: `#408`
- branch: `codex/r144-control-tower-gpt-worker-first-class`

## Truthful authority-first chronology

R3 history is preserved exactly as it happened. R4 does not claim that the R3 authority existed before the first R3 repair commit.

Instead, R4 created a **new** user-issued maintenance/adoption authority identity before any R4 substantive validator or test repair:

1. `af50bf7fc40b1628e6a372f668231132a2e53d45`
   - added only `coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R4.yaml`
   - exact adopted candidate input: `af6be5ab72d5da2e7202cb8e587d53526c1ccc74`
   - exact trigger review: `4974621759`
   - predecessor R3 authority required to remain `RELEASED`
2. Authority-only adoption checkpoint CI:
   - Program Control Tower run `32278792975`: `SUCCESS`
   - Phase 3 integrated offline memory run `32278792896`: `SUCCESS`
3. `9e2ff5a405c07f57349b0fb8f6721cac0520558b`
   - implemented exact R4 binding + ACTIVE/RELEASED state-machine validation
4. `653628a62cfbc9e2251bb4e1b830a026f75140fe`
   - added R4 adversarial tests

Thus the fresh R4 authority predates R4 substantive corrective writes. This is a fresh adoption/revalidation of the exact R3 candidate tree, not retroactive authorization of R3.

## B01.1 exact binding closure candidate

`worker_slots.py` now mechanically checks the R4 authority against:

- stable canonical R144 task brief for exact `task_id`, `route_epoch`, `issue`, and branch;
- exact PR `408`;
- exact trigger Review `4974621759`;
- exact adopted input head `af6be5ab72d5da2e7202cb8e587d53526c1ccc74`;
- exact activation parent head `af6be5ab72d5da2e7202cb8e587d53526c1ccc74`;
- exact R4 authority ID;
- exact released predecessor authority identity/state.

Negative tests cover wrong task / epoch / Issue / PR / branch / Review / adopted head / activation-parent head and wrong authority identity.

## B01.2 release-state closure candidate

R4 defines a mechanical state contract:

- `ACTIVE` may yield `maintenance_write_allowed=true` only when the exact authority is structurally valid;
- `RELEASED` always yields `maintenance_write_allowed=false`;
- `RELEASED` requires a non-empty `release_reason`;
- `RELEASED` requires `released_scope_status=NO_FURTHER_MODIFIER_WRITES_AUTHORIZED_BY_THIS_ARTIFACT`;
- `RELEASED` requires an explicit terminal `ACTIVE -> RELEASED` transition;
- an authority identity carrying release markers cannot be changed back to ACTIVE;
- any future maintenance activation requires a new user-issued authority identity.

Adversarial tests cover missing/incorrect release receipt fields and attempted in-place reactivation.

## B01.3 truthful adoption/revalidation closure candidate

The old R3 authority remains historical and `RELEASED`. R4 uses a new authority identity and does not rewrite or squash the earlier commit order.

The R4 authority-only checkpoint succeeded before substantive R4 repair. The active R4 substantive head `653628a62cfbc9e2251bb4e1b830a026f75140fe` then passed exact merge-ref CI:

- Program Control Tower run `32279464539`: `SUCCESS`
- Python 3.11 job `96154529305`: `SUCCESS`
- Python 3.13 job `96154529703`: `SUCCESS`
- checkout merge-ref: `94a0a05673daba86e27fa1297d1b0db065c1624a`
- merge binding observed: `Merge 653628a62cfbc9e2251bb4e1b830a026f75140fe into 97a067037c9812deabc4da8e2e0450a7ffbf8300`
- full Control Tower suite: `89/89 OK`
- Control Tower: `errors=[]`, `foundation_structural_check=PASS`, projection matches
- Work Claims: PASS
- claim projection: MATCH
- authorization witness round trip: `fresh=true / MATCH`

## Retained closures

The R3 fixes for these already-accepted blockers are intentionally retained:

- B02 canonical GPT worker registry missing => fail closed;
- B03 strict boolean / explicit identity authority schema;
- B04 malformed canonical registry => authorization witness invalid/stale.

## Release / review gate

After this receipt is committed, the R4 maintenance authority is to transition once from `ACTIVE` to `RELEASED`. That release commit is intentionally the **last modifier write under this authority**.

The final RELEASED exact head and its fresh merge-ref CI are post-release handoff evidence and are not fabricated into this pre-release receipt.

Hard gate remains:

`KEEP_DRAFT / NO_MERGE / NO_SELF_REVIEW / R143_REMAINS_FROZEN`
