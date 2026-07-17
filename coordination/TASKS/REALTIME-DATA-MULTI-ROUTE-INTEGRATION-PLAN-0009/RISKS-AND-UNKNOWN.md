# Risks And Unknowns

## Key Risks

- WorkBuddy 0008 post-upgrade results may change method names or field semantics.
- `Wtb` and similar metrics may have route-specific definitions.
- `Zjl/Zjl_HB` are useful but vendor-defined; overpromoting them would recreate fake DDX/DDY risk.
- Callback-driven collection can overload routes without debounce/rate limits.
- Local receive time can be mistaken for exchange time if schema names are loose.
- Existing code contains historical/offline quote construction that can be misread as realtime.
- `F:\tongdaxin` is being upgraded; any Codex access during this task could interfere, so it was not touched.
- Bulletin and some legacy docs show encoding mojibake; plans should rely on code/report facts and avoid rewriting unrelated docs.

## Unknowns Waiting On 0008

- Whether upgraded TdxQuant supports real tick rows.
- Whether HTTP 17709 is available.
- Whether formula enumeration/info exists.
- Whether TQ official skill is callable in WorkBuddy runtime.
- Whether ten-level depth is programmatically exposed.
- Whether any auction trajectory fields exist beyond aggregates.
- Whether new fields require unit conversion.

## Non-Goals

- No live trading.
- No account/position/asset calls.
- No automatic strategy promotion.
- No clearing `a_share_proxy_guard` from one route alone.
- No treating vendor fund-flow buckets as exchange order flow.

