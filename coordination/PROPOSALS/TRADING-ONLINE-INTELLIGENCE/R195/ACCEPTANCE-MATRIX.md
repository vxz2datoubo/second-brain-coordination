# R195 Online GPT Trading Runtime — Acceptance Matrix

Status: `CANDIDATE / PROPOSAL_ONLY`

Source: #690  
Roadmap: #688

| ID | Acceptance target | Current evidence | Candidate verdict | Promotion requirement |
|---|---|---|---|---|
| R195-A01 | Online GPT can bootstrap from GitHub without local RDC/WorkBuddy | Current session fresh-read canonical main, Trading adapter, W2 semantic schemas and created an isolated candidate branch using GitHub connector | PASS_CANDIDATE | exact-head validation + independent review + canonicalization |
| R195-A02 | A-share structured quote works through connected online provider | Longbridge returned 300418.SZ and 300058.SZ quote payloads with source timestamps | PASS_CANDIDATE | repeatability/freshness checks; semantic bindings for volume/turnover |
| R195-A03 | Online market-regime context can be acquired | Longbridge CN market temperature returned temperature=44 with provider-native valuation/sentiment fields | PASS_CANDIDATE | preserve provider-indicator semantics; never treat as exchange truth |
| R195-A04 | Broad Candidate Funnel can operate online | Longbridge CN screener with `prevchg>=3%` and `turnover_rate>=3%` returned total=150 | PASS_CANDIDATE | full-universe/pagination/throttling tests; PIT remains explicitly unverified |
| R195-A05 | Ambiguous provider units fail closed before normalized-fact admission | Screener marketcap remains unresolved; schema now requires every normalized fact to carry `semantic_verification_state=VERIFIED`, `unit_semantics_state=RESOLVED`, an empty ambiguity set, semantic digest and source-observation ref; deterministic negative test rejects a raw ambiguous fact that lacks this gate | PASS_STRUCTURAL_GATE | runtime validator must additionally resolve semantic ref/digest against canonical W2 before accepting a fact |
| R195-A06 | Financial/company evidence can be acquired online | Bigdata resolved 300418 and returned sourced company/market/earnings data | PASS_CANDIDATE | repeatability and source-attribution contract |
| R195-A07 | Cross-source reconciliation is possible without averaging-away disagreement | Longbridge and Bigdata agree on observed 300418 price 44.26; volume suggests an unresolved scale relationship preserved as `DATA_DIVERGENCE` | PASS_CANDIDATE | multiple-symbol/date checks |
| R195-A08 | Online evidence cannot masquerade as local runtime verification | Connected-provider schema forces `local_runtime_observed=false`; deterministic negative tests reject local-runtime promotion and `LOCAL_RUNTIME_VERIFIED` | PASS_STRUCTURAL_GATE | runtime observation must remain source-bound |
| R195-A09 | Online mode explicitly degrades without local L2 | Runtime contract lists L2 depth history, tick Delta, CVD, Absorption, Footprint and queue microstructure as unavailable unless independently verified | PASS_CANDIDATE | output fixture/test demonstrating capability-gap disclosure |
| R195-A10 | No trade/account/funds/order authority is created | Evidence packet constants force place_order/account/funds=false; deterministic negative test rejects `place_order=true` | PASS_STRUCTURAL_GATE | independent authority-boundary review |
| R195-A11 | Existing W2 semantic authority is reused | R195 points to canonical `MarketSemanticFieldSpec/v1` and `ProviderCapabilityObservation/v1`; no second numeric authority created | PASS_CANDIDATE | independent architecture review |
| R195-A12 | Online mode can later compose with local TDX/TQ/L2 rather than compete with it | Runtime contract has optional LOCAL_DEEP_MARKET_DATA port and Cross-Source Quorum path | PASS_CANDIDATE | later separately governed local integration slice |
| R195-A13 | Online interactive mode is not falsely labeled 24x7 service | Contract explicitly states online chat session is not background runtime | PASS_CANDIDATE | production adapter remains separate future gate |
| R195-A14 | TinyFish can discover A-share official/public filing evidence | Domain-restricted TinyFish search found CNINFO/static CNINFO filings for 300418 with code/title/date/official URL identity preserved; direct PDF fetch reached the official filing URL but reliable extracted filing text was not proven | PASS_DISCOVERY_PARTIAL_CONTENT | preserve source URL/provenance; separately verify full-document extraction when needed |
| R195-A15 | Longbridge live depth/recent-trade entitlement during A-share session is proven | Prior after-close calls were empty | PARTIAL | market-hours live Reality Audit |
| R195-A16 | Screener is proven PIT-safe for historical/replay use | Current discovery has query observation time but underlying market-data session/date was not independently bound. Packet now records `pit_identity_state=UNVERIFIED`, null market-data as-of/session date, and schema rejects a false `VERIFIED` upgrade without both fields | NOT_PROVEN_FAIL_CLOSED | dedicated PIT/no-lookahead audit; no replay use before VERIFIED |

## Deterministic semantic checks

Candidate includes `validate_r195_contracts.py`. Before review/canonicalization it must pass at the exact head. It verifies:

1. the example evidence packet validates;
2. `place_order=true` is rejected;
3. connected online evidence cannot set `local_runtime_observed=true` or mint `LOCAL_RUNTIME_VERIFIED`;
4. `CONNECTED_ONLINE_RUNTIME_OBSERVED` cannot claim it was not observed in the connected runtime;
5. an ambiguous/raw normalized fact without the semantic normalization gate is rejected;
6. a structurally verified normalized fact shape is accepted, while external semantic ref/digest integrity remains a runtime validation responsibility;
7. `pit_identity_state=VERIFIED` with null market-data as-of/session identity is rejected.

## Remaining fail-closed truths

- JSON Schema can require a semantic ref/digest and VERIFIED/RESOLVED gate, but cannot dereference GitHub/W2 by itself. Future runtime implementation MUST verify the ref and digest against current canonical `MarketSemanticFieldSpec/v1` before normalized-fact acceptance.
- Current screener observation is discovery evidence, not PIT/replay truth.
- Current online mode is research-only and creates no account/funds/order authority.

## Review identity

This candidate was authored/steered by the GPT Architecture Owner. The author MUST NOT be the sole independent reviewer. Any final ACCEPT must bind the exact candidate head after all candidate edits are frozen.
