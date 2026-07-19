# Broker Low-Cost Market Data Request

Send this to each broker or account manager. Do not include passwords, tokens,
cookies, account numbers, or position details.

## Goal

We need a legal low-cost A-share quant market-data route for local research
automation. Trading/order APIs are not required for this inquiry.

## Questions

1. Does your quant API include Shanghai/Shenzhen Level-2 market data for this account tier?
2. Which interface is available: QMT, PTrade, XTP, broker proprietary API, or another SDK?
3. Can the market-data API run in a market-data-only mode without enabling order/account functions?
4. Which fields are included?
   - five-level book
   - ten-level book
   - raw trade tick
   - raw order event / entrust event
   - order queue
   - cancel event
   - call auction indicative price, matched volume, unmatched volume trajectory
5. Are timestamps exchange timestamps, vendor timestamps, or local receive timestamps?
6. Are exchange sequence numbers, channel numbers, or correction flags available?
7. What is the minimum cost or asset threshold for the above fields?
8. Is local storage for personal research allowed?
9. Is redistribution or sharing prohibited? Please provide the license terms.
10. Are historical tick/L2 archives available at lower cost than realtime L2?

## Required Evidence From Broker

- official product name
- SDK/API documentation
- entitlement screenshot or text confirmation
- field list
- timestamp and sequence semantics
- cost and minimum asset requirement
- explicit statement on local research storage

## Mother-System Classification

- If only quote/five-level book is available: `FIVE_LEVEL_SNAPSHOT`
- If aggregate fields only are available: `L2_AGGREGATE`
- If raw trades are available: candidate `RAW_TRADE_TICK`, pending evidence
- If raw orders are available: candidate `RAW_ORDER_EVENT`, pending evidence
- If order queue is available: candidate `ORDER_QUEUE`, pending evidence
- If auction sequence is available: candidate `AUCTION_TRAJECTORY`, pending evidence

No route is promoted until WorkBuddy supplies a raw sample pack and Codex
validates schema, timestamps, and replay behavior.
