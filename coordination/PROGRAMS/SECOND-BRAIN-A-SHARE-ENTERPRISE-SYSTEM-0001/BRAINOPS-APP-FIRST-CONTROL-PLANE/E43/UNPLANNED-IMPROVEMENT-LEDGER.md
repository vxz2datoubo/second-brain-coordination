# E43 Unplanned Improvement Ledger

## IMP-E43-001 — prevent legacy classifier bypass

- AMED class: `B_BOUNDED_IMPLEMENT_AND_REPORT`
- observation: new E43 reconciliation code alone would not stop callers from
  using E42 `classify_execution()` for a positive receipt label.
- implemented change: E42 classifier now returns a claim-only observational
  assessment until E43 reconciliation is present.
- value: closes a real alternate call path; keeps existing receipt inspection
  possible without crediting terminal execution.
- compatibility: result type is unchanged; evidence type/reason change is
  intentionally fail-closed.
- rollback: branch revert.

## OP-E43-001 — future external trust root

- AMED class: `C_PROPOSAL_ONLY`
- idea: replace same-process seals with an independently verifiable envelope
  signer or a separately governed attestation process.
- owner: GPT to route after E43 review.
- trigger: a runtime task authorizes a Canary or real integration surface.
- validation gate: external verifier identity, key lifecycle, replay resistance,
  and independent adversarial review.
- current disposition: `PROPOSE_FOLLOW_UP`, not implemented.
