# E42 Active Discovery Report

agent_id: `CODEX`

## New design findings

1. A provenance digest belongs inside the durable record, not in the one-shot
   object address. Otherwise a substituted commit can create a new address.
2. A lost Contents API write response is a third state, not a normal conflict
   and not success. Read-back may aid reconciliation but cannot identify the
   writer, so an effect permit must remain blocked.
3. Owner identity must be checked before transformation and again when
   classifying the invocation; claim ID alone is not an ownership credential.
4. Terminal publication timing needs three ordered clocks: durable terminal,
   route `published_at`, and bounded transport observation.

## Difficulty and coordination

- The hardest part was preserving a production-shaped adapter without silently
  creating a live execution surface. The solution is a fixed-scope client with
  no default transport or credential loader.
- Real App callback and CLI process evidence cannot be validated in E42 without
  violating the no-invocation boundary. They remain explicit runtime UNKNOWNs.
- GitHub Contents API write-loss ambiguity needs a future separately approved
  reconciliation protocol before any real authority branch is used.

## Scope decision

These findings were fixed only where they were prerequisites for E42. No new
Canary, App/CLI runtime, credential handling, or publisher implementation was
started.
