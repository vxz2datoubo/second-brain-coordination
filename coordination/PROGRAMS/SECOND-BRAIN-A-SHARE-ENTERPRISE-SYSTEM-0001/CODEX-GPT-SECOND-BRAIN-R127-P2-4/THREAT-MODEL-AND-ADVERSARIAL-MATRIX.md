# R127 threat model and adversarial acceptance matrix

agent_id: CODEX

| Threat / invariant | Required future synthetic proof | Fail-closed result |
| --- | --- | --- |
| Default-off parity | NOT_CONFIGURED output equals P2.3 output | Provider is not a runtime dependency. |
| Failure and invalid result | exception, unavailable, denied, malformed response | P2.3 fallback; no hidden-candidate/count oracle. |
| Malicious suggestion | foreign, revoked, restricted or absent suggestion pathway | No public output before shared admission. |
| Injection / secret | secret-shaped or prompt-injection-shaped enrichment | Rejected before search/bundle/log projection. |
| Semantic score freeze | semantic-only versus lexical/relation duplicate discovery | semantic-only uses `score=None` supplemental placement; duplicates add channel only and never alter numeric score. |
| Determinism | duplicate lexical/temporal/relation/provenance candidates | atom-ID dedup and existing ordering unchanged. |
| Telemetry oracle | hidden candidate zero/one/many | identical public provider state/count output. |
| Analogy endpoint | source or target hidden/revoked/foreign/cross-scope | whole analogy suppressed. |
| Hidden-neighbor oracle | zero/one/many hidden raw neighbors around an otherwise eligible endpoint | identical structural feature, analogy projection, count and omission telemetry. |
| Non-evidentiary guarantee | analogies present/absent | support/counter, votes, confidence and trust-gate unchanged. |
| Lifecycle | CURRENT/HISTORICAL, valid_at and superseded atoms | semantic/analogy cannot resurrect an ineligible atom. |
| Persistence | restart and index rebuild | ordered safe output is deterministic. |
| Legacy removal | legacy callable supplied after P2.4 adapter migration | no parallel semantic authority remains. |

Public output must expose only coarse provider state authorized by the caller, never provider exception payload, IDs, source metadata, hidden suggestion count, hidden endpoint reason, hidden-neighbor count or hidden relation type.
