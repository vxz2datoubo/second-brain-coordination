# E48 Unplanned Improvement Ledger

| ID | Discovery | Decision | Reason | Status |
| --- | --- | --- | --- | --- |
| E48-IMP-001 | The first E48 GitHub workflow wrote generated provider evidence inside the checkout, making the release gate correctly return `WORKTREE_DIRTY`. | Move generated evidence to the runner temporary directory. | Preserves a clean source tree while retaining CI artifacts. | Implemented and CI verified |
| E48-IMP-002 | Mutation tests referenced `tests.*` module paths even though the directory need not be a Python package. A mutation could appear killed because the loader failed, not because the real test failed. | Load the named test with an explicit `tests` search path. | Each mutation now executes its intended test and produces real red evidence. | Implemented and locally verified |
| E48-IMP-003 | Durable CAS recovery needs a business-purpose identity, not only an operation name. | Add purpose-bound journal records inside the existing authority implementation. | Prevents replay across unrelated authorization stages without creating a parallel authority. | Implemented and tested |
| E48-PROP-001 | Final provider completion could later be aggregated from independently authenticated workflow evidence. | Propose only; do not implement in E48. | Requires a future task with trust-root and reviewer-contract decisions. | Proposal only |

## Scope guard

The implemented items are directly required to make the returned E48 gate executable and verifiable. The proposal remains outside E48 and has not changed policy, live authority, or deployment behavior.
