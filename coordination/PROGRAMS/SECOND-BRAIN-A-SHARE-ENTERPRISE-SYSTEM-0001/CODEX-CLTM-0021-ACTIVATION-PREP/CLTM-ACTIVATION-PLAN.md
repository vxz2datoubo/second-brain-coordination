# CLTM activation plan

## Status

This is a plan only. Epoch 78 authorizes this audit, not Session A-E runtime implementation, formal persistence, a private repository, an MCP deployment, or a gateway.

## Proposed post-acceptance sequence

1. GPT accepts this audit checkpoint and publishes a fresh implementation route with exact scope, base SHA, privacy authority and test gate.
2. Add a `ConversationEpisode` adapter to the existing W3 candidate contracts using synthetic/public-safe fixtures only.
3. Extend the single `LearningPacket`, `MemoryStore`, `QueryPlan`, and `ContextBundle` contracts for user/project/privacy scope, bitemporal history, correction and Trust-Gate outcomes.
4. Demonstrate the A-E slice entirely in candidate mode with no formal write.
5. Independently decide whether native ChatGPT, a future MCP integration, or a gateway is available and authorized; capability claims must be rechecked at that time.

## Non-negotiable acceptance gates

- one W3 authority; no parallel store/query/bundle/vector/graph runtime;
- current-state recall excludes superseded/revoked/stale entries by default;
- historical recall is explicit and provenance-bearing;
- user statement, assistant analysis, hypothesis, and unknown stay distinct;
- private body/credential values never enter this public repository or test fixture;
- no E48 live integration before its independent acceptance;
- formal PROJECT/GLOBAL write remains locked.

## Rollback

Activation-prep changes only audit documents. Reverting the audit branch or publishing a later route changes no durable knowledge state.
