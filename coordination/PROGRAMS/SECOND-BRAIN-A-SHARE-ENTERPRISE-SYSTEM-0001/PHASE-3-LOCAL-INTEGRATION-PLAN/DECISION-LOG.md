# Decision Log

| ID | Decision | Basis | Consequence |
| --- | --- | --- | --- |
| D-P3-001 | Treat this task as planning-only. | Active task #47 and `research_only / NO_TRADE`. | No code, service, provider, broker, account, or credential operation. |
| D-P3-002 | Keep P1/P2 as reusable contracts/reference, not local authority. | Merged P1/P2 matrices explicitly leave local runtime unknown. | Local work begins with adaptation evidence, not a second system. |
| D-P3-003 | Use a system-of-record matrix before adapter implementation. | Shared root has legacy state, public artifacts, candidate QQ work, and WorkBuddy evidence. | Prevents silent dual authority. |
| D-P3-004 | Correct the credential authority filename. | The task filename was absent; `CREDENTIAL-SECRETS-LOCAL-ONLY-v1.0` was verified. | Path drift remains recorded; no credential file was read. |
| D-P3-005 | Use an archive fallback for drafting. | Git fetch to current main reset twice. | Archive has verified source commit but is not a worktree; publication needs parent re-verification. |
| D-P3-006 | Require WorkBuddy read-only evidence before real data integration. | Local source semantics and provenance are unverified. | Adapter implementation is sequenced after M1/M2. |
| D-P3-007 | HTTP 8766 may only be a future narrow read wrapper. | Existing route surface is broad and service registry data may be stale. | No service call/action in this task. |

## Rejected alternatives

- Rebuild a new local mother system: rejected because current `brain_core` already contains candidate contracts/governance concepts.
- Treat legacy JSON/SQLite as canonical: rejected because provenance, authority, and rollback are not frozen.
- Start realtime or TQ/TDX probing now: rejected because #47 is planning-only and runtime capabilities require approved evidence.
