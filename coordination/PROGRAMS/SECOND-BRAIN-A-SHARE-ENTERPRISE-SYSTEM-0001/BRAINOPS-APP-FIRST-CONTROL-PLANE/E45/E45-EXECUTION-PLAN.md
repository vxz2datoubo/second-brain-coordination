# E45 Execution Plan: Attested Witness and Recovery Enforcement

## Lease

- Task: `CODEX-BRAINOPS-ATTESTED-WITNESS-CLAIM-BOUND-DECISION-AND-RECOVERY-ENFORCEMENT-CLOSURE-0041-E45`
- Route epoch: `47`; mode: `project_plan`; active Issue: `#140`.
- Canonical base: `085e7aee55bbc951fa0cdc0900d95831c57b0c18`.
- Branch: `codex/brainops-attested-witness-recovery-enforcement-0041-e45`.
- Completion signal: `CODEX_BRAINOPS_E45_ATTESTED_WITNESS_CLAIM_BOUND_RECOVERY_ENFORCEMENT_READY_FOR_GPT_REVIEW`.
- Frozen source: PR `#139`, tested head `1f3e379efd9149722d7f3f210562fd91221e2da0`, receipt head `d5bef926abba615dbb5a9303c0422a9543ba51c1`.

E45 is synthetic engineering only.  No live GitHub authority operation,
Canary, App Automation, Codex CLI invocation, credential/configuration read,
account, market-data, or trading action is permitted.

## Fundamental Goal

Close the gap between an advisory ledger and enforced authority mutation.  A
positive synthetic capability decision must be minted only by a verifier-owned
attestor, refer to one exact challenge/provenance/claim/invocation/holder/
target context, expire deterministically, and be consumed exactly once across
ledger instances.  Recovery must consume the same governed authorization in
the actual mutation path rather than through a legacy bypass.

Python object sealing remains API discipline, not a production trust boundary.
No E45 artifact may claim runtime authority from these synthetic contracts.

## Source and Reuse Policy

Only selected files from frozen PR #139 will be copied by exact source commit
and blob digest.  The substantive commit will add an E45 source-import
manifest before or alongside each imported file.  Whole-branch merge,
cherry-pick, source-branch modification, and any PR #139 mutation are
forbidden.

Expected reusable components are the revisioned CAS adapter, durable challenge
ledger, recovery ledger, owner-specific evidence models, terminal comparison
helpers, and their synthetic tests.  The import review must reject any E44
receipt/report as runtime input and reject all generated output.

## Stages and Acceptance Gates

1. **P0 - plan and accountable import**
   - Commit this plan, then create the sole Draft PR.
   - Produce a selected-source manifest with path, source commit, blob digest,
     reuse decision, and exclusion rationale.
   - Acceptance: the branch begins at canonical main; imported files have
     exact source proof; PR #139 remains unchanged.

2. **P1 - witness provenance**
   - Separate caller-provided raw observation from a verifier-minted synthetic
     transport attestation.
   - Bind attestation to challenge, observed time, transport identity and
     evidence digest.  Caller-created/modified witness-shaped data fails
     closed.
   - Acceptance: positive decision cannot originate from raw input or a copied
     `transport_id` string.

3. **P2 - claim-bound decision use**
   - Bind a decision to provenance digest, storage ID, claim ID, invocation,
     task, epoch, canary, nonce, holder and target.
   - Add expiry recheck and durable globally one-shot decision-use CAS
     consumption before any terminal/effect path.
   - Acceptance: cross-route, cross-claim, replay, expired and lost-response
     paths fail closed, including new ledger instances.

4. **P3 - owner and recovery enforcement**
   - Cross-bind Manual App, Automation and CLI owner evidence to the holder
     instance/correlation and attested transport/run/process identity.
   - Route `governed_recover_expired_claim()` through recovery-ledger consume;
     downgrade legacy positive recovery authorization to a non-mutating
     observation.
   - Acceptance: identity splices and legacy/replayed recovery grants cannot
     mutate synthetic authority state.

5. **P4 - evidence closure**
   - Validate YAML/JSON, changed-path allowlist, public-safety scan and all
     synthetic tests.
   - Make one substantive tested commit, run exact-head Python 3.11/3.13 CI,
     then create exactly one non-empty receipt-only commit and repeat the CI
     matrix.
   - Acceptance: both heads have independently visible passing CI and all
     required AMED/WPDCR/UNKNOWN/handoff artifacts retain `project_plan`.

## Test Strategy

The suite will use deterministic local CAS roots only.  Required adversarial
families are caller-witness injection, transport mutation, provenance/claim/
route substitution, expiry, decision replay across a new ledger instance,
lost-response retry, Manual/Automation/CLI identity splice, recovery bypass,
and recovery grant replay.  Positive assertions must be paired with a
negative mutation that fails by a concrete reason, not merely a boolean
fixture.

## Boundaries, Recovery and Unknowns

- Allowed paths are the BrainOps program surface and `.github/workflows/brainops-e45.yml` only.
- No source from PR #139 can be treated as live runtime proof.
- The work is reversible by reverting the receipt-only commit and then the
  substantive commit; no external authority state is created.
- Real transport attestation, process isolation against a hostile same-process
  caller, and production GitHub mutation behavior remain `UNKNOWN`.

## Planned Deliverable Topology

1. This non-empty plan commit.
2. One substantive tested commit containing selected imports, contracts, tests,
   source manifest, status/evolution artifacts and E45 workflow.
3. Exactly one non-empty receipt-only commit after exact-head CI evidence.

No later gate starts before GPT second-pass review.
