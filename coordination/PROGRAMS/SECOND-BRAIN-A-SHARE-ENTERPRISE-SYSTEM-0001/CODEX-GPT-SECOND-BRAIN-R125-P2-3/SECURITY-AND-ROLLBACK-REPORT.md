# R125 P2.3 security and rollback report

agent_id: CODEX

## Security result

The exact-recall proof does not treat a stored row as proof of recall. For every ordinary-retrieval omission, it queries the canonical statement through `ContextAssembler` with `budget=1`; caller observability and admission therefore execute before the atom is accepted as recalled. The foreign-identity test returns the same false result as an absent identity under the caller scope.

Ordinary `QueryPlan` remains budget 50 and the compatibility adapter retains no post-assembly candidate scans. No raw source pointer, private identity, source body or packet-content hash is added to a public result.

## Rollback

Revert the additive epoch-125 implementation commit. This returns to the accepted R124 state without history rewriting, data migration, store schema changes or external state changes.

## Locked boundaries

Private source/store access, real ingestion/canary, raw private output, scheduler, formal PROJECT/GLOBAL promotion, E48/live, production MCP/Gateway, permissions, trading and merge remain locked.
