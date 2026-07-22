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

## Post-D0 Governance Delta at Main `529af757`

The following records are absorbed only as current governance facts. They do not
change the W12 D0 implementation scope and do not create business runtimes.

### W13 Daily Participant Capital-Flow Intelligence

- Maturity is fixed at
  `REGISTERED_READY_FOR_D0_PROJECT_PLAN / NOT_IMPLEMENTED / NOT_BACKTESTED / NO_TRADE`.
- W13 is a participant-evidence compiler and bulletin product. W2 remains the
  market/replay system of record; W5 the event/evidence ledger; W6 the competing
  participant-hypothesis layer; W7 the validation and final risk gate; W9 the
  shadow/learning layer; W10 the frozen decision episode; W11 the sole capital
  allocator; and W12 the probability and decision-science provider.
- Participant activity, identity, direction and amount are separate semantics.
  A brokerage seat is not a real person, ETF flow is not an exact state-linked
  purchase amount, and a public market signature is not a program-account identity.
- Post-2024 Northbound public activity cannot be represented as daily net flow
  without authoritative point-in-time evidence and a matching disclosure regime.

### W5 PMN Policy, Macro, News and Cross-Asset Intelligence

- Maturity is fixed at
  `REGISTERED_QUEUED_FOR_D0_PROJECT_PLAN / NOT_IMPLEMENTED / NOT_BACKTESTED / NO_TRADE`.
- PMN reuses W5 event/evidence, W2 market/calendar/replay, W12 probability,
  W7 validation/risk, W10 decision freeze, W11 allocation and W13 participant
  context. It creates no second event, calendar, evidence, replay, probability,
  risk, memory or execution authority.
- Historical recurrence or a late-July prior is not an official meeting date.
  A surprise requires a frozen ex-ante expectation or `EXPECTATION_UNKNOWN`.
  Pre-event movement may raise a leakage hypothesis but does not prove insider
  access or identity. One cross-asset move is not a complete policy explanation.
- PR #8 remains historical TEIF/attention evidence pending PMN D0 disposition.

### AMED Enterprise Governance

- Maturity is fixed at
  `ACTIVE_ENTERPRISE_STANDARD / GOVERNANCE_ONLY / NO_BUSINESS_RUNTIME / NO_TRADE`.
- AMED belongs to W1 and W9 governance. It binds Agent routers, impact forecasts,
  execution receipts, research ledgers and GPT seven-gate second-pass audit.
- Mission intent, system position, hard boundaries, active discovery duty,
  A/B/C/D improvement authority and an explicit exploration budget are required
  for non-trivial work. L3 work is split into a new task instead of being silently
  implemented.
- AMED never becomes a scheduler, evidence ledger, learning database or business
  system of record.
