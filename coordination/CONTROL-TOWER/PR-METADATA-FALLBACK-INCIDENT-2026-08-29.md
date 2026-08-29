# PR Metadata Fallback Incident — 2026-08-29

Incident class: `PRIMARY_CONNECTOR_SCHEMA_FAILURE`

Observed target:

- repository: `vxz2datoubo/ai-world-simulation-engine`
- PR: `#96`
- exact head: `8651edec3ce0b9d3f140f4f920817e4abfa5830e`
- desired metadata operation: Draft -> Ready for review

Observed native connector failure:

`Repository.fullDatabaseId` is requested by the connector response selection, but the current GitHub GraphQL `Repository` type does not expose that field.

Fresh readback after repeated attempts confirmed the PR remained `draft=true`; therefore the mutation was not treated as successful.

Governance response:

- no code/head mutation on the target PR;
- no merge bypass;
- no review bypass;
- canonicalization remained blocked while Draft;
- establish a narrowly bounded official-API fallback with exact-head fencing and postcondition readback.

This incident record is evidence for transport resilience only. It creates no standing authority to use fallback operations beyond the bounded V1 operation.
