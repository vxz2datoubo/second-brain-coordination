# W10/W11/W12 Boundary Decision Absorption

`agent_id: CODEX`

Source: `coordination/BLUEPRINTS/W10-W11-W12-CROSS-MODULE-BOUNDARY-AND-P0-REMEDIATION-v1.0.md` at remote main `64a42895e49b31f4aa1de62d6db54bf54d4a555a`.

## Absorbed Decisions

1. **Risk chain:** user policy -> W7 final hard gate -> DS-08
   `PortfolioRiskEnvelope` -> W11 allocation candidate -> DS-09/Execution may
   reduce, delay, split or abstain. No downstream stage may enlarge authority.
2. **Robust decision vs Kelly:** DS-04 owns
   `AmbiguityAndRobustDecisionEnvelope`; W11 alone owns Raw, Fractional,
   Risk-Constrained and Robust Kelly. DS-04 never outputs capital fractions.
3. **Shared probability:** W12/DS-02 owns the one `ProbabilityEstimate` schema
   and computation. W10 freezes its reference/hash, W11 consumes read-only, and
   personal cognitive models cannot mutate it.
4. **T+1 semantics:** market turnover, portfolio turnover, sellable quantity and
   round-trip eligibility are distinct objects. Lot state references a versioned
   rule snapshot.
5. **Rule versioning:** `A_SHARE_RULE_SNAPSHOT` binds exchange, board, security
   type, effective interval, official evidence and delayed clauses.
6. **Ghost-capability governance:** the asserted count six is not evidence. Names,
   paths, prior claims and recommended downgrade are required before action.
7. **Romano-Wolf:** DS-10 existing subcapability, not a new skill; it requires a
   complete experiment family and dependence-preserving resampling and does not
   replace SPA/PBO/DSR/lockbox/cost/capacity/shadow gates.

## Workstream Consequences

- #60 M2 remains frozen; M0 must re-audit the actual PR #57/#58 Python lineage.
- #61 receives the contracted `ProbabilityEstimate` declaration in this D0
  package; runtime implementation still awaits an authorized child task.
- #62 waits for shared probability, DS-08/DS-04 envelopes and the A-share rule
  snapshot before single-opportunity historical validation.
- #63 remains D0-only and creates no child runtime.

