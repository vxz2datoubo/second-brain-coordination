# Broker Outreach Message

Use this as the short message to a broker, account manager, or support desk.
Do not include account number, password, token, cookie, position details, or
order history in the first message.

## Short WeChat / SMS Version

Hello. I want to confirm whether my account can obtain a low-cost legal A-share
quant market-data interface for local research automation. I only need market
data first, not order or account functions.

Please help confirm:

1. Is QMT, PTrade, XTP, broker proprietary SDK, or another quant API available?
2. Does it include Shanghai/Shenzhen Level-2 data?
3. Which fields are included: five-level book, ten-level book, raw trade ticks,
   raw order or entrust events, order queue, cancel events, call-auction
   indicative price / matched volume / unmatched volume trajectory?
4. Are timestamps exchange timestamps, vendor timestamps, or local receive
   timestamps? Are sequence numbers or channel numbers provided?
5. What is the lowest cost, asset threshold, or monthly package needed?
6. Can the market-data API run without enabling account/order functions?
7. Is local storage for personal research allowed under the license?

If possible, please send the official field list, SDK document, entitlement
description, and fee/asset-threshold policy.

## Email Version

Subject: Inquiry about low-cost A-share quant market-data API entitlement

Hello,

I am evaluating a local research-only A-share quant system and want to confirm
whether your brokerage can provide a legal low-cost market-data interface.

The first phase only needs market data. I do not need live order placement,
account queries, asset queries, position queries, or broker login automation for
this inquiry.

Could you please confirm:

1. Available API surface: QMT, PTrade, XTP, proprietary SDK, HTTP gateway, or
   other official route.
2. Whether Shanghai/Shenzhen Level-2 entitlement is available for my account
   tier.
3. Field coverage:
   - five-level order book
   - ten-level order book
   - raw trade tick records
   - raw order / entrust event records
   - order queue
   - cancel event records
   - call-auction indicative price, matched volume, and unmatched volume
     trajectory
4. Timestamp semantics: exchange timestamp, vendor timestamp, local receive
   timestamp, sequence number, channel number, reset rule, and correction stream.
5. Minimum asset threshold, monthly fee, package name, or other cost.
6. Whether market-data-only mode is supported without enabling trading/account
   functions in the same process.
7. Whether local storage for personal research and replay is allowed.
8. Any restrictions on redistribution, sharing, or automated collection.

Please provide the official product name, SDK documentation, field list, and
license or usage terms if available.

Thank you.

## Follow-Up If They Say "Level-2 Is Supported"

Please confirm whether "Level-2" means only ten-level quote snapshots and
aggregate metrics, or whether it also includes raw trade ticks, raw order events,
order queues, cancel events, and call-auction trajectory. We need the exact field
list before treating the route as raw L2 data.
