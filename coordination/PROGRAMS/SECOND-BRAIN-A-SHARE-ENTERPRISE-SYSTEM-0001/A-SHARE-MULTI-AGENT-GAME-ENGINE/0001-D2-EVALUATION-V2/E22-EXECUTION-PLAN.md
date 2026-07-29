# E22 Execution Plan: Evaluation V2

## Authority, scope, and recovery point

- Task: `CODEX-D2-EVALUATION-V2-EXECUTABLE-MUTATION-METAMORPHIC-AND-FAIL-CLOSED-EVIDENCE-0014-E22`
- Schema and route epoch: `23.0` / `22`
- Accepted D2 base: `fa68186ea81644b406b58e2ab56d65feeb4d4d94`
- New branch: `codex/d2-evaluation-v2-0014-e22`
- Required PR base: `codex/a-share-multi-agent-game-engine-0001-d2-e10`
- Gate: `B_NEW_EVALUATION_V2` only. Gates C and D, Issue #92, and PRs #101, #102, #103, and #105 are not writable by this task.
- Boundary: `PUBLIC_SAFE / SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`.

This first commit contains only this plan.  Recovery is deterministic: fetch the
active route, verify that its accepted base remains `fa68186...`, enter this
worktree, read `STATUS.yaml` when it exists, and resume at the first incomplete
checkpoint.  No market source, account, order, trade, replay, backtest, fit, or
performance calculation is authorized.

## Verified starting facts

1. `0001-D2/d2_game_core.py` is the sole D2 system under test (SUT). It already
   exposes immutable episode carriers, `arbitrate`, and `verify_episode_ledger`.
2. Gate A at `fa68186...` closed exact primitive, exact enum, and exact carrier
   boundaries. Evaluation V2 must test those boundaries without weakening them.
3. Frozen PR #102 (`3eec58a815aa9139fcf4d37a11c4b2aa9b3779c0`) is historical
   evidence only. It has no writable branch or execution authority.
4. Existing D1/D2 fixtures are synthetic. They may be reused to construct SUT
   inputs, but no external data or real identity is introduced.

## PR #102 migration decision

| Historical element | Decision | E22 treatment | Reason |
| --- | --- | --- | --- |
| Scenario and invariant catalog idea | `PORT_CONCEPT_ONLY` | Fresh executable catalog with requirement, fixture, oracle, and test IDs | A catalog is useful; its old rows are not proof against the accepted core. |
| Negative-test grouping | `PORT_CONCEPT_ONLY` | Fresh negative matrix tied to actual failures | E22 requires executable coverage and no orphan rows. |
| Determinism receipt intent | `PORT_CONCEPT_ONLY` | Canonical reports, archive runs, and receipt evidence | E22 adds mutation and oracle reports. |
| `evaluation_harness.py` | `NO_PORT` | New harness | The old predicates are not a real mutation registry or independent oracle. |
| Old test runner and tests | `NO_PORT` | New V2 test suite | It predates accepted E16--E21 repairs. |
| Old YAML receipts and generated counts | `NO_PORT` | Fresh receipt from actual executions | Historical outputs cannot prove E22 execution. |
| Old import/layout assumptions | `NO_PORT` | Direct SUT adapter with explicit base fingerprint | Prevents a second D2 authority or a stale-core evaluation. |

## Architecture

All new implementation stays below `0001-D2-EVALUATION-V2/`. It is an
evaluation package, not a production decision, memory, replay, or trading
runtime.

| Planned file | Role | SUT relationship |
| --- | --- | --- |
| `evaluation_v2_contract.py` | Immutable IDs, reports, and canonical serialization | Contains no D2 transition logic. |
| `synthetic_cases.py` | Deterministic synthetic fixture families and catalog reconciliation | Constructs public D2 inputs only. |
| `independent_oracle.py` | Ledger/state accounting reconstruction from immutable events and initial inputs | Recomputes conservation, external offsets, identity uniqueness, causal ordering, and hashes without importing D2 reducers. |
| `mutation_registry.py` | Executable mutant definitions, activation records, kill records, and stable score | Mutates evaluation inputs or independently materialized episode records; no decorative predicates. |
| `metamorphic_properties.py` | Property transforms and result comparators | Calls the SUT as a black box and checks independently stated relations. |
| `evaluation_v2_harness.py` | Runs the catalog, mutations, properties, and report reconciliation | Imports public D2 carriers/functions only. |
| `tests/test_evaluation_v2.py` | Focused synthetic unit, mutation, and metamorphic tests | Exercises the harness and SUT. |
| `tests/run_evaluation_v2.py` | Deterministic command-line report producer | Emits only canonical, public-safe synthetic summaries. |
| receipt and AMED files | Evidence, calibration, UNKNOWN, and handoff | Added only after executions are complete. |

The harness will fingerprint the imported SUT file and fail closed unless it is
the accepted `fa68186...` version. The oracle does not call `_arbitrate_internal`,
`verify_episode_ledger`, canonical hash helpers, or other production-only
branches. It will derive its own canonical representation from public immutable
carrier fields and compare it to stored D2 results rather than trusting stored
hashes, events, or net-filled summaries.

## Executable mutant model

Each registry row has: stable `mutant_id`, mandatory family, fixture ID,
activation function, observable behavior delta, killer test IDs, activation
digest, and status. Activating a mutant must change a real input/result path;
an unchanged trace is a harness failure, not a passing mutant. A mutant is
`KILLED` only when an independently executable oracle or metamorphic assertion
fails for the mutated artifact while passing for the baseline. All survivors are
listed explicitly with a reason; a score never hides them.

Required mutation families and intended executable attacks:

