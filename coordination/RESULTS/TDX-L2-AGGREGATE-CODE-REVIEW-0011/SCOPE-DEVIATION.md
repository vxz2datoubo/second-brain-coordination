# SCOPE-DEVIATION

## Finding

The 0009 plan was still waiting for 0008 post-upgrade evidence, but 0010 added code and mother-system writebacks before that evidence arrived.

## Why It Happened

The implementation was scoped as governance and offline classification only:

- no TdxQuant runtime call
- no TDX MCP call
- no TongDaXin directory access
- no broker/account/trade call
- no production integration

It attempted to convert already verified aggregate evidence and future broker collection into explicit governance objects.

## Did It Exceed Authorization?

Partially. The user requested action on the route, and 0010 stayed offline, but 0009 explicitly framed multi-route integration as plan-only while awaiting 0008. Therefore code and mother-system writes should be treated as `IMPLEMENTED_EXPERIMENTAL` and `PENDING_CODE_REVIEW`, not production completion.

## What Still Holds

- Conservative TDX aggregate field semantics.
- Public crawler auxiliary-only policy.
- Broker outreach and reply schema.
- Offline classifier idea.

## What Should Wait For Formal Phase 1 Approval

- Runtime raw storage integration.
- Any broker SDK probing.
- Any promotion of raw tick/order/queue/auction capabilities.
- Any proxy-guard clearance based on these routes.

## Recommendation

Keep the experimental implementation, fix classifier edge-case issues before formal integration, and require ChatGPT approval before any read-only runtime probe.
