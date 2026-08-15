# AMED Research Ledger

agent_id: CODEX

| Question | Evidence and result | Disposition |
| --- | --- | --- |
| Can a minimal durable skeleton avoid a service dependency? | SQLite is in the Python standard library and supports transactional append/reopen tests. | Implemented. |
| Can projection be source of truth? | Rebuild-after-delete checksum fixture proves it must remain derived. | Rejected. |
| Can a receipt authorize execution? | Canonical contract and negative fixtures require `execution_authorized=false`. | Rejected. |
| Can duplicate delivery claim exactly-once? | The synthetic store only proves idempotent effective processing. | Explicitly not claimed. |

Research inputs are frozen public contract files on canonical main. No private source, runtime, or live connector was read.
