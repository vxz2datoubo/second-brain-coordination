# Gap and Backfill Design

`GapDetector` tracks configurable fields such as `event_sequence` and returns:

- `continuous`
- `duplicate`
- `gap`
- `reset_candidate`
- `out_of_order`
- `unknown_scope`

`MockHttpBackfillClient` implements the offline interface:

`TCP gap detected -> request HTTP backfill -> raw save candidate -> event-key reconciliation -> dedupe -> gap status update`

No HTTP network call is performed in this task.
