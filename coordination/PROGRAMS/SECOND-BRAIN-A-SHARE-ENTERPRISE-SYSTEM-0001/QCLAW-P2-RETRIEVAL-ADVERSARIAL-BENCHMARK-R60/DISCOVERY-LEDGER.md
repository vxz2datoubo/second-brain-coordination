# R60 Discovery Ledger — remediation state

Historical false-green evidence is preserved as a defect record, not rewritten into success.

## D1 — public report observability
R118 froze caller observability before public rejection accounting. Targeted regression shows a hidden foreign candidate and an absent candidate have the same public admission report. Status: `CURRENT CONTRACT REGRESSION PASS`.

## D2 — fixture mutation truthfulness
Historical R60 mutated a copied atom while importing the unmodified packet. Remediation imports/re-reads the actual mutation, or uses canonical correction for derived closure. Status: `B02 CLOSED`.

## D3 — optional id_hint oracle
Historical forbidden sets could remain empty when `id_hint` was absent. Remediation derives forbidden IDs from persisted canonical identity. Status: `B03 CLOSED`.

## D4 — later-slice corpus
Canonical P2 has evolved beyond the original R116/R117-era snapshot. Thirty `runnable=false` cases remain useful candidate material but require case-by-case remapping before promotion. Status: `NEEDS_REVALIDATION`.

## D5 — honest current mismatches
`r60-013` and `r60-025` fail after fixing the harness. Expected outcomes were not changed. Status: `2 CURRENT FAIL / NEEDS_REVALIDATION`.

## D8 — hidden relation endpoint leak, corrected
**Historical defect:** pre-P2.2 `relations_around(selected_set)` can return a relation when either endpoint is selected. An admitted root could therefore expose a non-admitted/revoked/cross-scope endpoint ID through `bundle.relations`. The old R60 REJECT grader inspected only `bundle.atoms`, so `r60-019` could be PASS while the endpoint leaked. That historical PASS is invalid.

**Canonical evolution:** R118 explicitly recorded this defect as `R118-ADJ-P2-2-001`. R119/P2.2 then required independent admission of every relation/conflict/unknown endpoint before projection; current `ContextAssembler` implements endpoint-safe projection.

**Remediated proof:** the new full-surface oracle detects a simulated relation-target-only hidden ID at `$.relations[0].target_atom_id`. Against current runtime, `r60-019` persists a revoked endpoint with canonical ID `at-915e364b8719ad76582f`; the visible source can be admitted, but the forbidden endpoint occurs in no observable bundle/telemetry surface. Current result: `PASS`, while the historical pre-P2.2 leak remains recorded as a real defect.

## D9 — endpoint-free unknown behavior
Current P2.2 suppresses endpoint-free unknowns. Original `r60-025` expected one to surface. Status: `CURRENT FAIL / NEEDS_REVALIDATION`.

## D10 — superseded historical recall expectation
After real persistence, `r60-013` is genuinely superseded. Its HISTORICAL query does not explicitly include `superseded`, and current default truth states exclude it. Status: `CURRENT FAIL / NEEDS_REVALIDATION`.

## Evidence boundary
Local behavior run used isolated Python 3.13.5. Four load-bearing runtime modules were byte-verified; retrieval was a logic-preserving projection cross-checked against canonical GitHub source. Exact merged-runtime regression/public-safety evidence is GitHub Phase-3 CI.
