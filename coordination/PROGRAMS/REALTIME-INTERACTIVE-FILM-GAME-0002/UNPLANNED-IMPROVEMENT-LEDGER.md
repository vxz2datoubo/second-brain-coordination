# Unplanned Improvement Ledger

agent_id: CODEX

| ID | Classification | Improvement | Reason | Result |
| --- | --- | --- | --- | --- |
| I-S07-001 | AMED_B | Added transcript and slot-to-slot comparison with the save implementation | The route explicitly requires transcript export and branch replay comparison; the predecessor CLI had neither | Implemented and covered by S07 CLI test |
| I-S07-002 | AMED_B | Legacy v1 records are graph-validated after migration | A schema migration without semantic validation could report success then fail later | Implemented fail-closed validation |

No AMED_C/D authority expansion was attempted.
