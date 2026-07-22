# Existing Fragment and Non-Duplication Matrix

| Concern | System of record | Reusable W12 input | W12 may add | W12 must not add |
|---|---|---|---|---|
| Market facts, bars, sessions, availability | W2 | Point-in-time observations and RuleSnapshot refs | Decision-facing adapters | Market-data store or second event truth |
| Validation and hard risk | W7 | ValidationReport, `ALLOW/CAP/FREEZE/REJECT` | DS-10 audit interpretation; DS-08 risk envelope upstream | Risk engine or approval bypass |
| Context and DecisionEpisode | W10 | World, personal and task context; frozen ProbabilityEstimate reference/hash | DecisionFrame and attribution projections | Second DecisionEpisode truth or copied/mutated probability |
| Expected value and allocation | W11 | NetEV, DS-08/DS-04 envelopes and allocation outputs | Calibrated ProbabilityEstimate inputs | Portfolio optimizer or Raw/Fractional/Risk-Constrained/Robust Kelly duplicate |
| Orders and fills | OMS / Execution | Read-only execution and TCA facts | DS-09 research contracts later | Order router, broker adapter or order state; execution may never enlarge allocation |
| Shared probability | W12 / DS-02 | Source forecasts, dependence and calibration evidence | One ProbabilityEstimate schema/computation | PEOS, personal model or W11 probability copy/rewriter |
| Memory and retrieval | PR #57 | LearningPacket and ContextBundle | Candidate W12 atoms/packets | Store, fusion, index, QueryPlan or ContextBundle duplicate |
| Knowledge gateway | PR #58 | Access decision and AnswerEvidenceBundle | W12 query presets after acceptance | Gateway, evidence bundle or revocation duplicate |
| Local legacy contracts | `F:/aidanao/brain_core` | Source/Evidence/Knowledge/Decision/Forecast fragments | Explicit migration mapping | Silent declaration as remote canonical runtime |
| Temporal evidence | PR #8 | Multi-time and provenance semantics | Adapted fields after contract comparison | Second event/evidence/probability authority |
| QCLAW sync evidence | PR #34 | Historical privacy and staging evidence | Hash-linked evidence references | Current-state claims without revalidation |

The non-duplication rule is structural: renaming an existing object or placing it in another directory does not create a new capability boundary.
