# Threat Model

| Threat | E35 control | Residual state |
|---|---|---|
| GitHub task or prompt injection | Fixed route ID/epoch, target-agent allowlist, no command field and no executor | Future review still required |
| OAuth/session exposure | No session, browser profile, cookie, token or credential inspection; redact before audit | App/CLI sharing remains UNKNOWN |
| Localhost console exposure | Exact `127.0.0.1` contract; public bind rejected; GET-only routes | A manually approved future start needs fresh port checks |
| Arbitrary executable or argument injection | Service manifests reject executables/arguments; nested execution-shaped fields are rejected | Future service launcher needs a separately reviewed allowlist |
| Duplicate agent ownership | Per-route/epoch SQLite unique active lease and ownership fencing | No actual executor exists yet |
| Stale or replayed route | Epoch match, idempotency, user approval and active-lease checks fail closed | Remote reconciliation remains shadow-only |
| Offline GitHub state | `github_offline` blocks, later online reconciliation re-evaluates the full route | No automatic retry is scheduled |
| Accidental use of QQ route | QQ target fails closed before owner selection | QQ route remains separately governed |
| Whole-app interruption | UI only displays disabled controls; no kill or terminate operation exists | Emergency design requires an explicit later route |

No audit record may contain secret-like values. The redaction function removes
values keyed by token, secret, password, cookie, credential, authorization, or
API-key variants before serialization.
