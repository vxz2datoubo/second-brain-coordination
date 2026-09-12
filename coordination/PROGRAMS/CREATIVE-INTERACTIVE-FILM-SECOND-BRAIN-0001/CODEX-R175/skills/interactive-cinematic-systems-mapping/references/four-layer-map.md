# Four-layer product map

## Why four layers exist

The owner should see every material product consequence, but should not have to
learn storage internals, hash serialization, camera solvers, or statistical
monitoring before making a safe decision. The layers control explanation depth;
they do not hide uncertainty or transfer authority.

## Card decision table

| Layer | Use when | Required language | Never do |
| --- | --- | --- | --- |
| `explicit_known` | Direct request, signed decision, or canonical contract | “你已经明确要求……，所以……” plus source | Generalize beyond the recorded scope |
| `implicit_known` | Necessary high-confidence product inference | “暂定推断，置信度 0.xx，因为……” plus reversal point | Present inference as approval |
| `explainable_unknown` | Owner can act after a short explanation | What it is; what changes; value/cost; decision needed | Dump implementation detail instead of a decision model |
| `opaque_unknown` | Internals can remain delegated | Guard; observable signal; owner; stop/escalation condition | Hide money, rights, privacy, safety, or release impact |

## Capability sweep

For a whole-platform map, inspect all of these edges:

1. player text/comment and source provenance;
2. normalization to `ChoiceIntent` and clarification behavior;
3. model/simulator `NarrativeProposal` as a non-authoritative candidate;
4. story graph, event ledger, state replay, quest/reward/relationship state;
5. drama-manager beat eligibility and meaningful consequence;
6. script, character, scene, style, and rights packages;
7. verified state to director brief, shot bundle, and continuity gates;
8. avatar/character revisions and private asset references;
9. media jobs, idempotency, quality report, provenance, and budget gate;
10. manual/Douyin operations, deduplication, waiting, and recovery;
11. creative-knowledge candidates, correction, human review, and promotion;
12. GitHub evidence, Agent ownership, closeout, rollback, and drift alarms.

## User-facing summary contract

Whenever a material decision or blocker is reported, show:

- what the user needs to do now, or “现在不需要做任何事”;
- why it matters;
- expected value and cost effectiveness;
- remaining concern and automatic stop condition;
- a copyable forwarding prompt only when another actor truly must act.

Do not call a green test an independent review. Do not describe a provider's
published capability as achieved product quality. Do not turn an absent metric
into zero.
