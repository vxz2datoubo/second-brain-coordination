# W12 D0 Decision Log

- `DL-001` Use remote `main` SHA `64a42895e49b31f4aa1de62d6db54bf54d4a555a` as the only valid base after the 2026-07-22 boundary-decision update.
- `DL-002` Keep Issue #38 and PR #58 paused and preserved; W12 must reuse their canonical contracts.
- `DL-003` Treat Gap Compiler as D1 meta-infrastructure, not one of the three child vertical slices.
- `DL-004` Default first child slices are DS-01, DS-02 and DS-10, subject to D0 evidence confirmation.
- `DL-005` Do not commit from the temporary stale worktree base. Retry a fast-forward before the first commit.
- `DL-006` Local facts require an opened file plus exact path, SHA256 and inspection command; otherwise use `ACCESS_NOT_AVAILABLE` or `UNKNOWN`.
- `DL-007` Documentation and schemas never prove executable or A-share-validated capability on their own.
- `DL-008` Do not modify the three protected local blueprints in this D0 task; report their backwrite state only.
- `DL-009` Repeated git HTTPS fetch attempts timed out while the GitHub REST API remained available. Publish through the Git Data API only if the new commit parent is the exact authoritative `main` SHA and its tree is based on that commit.
- `DL-010` Terminal display mojibake is not accepted as path evidence; UTF-8 file bytes were independently checked and retain the correct Chinese paths.
- `DL-011` Absorb `W10-W11-W12-CROSS-MODULE-BOUNDARY-AND-P0-REMEDIATION-v1.0.md`: DS-02 owns the shared ProbabilityEstimate computation/schema, W10 freezes references, W11 consumes read-only, and no parallel probability object is introduced.
- `DL-012` Six unnamed ghost capabilities remain evidence-unresolved. Numbered placeholder slots record the missing identities; no maturity downgrade is executed without names and paths.
