# R158 — Trusted Opportunity Provenance Binding into R151/R152

## Purpose
R158 closes the caller-trust seam between canonical S0C → R153 → R154 → R155 → R156 materialization and retained R151/R152 release/apply authority.

## Canonical base
- base main: `86912463b8a76f5f3f9b0a7ab6e511a1b6ae750f`
- governing Issue: #475
- current materializer: `coordination/CONTROL-TOWER/signal_opportunity_materializer_current.py`

## Contract
1. R151 no longer accepts arbitrary opportunity mappings as authority-bearing candidates.
2. `materialize_trusted_opportunity_batch()` invokes only the canonical current materializer and admits only `MATERIALIZED_FOR_R151` decisions whose decision and opportunity digests recompute exactly.
3. The trusted batch is an invocation-local Python object capability, not a cryptographic signature, durable truth store, or transferable authority token. Digest strings are mutation evidence only.
4. The batch binds canonical main, current-materializer identity, opportunity digests, materialization-decision digests, and a deterministic batch digest.
5. Duplicate opportunity provenance, malformed items, or authority-boundary drift fail closed.
6. R151 mints only `IdleSignalAutoReleaseAuthorization/v2`, binding the selected batch and materialization decision.
7. R152 rejects v1 authorization and has no caller opportunity argument. It fresh-rematerializes from canonical materialization inputs, derives the selected opportunity from the fresh sealed batch, then evaluates apply surface.
8. Main drift, rematerialization drift, forged batch/object/digest, stale authorization, non-materialized decisions, or provenance ambiguity fail closed.

## Preserved authority
- S0C remains unique Signal truth.
- R153→R156 remains the opportunity materialization/provenance chain.
- R151 remains sole idle selector/release authority.
- R152 remains apply transaction authority.
- R149/R150 remain release-impact/current-state gates.
- No second ledger, materializer, scheduler, task authority, signature authority, or ranking policy.
- No W3 write, trading/order/funds, secrets/permission expansion, production deploy, destructive history, self-review, or self-merge authority.

## Verification
Retained R151/R152 tests are migrated to v2 without deleting prior behavioral coverage, with additional adversarial cases for raw opportunity injection, fake batch construction, digest tamper, v1 authorization, and fresh rematerialization drift. CI reruns R157→R149 and the full Control Tower suite on Python 3.11 and 3.13.

## Exact bounded scope
Exactly the seven paths authorized by Issue #475 are changed. No S0C or R153/R154/R155/R156 implementation file is modified.
