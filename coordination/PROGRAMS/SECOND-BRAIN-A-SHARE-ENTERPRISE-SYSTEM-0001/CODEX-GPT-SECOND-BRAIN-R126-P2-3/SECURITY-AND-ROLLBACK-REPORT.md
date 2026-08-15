# R126 P2.3 security and rollback report

agent_id: CODEX

## Security result

The exact-target proof is internal and returns only a boolean. It obtains a requested synthetic atom only to run the existing `ContextAssembler` caller-observability and admission boundary; a row's presence alone is not success. It bypasses discovery ranking and budget selection solely to avoid duplicate-statement tie displacement. Missing, foreign, revoked, or otherwise inadmissible identities return false without a rejection-reason oracle.

Ordinary QueryPlan budget and ranking remain unchanged. No adapter-side scan, second store, public schema, private content, source pointer, or raw packet data is added.

## Rollback

Revert the additive epoch-126 commit. This restores accepted R125 behavior without history rewriting, schema migration, data migration, or external side effects.

## Locked boundaries

Private source/store access, real ingestion/canary, raw private output, scheduler, formal PROJECT/GLOBAL promotion, E48/live, production MCP/Gateway, permissions, trading and merge remain locked.
