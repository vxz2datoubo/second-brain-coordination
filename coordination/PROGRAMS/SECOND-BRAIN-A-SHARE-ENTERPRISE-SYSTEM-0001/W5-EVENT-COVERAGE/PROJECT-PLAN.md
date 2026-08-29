# W5 Event Coverage P0-VS1 — Project Plan

Status: `BOUNDED_REMEDIATION / RESEARCH_ONLY / NO_TRADE / FAIL_CLOSED_ON_MISSING_SOURCE_AUTHORITY`

Source Issue: #486
Parent P0: #308
Current remediation snapshot: `W5-EVENT-COVERAGE-2026-08-29-R1` / Issue #486 comment `5463776748`
Snapshot canonical base: `9c9cd901dee77154b1ddc7511d126737b4420bab`

## Goal

Turn the existing W5 event/source/time semantics into an executable deterministic pre-synthesis gate without creating a second event ledger, second news store, second source authority, or caller-mintable causal authority.

## Effective-spec chronology and fresh-main reconciliation

`SPEC_SNAPSHOT_GATE/v1` became effective before this remediation. Issue #486 then published `W5-EVENT-COVERAGE-2026-08-29-R1` at 2026-08-29T17:16:24Z. The acceptance-relevant blocker-remediation commits were written later, beginning at 17:20:01Z. Therefore the snapshot is genuinely pre-write and is not a retroactive provenance label.

Before final review handoff Engineering fresh-reconciled current canonical main `faed675036eb535218eaf8dc867fe29512175db1` against the snapshot inputs and prior independent review. The later main movement consists of unrelated Control Tower / R163 execution-governance work and does not add a canonical W5 source-instance registry, causal-identification authority, participant-intent authority, or a superseding W5 binding decision. The R1 fail-closed remediation decisions therefore remain the effective specification for this bounded PR.

If a later binding W5 correction, source-authority implementation, or superseding independent-review result appears before handoff, Engineering must stop and reconcile again rather than silently inheriting it.

## Canonical reality discovered during independent review

The canonical W5 blueprint/skill retain the source-grade vocabulary and W5 event/evidence system-of-record boundary, but their current-reality section still says the source instance registry/adapters are **NOT ASSEMBLED / NOT IMPLEMENTED**.

Therefore this VS1 remediation intentionally does **not** invent a source instance authority merely to preserve a green happy path.

Until a separately governed canonical W5 source registry or mechanically trusted adapter receipt exists:

- caller `SourceRegistry/v1` material is candidate/evidence metadata only;
- caller source grade/class/coverage-role fields cannot satisfy mandatory coverage;
- `observed_coverage_roles` remains empty;
- mandatory roles remain unresolved;
- coverage grade remains `INCOMPLETE`;
- the public gate cannot return `READY_FOR_SYNTHESIS` from caller source metadata.

This is a deliberate fail-closed capability gap, not a fabricated implementation.

## Reuse map

This slice reuses, rather than duplicates:

- #68 / `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-BLUEPRINT-v1.0.md`
  - `PolicyMacroEvent.event_type`
  - W5 source-grade vocabulary `A1/A2/B1/B2/C1/C2/D`
  - `available_at` / `market_effective_at`
  - point-in-time/source-authority discipline
- #199 cross-market event-transmission semantics
- existing W2/W5 event/market systems of record
- #282/#30 only as future feedback consumers
- #312 as future shared Method Discovery / Effective Challenge authority

The VS1 runtime remains an authority-free compiler/verifier over bounded evidence. It persists no canonical event truth.

## Runtime path

```text
intent class
  + caller candidate SourceRegistry/v1 (EVIDENCE ONLY)
  + scanned source ids
  + scanned proxy symbols
  + point-in-time event candidates
  + candidate claims
        |
        v
Event Coverage Gate
  1. derive mandatory roles from intent class
  2. keep missing canonical source authority explicit
  3. reject future event evidence
  4. deduplicate syndicated source chains
  5. detect unresolved anomaly/no-news state
  6. compile ClaimEvidenceLedger/v1
  7. enforce data-grade/language rules
  8. reject caller causal/participant authority flags
        |
        v
EVENT_COVERAGE_INCOMPLETE
| ABSTAIN
```

`READY_FOR_SYNTHESIS` remains in the historical enum for forward compatibility but is unreachable in the current public VS1 path while canonical source instance authority is absent.

## Causal / participant-intent rule

Current canonical W5 does not provide a typed causal-identification authority or participant-intent authority for this slice.

Therefore:

- `causal_identification_evidence` and `participant_intent_evidence` caller booleans are rejected;
- unique-cause language such as `唯一原因/就是因为/主要因为` is blocked with `CANONICAL_CAUSAL_IDENTIFICATION_AUTHORITY_UNAVAILABLE`;
- participant-intent language such as `主力/吸筹/洗盘/出货` is blocked even at Data Grade A with `CANONICAL_PARTICIPANT_INTENT_AUTHORITY_UNAVAILABLE`;
- future separately governed typed evidence may reopen these claims, but this remediation cannot self-authorize that bridge.

## Preserved point-in-time semantics

- future `available_at` evidence cannot support a current answer;
- syndicated copies sharing a `source_chain_id` count once;
- invalid/fabricated event ids cannot support a claim;
- Data Grade C cannot support strong CVD/Delta/footprint/order-book language;
- Data Grade C supply/demand narrative is downgraded;
- unexplained anomaly with no eligible event retains `event_backfill_required=true` while source coverage remains incomplete;
- proxy-scan gaps remain explicit.

## Anti-forgery / authority boundary

`run_event_coverage_gate(...)` never accepts a pre-approved report/ledger. Caller source metadata is validated for shape and event linkage only, then explicitly labeled evidence-only. It cannot mint source coverage authority.

Every returned authority vector remains all false. This slice cannot:

- create task/route/work claim;
- grant execution/write/review/merge/release authority;
- write W3 or canonical domain truth;
- trade or touch accounts/orders/funds;
- expand permissions or access secrets.

## Mandatory remediation regressions

1. fabricated all-role caller registry cannot create complete coverage;
2. grade escalation cannot change coverage authority;
3. caller registry output is explicitly evidence-only;
4. forged scanned source id fails closed;
5. caller causal boolean is rejected;
6. caller participant-intent boolean is rejected;
7. unique-cause language blocks without typed canonical authority;
8. participant-intent language blocks even at Data Grade A;
9. future event evidence is excluded;
10. syndicated copies remain one evidence chain;
11. anomaly/no-news retains backfill signal without pretending source scan completeness;
12. portfolio proxy gaps remain visible;
13. Data Grade C microstructure restriction remains;
14. Data Grade C supply/demand downgrade remains;
15. deterministic replay/digests remain stable;
16. all authority flags remain false;
17. event cannot self-declare source grade;
18. fake event ids cannot support claims;
19. timezone-naive query fails closed;
20. exhaustive caller-grade/all-role combinations cannot reach `READY_FOR_SYNTHESIS` while canonical source authority is absent.

## Non-goals

- no live news/source adapter;
- no new canonical source registry;
- no credentialed/paid source access;
- no production deployment;
- no autonomous position change/trading;
- no L2 purchase;
- no generic LLM reviewer / Effective Challenge runtime;
- no learning promotion;
- no second event/market-data/source store.

## Stop gate

Exact-head CI → Draft PR → #453 `REVIEW_REQUEST/v1` with effective-spec snapshot → independent reviewer.

Completion signal: `W5_EVENT_COVERAGE_P0_VS1_READY_FOR_INDEPENDENT_REVIEW`
