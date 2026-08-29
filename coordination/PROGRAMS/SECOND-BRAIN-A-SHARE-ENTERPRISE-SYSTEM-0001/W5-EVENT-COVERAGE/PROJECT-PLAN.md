# W5 Event Coverage P0-VS1 — Project Plan

Status: `BOUNDED_IMPLEMENTATION / RESEARCH_ONLY / NO_TRADE`

Source Issue: #486  
Parent P0: #308  
Canonical release base: `939629f6e445245d1e8db693826be6d2aaa12521`

## Goal

Turn the existing W5 event/source/time semantics into an executable, deterministic pre-synthesis gate so a market or portfolio answer cannot silently skip event coverage and then fill the gap with a fluent story.

## Reuse map

This slice **does not create a new event ledger or news store**.

It reuses:

- #68 / `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-BLUEPRINT-v1.0.md`
  - `PolicyMacroEvent.event_type`
  - W5 source grades `A1/A2/B1/B2/C1/C2/D`
  - `available_at` / `market_effective_at`
  - point-in-time and source-authority discipline
- #199 cross-market event-transmission semantics
- existing W2/W5 market/event authorities
- #282/#30 only as future feedback consumers
- #312 as the future shared Method Discovery / Effective Challenge authority

The VS1 runtime is a compiler/verifier over bounded input evidence. It does not persist canonical event truth.

## Runtime path

```text
intent class
  + SourceRegistry/v1
  + explicit scanned source ids
  + explicit scanned proxy symbols
  + point-in-time event candidates
  + candidate claims
        |
        v
Event Coverage Gate
  1. derive mandatory coverage roles from intent class
  2. verify explicit scan coverage
  3. reject future event evidence
  4. deduplicate syndicated source chains
  5. detect unresolved anomaly/no-news state
  6. compile ClaimEvidenceLedger/v1
  7. enforce data-grade/language rules
        |
        v
READY_FOR_SYNTHESIS
| EVENT_COVERAGE_INCOMPLETE
| PRICE_ANOMALY_UNRESOLVED
| ABSTAIN
```

## Intent policy

VS1 intentionally derives required roles from the intent class rather than trusting the caller to provide an empty allowlist.

`MARKET_ATTRIBUTION` requires:

- `FIRST_PARTY`
- `MARKET_WIRE`
- `COMPANY_DISCLOSURE`
- `TECHNOLOGY_RELEASE`
- `POLICY_REGULATORY`

`PORTFOLIO_LATEST` requires all of the above plus:

- `OVERSEAS_PROXY`
- explicit scan coverage for every configured proxy/comparable symbol
- default 24-hour point-in-time lookback

Missing coverage is `EVENT_COVERAGE_INCOMPLETE`, never evidence of “no event”.

## Data-grade / language contract

- Data Grade C cannot support CVD/Delta/footprint/absorption/order-book claims.
- Participant-intent terms such as 主力/吸筹/洗盘/出货 require Data Grade A **and** explicit participant-intent evidence.
- Supply/demand narrative terms at Data Grade C require downgrade.
- “唯一原因/就是因为/主要因为” cannot become accepted causal language without explicit causal-identification evidence.
- A complete scan with no qualified event and an unexplained anomaly returns `PRICE_ANOMALY_UNRESOLVED`; the runtime never invents an event or participant story.

## Anti-forgery / authority boundary

The public trust path is `run_event_coverage_gate(...)`, which derives coverage and claim outcomes directly from raw bounded inputs in one deterministic pass. A caller does not supply a pre-approved `EventCoverageReport` to mint synthesis authority.

Every returned object carries all-false authority flags. It cannot:

- create task/route/work claim;
- grant execution or write authority;
- grant independent-review ACCEPT;
- grant merge/release;
- write W3 or domain truth;
- trade or touch accounts/orders/funds;
- expand permissions or access secrets.

## Mandatory regressions

1. BlueFocus / DeepSeek Harness point-in-time candidate is visible before the A-share anomaly but cannot be promoted to unique cause.
2. Complete no-news scan + unexplained jump returns `PRICE_ANOMALY_UNRESOLVED`.
3. Data Grade C blocks strong microstructure / participant-intent language.
4. `available_at` after the query/anomaly cutoff cannot count as evidence.
5. Multiple syndicated copies sharing one `source_chain_id` count as one independent chain.
6. Missing mandatory source role returns `EVENT_COVERAGE_INCOMPLETE`.
7. `PORTFOLIO_LATEST` requires explicit proxy coverage.
8. Equivalent inputs produce stable digests.
9. Authority flags remain all false.

## Non-goals

- no live news adapters in VS1;
- no credentialed/paid-source access;
- no production deployment;
- no autonomous position change;
- no L2 purchase;
- no generic LLM reviewer / Effective Challenge runtime;
- no learning promotion;
- no second event or market-data store.

## Stop gate

Exact-head CI -> Draft PR -> #453 `REVIEW_REQUEST/v1` -> independent reviewer.

Completion signal: `W5_EVENT_COVERAGE_P0_VS1_READY_FOR_INDEPENDENT_REVIEW`
