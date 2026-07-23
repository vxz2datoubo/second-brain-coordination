# System Discovery And Opportunity Report

> agent_id: `CODEX`
>
> scope: Issue #72 active discovery
>
> status: `SUCCESS_WITH_FINDINGS`

## Findings

1. **Logical and physical authority were being conflated.** W3 can have one logical owner while local `brain_core` and public Phase 3 remain two un-reconciled physical candidates. The safe action is a migration decision, not deletion or silent promotion.
2. **Maturity language was too coarse.** Blueprint, contract, implementation, synthetic determinism, A-share sample-out validation and shadow reconciliation need distinct states. The ledger now records zero A-share-backtested or shadow-validated modules.
3. **PR #70 is evidence input, not a passed gate.** Its 110-query package still needs immutable consumption and result evaluation against PR #58.
4. **0017 has the cleanest next falsifiable path.** BAR_ONLY can reuse current replay/rule assets while explicitly refusing hidden-stop, identity and order-flow claims.
5. **Some registration supplements are becoming redundant.** They should remain until a consumer search and GPT-approved deprecation, avoiding a noisy cleanup during convergence.
6. **Implementation and authority readiness require separate evidence.** R1 found that W3, W7 and W12 cannot be described accurately by a single maturity field: a component may be implemented while its canonical producer is unresolved, or a declared owner may lack a merged executable producer.
7. **Counterevidence and independent proof are different.** PR #75 can inform GPT's selection under uncertainty without establishing preregistered procedural independence.

## Opportunities Within Budget

| Proposal | Net value | Cost/risk | Disposition |
|---|---|---|---|
| W3 local/public system-of-record migration ADR and rehearsal | prevents divergent truth and data loss | high care, private data | `PROPOSE_FOLLOW_UP` |
| 0017 BAR_ONLY D0 then narrow implementation | early A-share falsifiable capability | overfitting and semantic overclaim | `SELECTED_CANDIDATE_NOT_ACTIVATED` |
| 0018 supplement deprecation | reduces routing drift | unknown consumers | `PROPOSE_DEPRECATION_AFTER_SEARCH` |

No new Skill, data source, runtime or workstream was created. Discovery did not expand WIP.
