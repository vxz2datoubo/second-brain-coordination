# Session State Machine

Implemented states:

- `DISCONNECTED`
- `CONNECTING`
- `WAIT_GREETING`
- `LOGIN_SENT`
- `AUTHENTICATED`
- `SUBSCRIBE_SENT`
- `STREAMING`
- `BACKOFF`
- `KICKED`
- `STOPPING`

Rules implemented in skeleton:

- subscribe is blocked before login success is verified
- KICK transitions to `KICKED`
- exponential backoff plus jitter is available
- credentials come from environment variables only when network runtime is explicitly enabled
- `connect()` raises while `allow_network=False`

Real socket loop remains WorkBuddy-owned runtime work.
