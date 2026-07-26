# D3 Bounded Proposal

## Status

Proposal only. D3 is not implemented and no real data, replay, backtest,
participant identity, account, routing, order, or trading access is requested.

## Options

| Option | Scope | Prerequisites | Evidence gate | Cost | Rollback |
| --- | --- | --- | --- | --- | --- |
| A. Synthetic calibration harness | Add synthetic score-calibration fixtures only | Accepted E12 core/evaluation | Independent holdout fixture and calibration tests | Low | Revert new D3-only path |
| B. Point-in-time replay adapter design | Plan contracts without source activation | Accepted data governance and rule snapshots | Schema-only review, no execution | Medium | Remove design-only artifacts |
| C. Bounded opponent-model research proposal | Specify Level-k/Bayesian candidate interfaces | A and B accepted plus evidence policy | Formal review of UNKNOWN/abstention rules | Medium | No runtime rollback needed before implementation |

## Recommended sequence

Choose A only after GPT accepts E12. B remains plan-only until point-in-time
data provenance and versioned A-share rule snapshots are accepted. C must not
start before B's evidence gate; fixed weights or a sigmoid must never be called
a calibrated probability.

## Non-negotiable gates

- Every later stage retains `research_only / NO_TRADE`.
- Synthetic outputs cannot be renamed into real participant identities.
- Candidate knowledge stays quarantined unless a separately accepted authority
  path says otherwise.
- Any real-source admission requires a new route and data-governance approval.
