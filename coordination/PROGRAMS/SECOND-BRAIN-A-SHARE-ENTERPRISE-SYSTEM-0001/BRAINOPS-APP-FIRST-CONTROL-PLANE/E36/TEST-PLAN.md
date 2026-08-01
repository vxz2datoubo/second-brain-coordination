# E36 Test Plan

The test suite uses only temporary SQLite files and synthetic identifiers.
It never calls a network, Codex automation, CLI execution, browser, service or
trading interface.

Required proof clusters:

1. exact lowercase SHA256 event payload identity;
2. all six approval bindings and expiry;
3. manual-owner exclusion and explicit CLI fallback permission;
4. absent approval, disabled automation, stale epoch, offline and paused-route
   failures before any reservation;
5. one persistent event effect and duplicate suppression;
6. synchronized route-state evidence written atomically with the event;
7. deterministic stale lease release and monotonic fencing;
8. value-aware redaction that reports category/path but never value.

The legacy E35 tests remain in the same suite to detect behavioral regression.
