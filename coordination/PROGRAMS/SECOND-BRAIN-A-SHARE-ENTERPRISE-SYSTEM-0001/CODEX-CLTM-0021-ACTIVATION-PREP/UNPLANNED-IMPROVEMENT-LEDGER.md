# Unplanned improvement ledger

| Finding | Level | Decision | Rationale |
| --- | --- | --- | --- |
| Phase 3 `QueryPlan` default includes `superseded`. | A | Recorded as a mandatory future contract correction, not implemented now. | Epoch 78 is audit-only. |
| Phase 3 atom upsert lacks a bitemporal correction chain. | A | Recorded as required additive extension. | Silent overwrite is incompatible with CLTM history. |
| PR #229 reuses module number `0020` in its blueprint header. | A | Corrected in audit interpretation; no stale file copied. | Avoids collision with QCLAW module 0020. |
| Private repository proposed by PR #229. | C | Rejected for this route. | Private repo creation is not authorized. |
