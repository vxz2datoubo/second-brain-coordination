# E43 System Discovery and Opportunity Report

## DISC-E43-001 — legacy positive classifier was a bypass

- severity: `S2_MATERIAL`
- type: `INTERFACE_OR_AUTHORITY_CONFLICT`
- verified fact: E42's legacy classifier could return the receipt's App/CLI
  evidence type while the durable claim remained `CLAIMED`.
- immediate action: implemented `IMP-E43-001` on the E43 branch and added
  regression coverage.
- what this does not prove: a synthetic E43 path is not a live runtime
  attestation or production permission proof.
- recommended disposition: `ACCEPT_IN_CURRENT_TASK`.

## DISC-E43-002 — Python sealing is not a production root of trust

- severity: `S3_MAJOR`
- type: `NEW_UNKNOWN_WITH_DECISION_IMPACT`
- verified fact: the current classes deny ordinary constructors, but code inside
  the same Python process can still inspect or alter process memory.
- safe disposition: E43 treats this as an explicit boundary and does not claim
  it is cryptographic isolation.
- coordination: GPT should decide whether a future runtime task requires an
  external signer or process boundary before any Canary is considered.
- current task impact: none on synthetic contract delivery; blocks live trust
  promotion only.
