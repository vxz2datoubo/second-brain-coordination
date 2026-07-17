# Queue Version Handling

- Queue V1: uses `#` multi-record structure and generic raw queue fields.
- Queue V2: maps ask1/bid1 price, queue counts, seller 50-entry queue, buyer 50-entry queue.
- Without explicit version selection, queue payloads are marked `AMBIGUOUS_QUEUE_FORMAT`.

This avoids silently guessing queue semantics before WorkBuddy supplies real samples.
