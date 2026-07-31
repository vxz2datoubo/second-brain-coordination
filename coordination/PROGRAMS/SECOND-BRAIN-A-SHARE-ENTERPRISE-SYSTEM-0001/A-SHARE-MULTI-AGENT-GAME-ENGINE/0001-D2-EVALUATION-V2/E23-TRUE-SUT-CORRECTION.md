# E23 True-SUT Evaluation Correction

## Scope

This correction is limited to Gate B R1 on PR #106. It is public-safe,
synthetic-only evaluation work. The accepted D2 source remains unmodified and
SHA-locked. No real market data, replay, backtest, account, order, or trade
path is exercised.

## Corrected Mutation Model

Each mutation now starts with the accepted `d2_game_core.py` text, verifies its
SHA-256 fingerprint, replaces a named source seam exactly the registered number
of times, and compiles the mutant only in memory. The baseline and the mutant
run the same public SUT fixture. A registry row is rejected before execution
when it has no source replacement or uses an output-only/post-hoc seam.

The eight required families are distinct:

1. arrival sequence replaced by identifier ordering;
2. late duplicate/replay reservation;
3. partial peer-transfer commit;
4. omitted external-liquidity flow;
5. stored state-hash trust;
6. forward causal-parent acceptance;
7. conflict-ownership bypass;
8. weakened exact carrier and enum boundary.

Each row records baseline and mutant source hashes, behavior delta, a named
independent oracle, and a non-digest-only kill outcome. A generic expected
digest mismatch is not accepted as a kill condition.

## Corrected Catalog And Property Model

Scenario, invariant, negative, episode, counterfactual, and cross-family rows
carry normalized semantic input plus expected-relation signatures. The catalog
validator fails closed on a duplicated pair; repetition of a relation hash
alone is allowed only when the normalized input differs.

The eight properties execute real input transformations: arrival sequence swap,
consistent alpha renaming, continuation identity substitution, unavailable
causal-parent injection, peer quantity scaling, external side flip, stored
state-hash tampering, and exact tuple-carrier subclass substitution. Each is
paired with a relevant mutant and must pass for baseline while detecting its
mutant.

## Oracle Boundary

The independent oracle consumes public immutable episode fields and performs
its own accounting checks. It does not invoke the production reducer or use a
production verifier result as the general evaluation verdict. The stored-hash
family additionally has an explicit binding check to avoid a digest-only test.

## CI Boundary

The existing public-safe Python 3.11/3.13 matrix is extended to run this
directory's focused test suite and deterministic public runner. Archive and CI
evidence remain required before the final receipt; this file does not claim
that those executions have already occurred.

## Rollback

Revert the single E23 substantive commit from PR #106. This removes only the
E23 evaluator files and the one permitted workflow step; no data or runtime
state exists to restore.
