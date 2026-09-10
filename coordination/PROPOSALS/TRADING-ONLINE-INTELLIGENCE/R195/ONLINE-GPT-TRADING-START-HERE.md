# R195 Online GPT Trading Runtime — Start Here

Status: `CANDIDATE / PROPOSAL_ONLY / READ_MARKET_DATA / NO_TRADE`

Source Issue: #690
Roadmap: #688
Parent Trading Program: #31

## Purpose

Allow an online ChatGPT session connected to GitHub and approved read-only market/research providers to operate the Trading System even when the Owner's local TDX/TQ/L2 machine is unavailable.

This is **not** a second trading system, a second control plane, a broker bridge, or an order path. It is an online execution profile that consumes the existing Trading System governance and W2 market-semantics contracts.

## Mandatory bootstrap

Before any nontrivial online Trading run:

1. Fresh-read current remote `main`.
2. Read `coordination/GPT-UNIFIED-ORCHESTRATOR-START-HERE.md`.
3. Read the current Trading project adapter:
   `coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml`.
4. Read the current Trading active route / Issue / PR / exact-head / review state.
5. Read #688 and #690.
6. Read the canonical W2 market semantic contracts:
   - `MARKET-SEMANTIC-FIELD-SPEC.schema.json`
   - `PROVIDER-CAPABILITY-OBSERVATION.schema.json`
7. Runtime-discover currently connected provider capabilities. Never assume a plugin/provider is installed, entitled, fresh, or semantically unchanged merely because a prior run succeeded.

## Online execution pipeline

`ONLINE_GPT_SESSION`
→ `PROVIDER_CAPABILITY_DISCOVERY`
→ `MARKET_STATUS / FRESHNESS CHECK`
→ `STRUCTURED MARKET READ`
→ `SEMANTIC NORMALIZATION`
→ `ONLINE EVIDENCE PACKET`
→ `CANDIDATE FUNNEL`
→ optional `NEWS / FUNDAMENTAL / WEB EVIDENCE`
→ `READ-ONLY SYNTHESIS`

If local TDX/TQ/L2 is later available:

`ONLINE EVIDENCE` + `LOCAL EVIDENCE`
→ `CROSS-SOURCE QUORUM`
→ `LOCAL DEEP JUDGE`

## Provider roles

Provider names are runtime-resolved candidates, never permanent truth authorities.

- Structured A-share online market port: Longbridge when connected and capable.
- Financial / filing / company research port: Bigdata.com when connected and relevant.
- Browser / web-event acquisition port: TinyFish when connected and useful.
- Engineering/governance truth: GitHub current canonical state.
- Local deep microstructure: TDX/TQ/L2 only when separately available and authorized.

## Fail-closed rules

Never guess or silently normalize an ambiguous provider field.

Examples already observed:

- Longbridge screener has returned raw-looking market-cap values while labeling the unit `亿`.
- CN session metadata has not by itself represented the full closing call-auction semantics.
- Capital-flow response shape has differed from advertised schema in prior observation.
- After-close depth/trades may be empty while quote/aggregate trade statistics remain available.

For any such field, emit `UNVERIFIED`, `AMBIGUOUS_SEMANTICS`, `ENTITLEMENT_UNVERIFIED`, or `DATA_DIVERGENCE` as appropriate. Do not manufacture a canonical value.

## Online-only degradation contract

When the local deep-data layer is unavailable, the online session MUST explicitly mark these as unavailable unless an online provider has been independently verified to supply equivalent semantics:

- true L2 depth history
- tick-reconstructed Delta
- CVD
- Absorption
- Footprint
- exchange-faithful queue microstructure

Do not synthesize these from coarse quote or aggregate flow data.

## Candidate Funnel rules

The Online Scout may cheaply scan the broad CN universe and narrow candidates, but it must preserve:

- provider + query identity
- query predicates
- as-of timestamp
- page/coverage state
- total result count when available
- candidate universe before local deep filtering
- missingness / throttling / partial-page evidence

A screener result is a discovery set, not a validated winner list and not W7 acceptance.

## Output

Every online run should produce an `ONLINE_TRADING_EVIDENCE_PACKET/v1` compatible record or equivalent structured receipt containing source, timestamps, capability state, normalized facts, unresolved fields, candidate-funnel state and capability gaps.

The online session may provide research synthesis and conditional scenarios, but it must not create order/account/funds authority.

## Hard boundaries

- `READ_MARKET_DATA != PLACE_ORDER`
- no broker credentials in GitHub
- no real trade without separate explicit Owner Gate
- no invented local-runtime evidence
- no second numeric contract
- no second experiment/trial ledger
- no self-review / self-merge

## Candidate status

This R195 proposal is not canonical until exact-head CI, independent review and separate canonicalization complete. Until then it is implementation evidence only.