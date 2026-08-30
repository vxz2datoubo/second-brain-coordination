# R169 bridge-provenance remediation

`migration_bridge` records are receipt-bound history markers, not an extensible
event category.  Validation reconstructs the expected migrated prefix from the
original v1 bytes recorded in the receipt.  It then compares the full actual
bridge set as ordered `(sequence, event_id)` pairs against the expected set.

This blocks an attacker who appends a content-correct bridge and recomputes all
ledger hashes: that event has no expected position or identity.  The same
validation boundary is used before save loading, state calculation, timeline
construction, director continuity access, and review-packet creation.

The tests also retain the two important predecessor behaviours: a genuine
terminal migration bridge is accepted only where the source requires it, and
the lossy `listen -> approach -> leave` legacy route fails without changing the
legacy file or creating a default save.
