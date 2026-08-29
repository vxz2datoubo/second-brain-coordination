# W5 Event Coverage P0-VS1 — Clean Successor Plan

Status: `GOVERNED_CLEAN_SUCCESSOR / RESEARCH_ONLY / NO_TRADE / FAIL_CLOSED`

Source Issue: #486  
Parent P0: #308  
Route epoch: 164  
Pre-write snapshot: `W5-EVENT-COVERAGE-R164-CLEAN-SUCCESSOR-2026-08-29` / Issue #486 comment `5465321008`  
Canonical implementation base: `0665cc0147fe7efae7e9498c36f9a87566ad036c`

## Provenance

This branch is a non-retroactive clean successor created after the required post-`CHANGES_REQUIRED` snapshot. PR #487 head `d3fde862ffa3f0aa458266048e97272457d89e1b` is reference/adversarial evidence only and is not an acceptance candidate or inherited execution provenance.

Binding reviews:

- `pullrequestreview-5059199228` / `issuecomment-5464903998`: `CHANGES_REQUIRED`, blocker `FREE_TEXT_PARTICIPANT_INTENT_SEMANTIC_BYPASS`.
- `pullrequestreview-5059359436`: stale-snapshot gate block on the old remediation head.

## Goal

Implement the bounded deterministic W5 event-coverage pre-synthesis gate while preserving the existing W5 authority model and refusing all caller-mintable source, causal, participant-intent, trading, task, route, write, review, release and merge authority.

## Fail-closed authority decisions

1. Caller `SourceRegistry/v1` is evidence metadata only. No current canonical assembled source-instance authority exists, so caller class/grade/coverage-role metadata cannot satisfy mandatory coverage and `READY_FOR_SYNTHESIS` is unreachable.
2. Caller causal/participant booleans are forbidden.
3. No governed typed free-text semantic authority exists. Therefore arbitrary caller free text is non-authoritative and may be at most `DOWNGRADE`; caller `claim_type` relabeling cannot upgrade it to `ALLOW`.
4. Explicit recognized unique-causal or participant-intent terms remain `BLOCK`.
5. Point-in-time filtering, future-information exclusion, source-chain deduplication, Data Grade C restrictions, proxy/source gaps and all-false authority are retained.

## Exact bounded surface

Exactly seven files belong to this slice: three schemas, runtime, adversarial tests, this plan and the dedicated workflow. No canonical W5 source registry, source adapter, news store, trading path, generic Effective Challenge runtime or second authority is created.

## Acceptance attacks

- fabricated all-role registry and grade escalation cannot produce complete coverage;
- forged scanned source IDs fail closed;
- caller causal/participant booleans fail closed;
- zero-blacklist-token paraphrases such as `大资金正在持续收集流通筹码` and `大型资金账户正在主动减少市场流通筹码` never receive `ALLOW`;
- the same protected meaning relabeled as `OBSERVED_FACT`, `SOURCE_CLAIM`, `MODEL_INFERENCE` or `UNKNOWN` never receives `ALLOW`;
- future events, syndicated copies, proxy gaps, Data Grade C and invalid event references retain their prior safeguards;
- all authority vectors remain false;
- deterministic replay/digests remain stable.

## Stop gate

Exact-head Python 3.11/3.13 CI, retained Control Tower regressions, current-main integration-delta check, exact seven-file scope, whitespace check, then a new Issue #453 `REVIEW_REQUEST/v1`. No self-review, Ready transition or merge before independent exact-head acceptance.
