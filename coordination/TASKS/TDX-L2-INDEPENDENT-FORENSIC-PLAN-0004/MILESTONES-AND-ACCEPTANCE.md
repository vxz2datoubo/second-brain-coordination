# MILESTONES-AND-ACCEPTANCE

## Milestone 1: Static Evidence Consolidation

Deliverables:

- raw evidence inventory
- WorkBuddy conclusion review
- `tqcenter.py` call graph
- forbidden-call list

Acceptance:

- every conclusion references raw evidence or is marked unverified
- stale claims are identified explicitly

## Milestone 2: Local File Delta Forensics

Deliverables:

- full inventory snapshot
- rolling delta table
- file-head and tail snapshots
- candidate record-width table
- cache/DB classification

Acceptance:

- no writes to `F:\tongdaxin`
- at least five priority objects classified
- no decoded L2 claim without aligned bytes and market-field proof

## Milestone 3: TdxQuant Read-Only Runtime Probe

Deliverables:

- raw snapshot payload
- raw callback JSONL
- exact method availability table
- `get_market_data(period='tick')` result/error
- close/cleanup receipt

Acceptance:

- no trading/account method called
- controlled timeout and shutdown completed
- fields classified into snapshot, aggregate, tick, order, queue, auction, or absent

## Milestone 4: Formula-Layer Verification

Deliverables:

- formula names tested
- output payloads
- mapping to aggregate/statistical vs raw-event semantics

Acceptance:

- `L2_AMO`, total bid/sell, total cancel bid/sell, L2 trade count, L2 order count, and auction formulas are explicitly classified

## Milestone 5: Route Decision

Deliverables:

- final route matrix:
  - local file
  - TdxQuant
  - TDX MCP
  - WeStock/Tencent
  - combination route
- mother-system data contract mapping

Acceptance:

- selected route states what it can prove and what remains unavailable
- no strategy promotion from unverified L2 claims

## Target-Mode Success Conditions

A later goal-mode implementation is successful only if it:

1. produces independent raw evidence;
2. does not modify TongDaXin or WorkBuddy outputs;
3. proves whether TdxQuant callback is richer than TDX MCP;
4. distinguishes aggregate fields from raw per-event streams;
5. updates the mother-system route status only after evidence review.

