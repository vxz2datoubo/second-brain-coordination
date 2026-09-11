# R195 Online GPT Trading Runtime — Acceptance Matrix

Status: `CANDIDATE / PROPOSAL_ONLY`

Source: #690  
Roadmap: #688

| ID | Acceptance target | Current evidence | Candidate verdict | Promotion requirement |
|---|---|---|---|---|
| R195-A01 | Online GPT can bootstrap from GitHub without local RDC/WorkBuddy | Current session fresh-read canonical main, Trading adapter, W2 semantic schemas and created an isolated candidate branch using GitHub connector | PASS_CANDIDATE | exact-head CI + independent review + canonicalization |
| R195-A02 | A-share structured quote works through connected online provider | Longbridge returned 300418.SZ and 300058.SZ quote payloads with source timestamps | PASS_CANDIDATE | repeatability/freshness checks; semantic bindings for volume/turnover |
| R195-A03 | Online market-regime context can be acquired | Longbridge CN market temperature returned temperature=44 with provider-native valuation/sentiment fields | PASS_CANDIDATE | preserve provider-indicator semantics; never treat as exchange truth |
| R195-A04 | Broad Candidate Funnel can operate online | Longbridge CN screener with `prevchg>=3%` and `turnover_rate>=3%` returned total=150 | PASS_CANDIDATE | PIT/full-universe/pagination/throttling contract tests |
| R195-A05 | Ambiguous provider units fail closed | Screener marketcap returned raw-looking value `50106812328` with display unit `亿`; R195 contract excludes it from canonical use | PASS_CANDIDATE | regression test that ambiguous unit/scale cannot enter normalized facts |
| R195-A06 | Financial/company evidence can be acquired online | Bigdata resolved 300418 and returned sourced company/market/earnings data | PASS_CANDIDATE | repeatability and source-attribution contract |
| R195-A07 | Cross-source reconciliation is possible without averaging-away disagreement | Longbridge and Bigdata agree on observed 300418 price 44.26; volume suggests an unresolved scale relationship | PASS_CANDIDATE | multiple-symbol/date checks and explicit `DATA_DIVERGENCE` tests |
| R195-A08 | Online evidence cannot masquerade as local runtime verification | Connected-provider schema forces `local_runtime_observed=false` and uses separate online evidence classes | PASS_CANDIDATE | schema validation tests |
| R195-A09 | Online mode explicitly degrades without local L2 | Runtime contract lists L2 depth history, tick Delta, CVD, Absorption, Footprint and queue microstructure as unavailable unless independently verified | PASS_CANDIDATE | output fixture/test demonstrating capability-gap disclosure |
| R195-A10 | No trade/account/funds/order authority is created | All R195 contracts set read-only/no-trade; evidence packet constants place_order/account/funds=false | PASS_CANDIDATE | negative tests against authority widening |
| R195-A11 | Existing W2 semantic authority is reused | R195 points to canonical `MarketSemanticFieldSpec/v1` and `ProviderCapabilityObservation/v1`; no second numeric authority created | PASS_CANDIDATE | independent architecture review |
| R195-A12 | Online mode can later compose with local TDX/TQ/L2 rather than compete with it | Runtime contract has optional LOCAL_DEEP_MARKET_DATA port and Cross-Source Quorum path | PASS_CANDIDATE | later separately governed local integration slice |
| R195-A13 | Online interactive mode is not falsely labeled 24x7 service | Contract explicitly states online chat session is not background runtime | PASS_CANDIDATE | production adapter remains separate future gate |
| R195-A14 | TinyFish can discover A-share official/public filing evidence | Domain-restricted TinyFish search found CNINFO/static CNINFO filings for 300418 with code/title/date/official URL identity preserved; direct PDF fetch reached the official filing URL but reliable extracted filing text was not proven | PASS_DISCOVERY_PARTIAL_CONTENT | preserve source URL/provenance; separately verify full-document extraction when needed |
| R195-A15 | Longbridge live depth/recent-trade entitlement during A-share session is proven | Prior after-close calls were empty | PARTIAL | market-hours live Reality Audit |
| R195-A16 | Screener is proven PIT-safe for historical/replay use | Current live discovery works, historical PIT behavior not proven | NOT_PROVEN | dedicated PIT/no-lookahead audit; do not use as replay truth beforehand |

## Required negative tests before promotion

1. A field with `AMBIGUOUS_UNIT` or `AMBIGUOUS_SCALE` cannot enter `normalized_market_facts`.
2. `CONNECTED_ONLINE_RUNTIME_OBSERVED` cannot set `local_runtime_observed=true`.
3. Missing local L2 cannot cause synthetic CVD/Delta/Absorption/Footprint generation.
4. Two materially disagreeing provider values must emit `DATA_DIVERGENCE`; arithmetic averaging is forbidden.
5. Candidate Funnel output cannot be labeled W7 accepted, probability truth, allocation truth, or order truth.
6. A provider/plugin becoming unavailable must degrade capability rather than silently reuse stale observation.
7. GitHub main/head movement must trigger fresh reconcile before candidate persistence/canonicalization.

## Review identity

This candidate was authored/steered by the GPT Architecture Owner. The author MUST NOT be the sole independent reviewer. Any final ACCEPT must bind the exact candidate head after all candidate edits are frozen.