1. Replace declared arrival order with agent/action-ID order.
2. Move duplicate/replay identity reservation after terminal branching.
3. Commit only one leg of a peer transfer.
4. Omit or invert an external liquidity offset.
5. Trust a stored ledger/hash rather than reconstructing it.
6. Accept a forward or cyclic causal parent.
7. Bypass conflict `CLAIM` / `RELEASE` / `EXPIRE` ownership rules.
8. Replace exact primitive/enum/carrier checks with nominal `isinstance` or
   string fallback behavior.

The implementation will include at least one active mutant per family and
cross-family composites. The activation log, killer mapping, kill matrix,
mutation score, and surviving-mutant inventory are generated from execution,
not hand-written claims.

## Independent oracle and metamorphic properties

The independent oracle uses only initial inventory, immutable actions, emitted
events, declared external flows, and public episode fields. It separately checks
agent ownership, per-agent deltas, peer complementarity, closed-system
conservation, open-system offsets, unique action/order/invocation identities,
causal-parent precedence and acyclicity, conflict ownership transitions, and
tamper-sensitive canonical state reconstruction.

The metamorphic suite must cover the following relations with explicit
property IDs and test IDs:

1. Input permutation with a fixed `arrival_sequence` preserves semantic output.
2. Consistent alpha-renaming of every related identifier preserves normalized
   semantic shape while changing only identity-derived values.
3. Continuing an episode from its prior immutable state agrees with the same
   scheduled multi-step construction.
4. Replaying an action, order, or invocation identity fails before a second
   terminal event is emitted.
5. A valid peer transfer preserves closed-system inventory and has no external
   offset.
6. An external-liquidity action is accounted by an equal and opposite declared
   external flow.
7. Coordinated stored-state, flow, or hash tampering is rejected by the
   independent reconstruction.
8. Exact primitive, enum, and carrier lookalikes remain rejected, including in
   multi-fault reason-precedence cases.

## Coverage contract

The suite will reconcile executable IDs rather than merely count rows:

| Catalog | Minimum | Required row links |
| --- | ---: | --- |
| Synthetic scenarios | 72 | scenario, fixture, requirement, test |
| Semantic invariants | 80 | invariant, requirement, fixture, failure oracle, test |
| Negative cases | 37 | negative case, expected fail-closed code, test |
| Stateful multi-step episodes | 24 | episode, steps, continuation property, test |
| Counterfactual pairs | 36 | baseline, changed input, expected relation, test |
| Cross-family interactions | 24 | mutant/property families, expected killer, test |

Catalog reconciliation fails on missing IDs, duplicate IDs, nonexistent test
IDs, missing failure oracles, or unreferenced executable rows.

## Checkpoints and commit shape

| Checkpoint | Work | Evidence | Commit state |
| --- | --- | --- | --- |
| 10% | This plan, PR #102 port/no-port decision, base lock | plan validation and worktree status | Commit 1, plan only; then Draft PR |
| 30% | Contracts, fixtures, catalog reconciliation | focused catalog tests | uncommitted until substantive checkpoint |
| 60% | Independent oracle, all mandatory mutant families, metamorphic core | kill/activation reports and focused tests | folded into Commit 2 |
| 85% | Full counts, archive harness, safety scan, CI-compatible entry point | exact command receipts | folded into Commit 2 |
| 100% | Three clean archive runs, calibration, AMED, handoff, external anchors | byte-identical canonical report hashes | Commit 3, receipt only |

Commit 2 contains implementation, tests, and any verified plan correction.
Commit 3 contains evidence/receipt documents only. No amend, rebase, reset,
force push, merge, or writes to frozen PR branches are allowed.

## Evidence pipeline and validation

1. Run focused Evaluation V2 tests under local Python with a fixed seed.
2. Run inherited D1/D2 tests to show the evaluation layer did not alter the SUT.
3. Produce canonical public-safe report bytes, with process platform, Python
   version, root path, `PYTHONHASHSEED`, exact command, exit code, elapsed time,
   stdout hash, and stderr hash recorded in the final receipt.
4. Export three clean Git-archive roots from the substantive commit and run the
   complete V2 suite under three distinct hash seeds. The canonical semantic,
   mutation, and reason-order reports must be byte-identical across runs.
5. Run parser/serialization checks, link/allowlist checks, and a public-safe
   secret scan. Scanner fixtures and temporary archives remain untracked.
6. Require Python 3.11 and 3.13 CI. If the repository workflow does not provide
   an authorized path to run this suite, record that as an execution finding
   rather than claiming CI coverage.

## Risks, alternatives, and surviving unknowns

- **Common-mode oracle risk:** mitigated by no import of production reducer or
  verifier internals, independently specified accounting, and mutants that
  target stored-state trust.
- **Count theatre:** mitigated by executable catalog-to-test and
  invariant-to-failure-oracle reconciliation.
- **Synthetic overclaim:** all conclusions remain synthetic evaluation evidence,
  never market validity, participant identity, or profitability evidence.
- **PR #102 contamination:** mitigated by explicit concept-only lineage and
  fresh files on the accepted base.
- **CI path uncertainty:** a workflow may not currently execute this new path;
  the final receipt will report the observed state exactly.
- **Surviving unknown:** mutation adequacy demonstrates only selected semantic
  faults. It cannot prove absence of all defects and cannot release Gate C.

## Rollback

Delete only the new branch and its worktree after GPT declines the Draft PR;
the accepted base and frozen PRs remain untouched. Before deletion, preserve the
final receipt commit hash and external review links. No data, account, service,
or production-state rollback is relevant because this task is synthetic-only.
