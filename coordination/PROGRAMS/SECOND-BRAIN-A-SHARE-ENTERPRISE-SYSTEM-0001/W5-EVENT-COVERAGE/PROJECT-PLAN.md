# W5 Event Coverage P0-VS1 — R166 clean governed successor

## Status

`BOUNDED_REFERENCE_IMPLEMENTATION / RESEARCH_ONLY / NO_TRADING / NO_SOURCE_OR_CAUSAL_AUTHORITY`

Source Issue: #501  
Parent remediation: #486  
Route epoch: 166  
Task: `GPT-W5-EVENT-COVERAGE-CLEAN-SUCCESSOR-R166`  
Worker slot: `GPT-WORKER-R166-W5-EVENT-COVERAGE-2`  
Pre-write snapshot: `W5-EVENT-COVERAGE-R166-2026-08-29-001`

R166 is a clean, non-retroactive implementation. PR #487 and PR #497 remain read-only historical/technical evidence and are not acceptance provenance for this branch.

## Purpose

Provide a deterministic pre-synthesis W5 gate that answers a narrow question:

> Given a caller-supplied candidate source list, point-in-time event candidates, and textual claims, what evidence gaps or claim-level restrictions must remain visible before any downstream research synthesis?

The gate deliberately does **not** answer whether a source is canonically trusted, whether a causal explanation is true, whether a market participant had a particular intention, or whether any trading action should occur.

## Authority model

The following are mechanically false in this slice:

- canonical source-instance authority is unavailable;
- typed causal authority is unavailable;
- typed participant-intent authority is unavailable;
- typed free-text semantic authority is unavailable;
- task, route, execution, write, review, merge, release, W3, domain, trading, permission and secret-access authority are all false.

Therefore:

1. `SourceRegistry/v1` is a caller **candidate evidence projection only**. Source class, grade, roles and `enabled` prove shape, not trust.
2. `observed_coverage_roles` remains empty until a separately governed canonical source-instance authority exists.
3. A caller cannot obtain `READY_FOR_SYNTHESIS` merely by fabricating a complete-looking registry.
4. Caller booleans such as `causal_identification_evidence` or `participant_intent_evidence` are rejected as invalid fields.
5. Caller `claim_type` relabeling cannot upgrade free-text authority.
6. Explicit unique-causal or participant-intent assertions block while their typed authorities are unavailable.
7. Other arbitrary free text is capped at `DOWNGRADE`, never authority-bearing `ALLOW`, while source-instance and typed semantic authority are unavailable.

## Data flow

`intent + caller SourceRegistry + scanned IDs + events + claims`

→ strict shape validation

→ point-in-time event filtering

→ source-chain deduplication

→ unresolved source/proxy coverage report

→ claim/evidence ledger

→ bounded disposition (`EVENT_COVERAGE_INCOMPLETE`, `PRICE_ANOMALY_UNRESOLVED`, or `ABSTAIN` in this authority epoch)

All output digests are deterministic integrity evidence only.

## Point-in-time rules

- timezone-aware timestamps are mandatory;
- future events are excluded;
- events before the requested window are excluded;
- irrelevant target/proxy events are excluded;
- market-effective time cannot predate source availability;
- syndicated copies sharing a source-chain ID count as one candidate chain;
- claim references to excluded, nonexistent or deduplicated-away event IDs block that claim;
- unexplained anomaly with no candidate event keeps backfill required.

## Data Grade rules

- microstructure-strength language such as CVD, Delta, footprint, absorption or order-book intent blocks when Data Grade is not A;
- supply/demand narrative under Data Grade C is explicitly downgraded;
- Data Grade never creates source or participant authority.

## Schemas

The bounded machine surfaces are:

- `SOURCE-REGISTRY.schema.json` → normalized candidate registry projection;
- `EVENT-COVERAGE-REPORT.schema.json` → point-in-time coverage/gap evidence;
- `CLAIM-EVIDENCE-LEDGER.schema.json` → claim-level decision evidence.

All three schemas are JSON Schema 2020-12, closed at the top level, and keep emitted authority values false.

## Verification

R166 requires all of the following before Engineering handoff:

- Python 3.11 and 3.13;
- compile success;
- complete W5 adversarial unit suite;
- all three JSON schemas parse and remain closed;
- static all-false authority boundary;
- exact seven-file changed scope from snapshot base `f1c687947c4846ca9484de0cf977df658f5bfcfb`;
- whitespace gate;
- current-main integration proof that pins one remote main SHA and one exact candidate SHA for the full comparison;
- retained Control Tower failures are classified by test ID plus normalized failure fingerprint;
- candidate-introduced or candidate-modified retained failures block;
- baseline failures may remain visibly recorded without being misattributed to R166;
- any main/head drift during the proof is `TEST_ENVIRONMENT_INVALID`.

The R166 workflow-local comparator is **not** the future canonical reusable CI primitive from #496. It is bounded evidence for R166 only.

## Explicit non-goals

R166 does not create or modify:

- a canonical source registry or live credentialed source adapter;
- an event truth authority;
- a causal-identification authority;
- participant-intent inference authority;
- generic Effective Challenge runtime;
- W3/MemoryStore/knowledge truth;
- A-share trading, order, broker, fund or production execution paths;
- provider/model/network runtime dependencies;
- review, Ready, merge or release authority.

## Stop gate

Engineering stops after exact-head CI, scope/provenance audit and handoff. Acceptance must come from a new exact-head independent review through Issue #453. Green CI is evidence, not acceptance authority.
