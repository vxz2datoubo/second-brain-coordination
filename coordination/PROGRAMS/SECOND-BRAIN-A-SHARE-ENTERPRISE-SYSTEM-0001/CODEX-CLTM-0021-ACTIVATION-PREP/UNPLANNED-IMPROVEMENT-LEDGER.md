# Unplanned improvement ledger

| Finding | Level | Decision | Rationale |
| --- | --- | --- | --- |
| Phase 3 `QueryPlan` default includes `superseded`. | A | Recorded as a mandatory future contract correction, not implemented now. | Epoch 78 is audit-only. |
| Phase 3 atom upsert lacks a bitemporal correction chain. | A | Recorded as required additive extension. | Silent overwrite is incompatible with CLTM history. |
| Initial audit incorrectly reported a PR #229 module-header collision. | A | Corrected by R2 audit remediation; no PR #229 file is copied. | PR #229 correctly uses CLTM module `0021`; MODULE_0020 remains a separate derived semantic-reconstruction / graph-projection dependency. |
| Private repository proposed by PR #229. | C | Rejected for this route. | Private repo creation is not authorized. |
