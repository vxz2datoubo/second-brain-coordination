# E54 Work Package Decision Record

## WP0: clean successor boundary

**Decision:** E54 begins from canonical `main` and preserves E53 strictly as
frozen evidence. It creates no whole-branch integration path.

**Reason:** E53's receipt-only topology and independent review make append or
branch merge invalid. A source-selection ledger provides accountability without
trust transfer.

## WP1-WP3: re-author the authority core

**Decision:** Replace, rather than verbatim copy, E53's authority package.

**Reason:** Its public method names are useful design references, but the
reviewed implementation contains nested alias, ownership, relation, and packet
verification defects. Rewriting makes each corrected guard independently
testable and mutation-addressable.

## WP4: checkpoint branch

**Decision:** Publish one public-safe checkpoint branch, not an intermediate
commit on PR #174.

**Reason:** the visibility protocol requires remote reviewability for material
local progress while final topology requires only one substantive and one
receipt commit after the plan head.

## WP5: Provider as execution evidence, not authority by itself

**Decision:** build a deterministic six-job matrix and byte comparator, then
defer authority credit to GPT's independent review.

**Reason:** E53 showed that a green provider run can still certify an incomplete
invariant surface.
