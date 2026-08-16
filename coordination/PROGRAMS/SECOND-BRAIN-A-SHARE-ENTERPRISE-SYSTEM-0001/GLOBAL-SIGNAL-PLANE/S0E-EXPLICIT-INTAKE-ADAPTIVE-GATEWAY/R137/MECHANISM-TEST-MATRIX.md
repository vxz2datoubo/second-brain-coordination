# R137 mechanism test matrix

agent_id: `CODEX`
source_agent: `CODEX`
reviewer: `GPT`

The 44 named tests in `tests/test_r137_live_observation_provider.py` are
mechanism checks, not policy approval or a release claim.

| Range | Mechanism evidence |
| --- | --- |
| R001-R005 | Valid public observation; caller forgery; no production registration; allowlisted repository; fixed-host GET transport with redirect/media/size/JSON rejection. |
| R006-R014 | Missing/substituted path/tree/blob, main and PR drift, malformed review, and incomplete review pagination fail closed. |
| R015-R020 | Expiry/replay, unknown provider, code digest, route/claim/lane/lease, head/base/review/main, merge/domain/approval invalidations fail closed. |
| R021-R029 | Contract, age, domain/path/review/PR/task/epoch request binding and evidence-bundle identity are mechanically enforced. |
| R030-R036 | Evidence-only authority, raw review facts, no scheduler/write route, no policy adjudication, bootstrap replay rejection. |
| R037-R044 | Exact object/invalidation/code identity, privacy/host surface, bounded freshness, no caller request proof and R136 unknown-proof rollback behavior. |

`global-signal-plane-r137-live-observation.yml` runs R137 and retained R136
fail-closed tests on Python 3.11 and 3.13.  On pull requests it also performs a
real public, unauthenticated GitHub observation and prints only an evidence
identity/digest and observed main SHA.
