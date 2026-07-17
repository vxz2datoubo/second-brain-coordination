# Security Boundaries

- No StockAPI server connection was made.
- No real account or password was used.
- Runtime credentials are environment-variable names only: `STOCKAPI_ACCOUNT` and `STOCKAPI_PASSWORD`.
- Command redaction masks account/password fields.
- `connect()` refuses to run while `allow_network=False`.
- No broker, trading, account, order, cancel, asset, or position function was called.
- `F:/tongdaxin` was not accessed.
- Raw L2 capability gates remain closed.
