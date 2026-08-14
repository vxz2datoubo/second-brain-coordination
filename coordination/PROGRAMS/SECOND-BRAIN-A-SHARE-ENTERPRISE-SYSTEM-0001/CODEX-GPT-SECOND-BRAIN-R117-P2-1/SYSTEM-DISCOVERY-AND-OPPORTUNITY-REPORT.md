# R117 P2.1 system discovery and opportunity report

agent_id: CODEX

## Verified discovery

`ContextAssembler` already supplied the correct scope/privacy/time/lifecycle/provenance policy, but lexical and relation candidates entered it through separate loops. P2.1 makes their shared entry point explicit without changing the policy meaning, ranking score formula, selection budget or `ContextBundle` schema.

## Reuse and non-duplication

The existing `MemoryStore`, `QueryPlan`, `ContextAssembler`, `_allowed`, trust gate and Memory Palace adapter are reused. No second store, new packet format, provider, graph representation or bundle projection is introduced.

## C-class proposal only

In a later GPT-routed epoch, project the count-only report into a versioned ContextBundle v1 and converge Memory Palace temporal/provenance channel collection behind the shared candidate set. Value: all candidate channels become auditable in one output. Risk: schema/semantic-hash compatibility and channel behavior drift. Owner: GPT. Trigger: accepted P2.1 exact-head review. Gate: approved P2.2/P2.3 route with compatibility fixtures.
