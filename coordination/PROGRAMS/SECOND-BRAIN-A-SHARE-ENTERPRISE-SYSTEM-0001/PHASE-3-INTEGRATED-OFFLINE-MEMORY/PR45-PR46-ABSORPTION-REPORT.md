# PR #45 and PR #46 Absorption Report

`agent_id: CODEX`

## PR #46 base

The integrated package retains the candidate SQLite store, atom/relation/conflict/unknown/packet/revision/audit model, candidate fusion, retrieval, snapshot and rollback responsibilities. It changes manual FTS indexing to automatic transactional indexing and replaces whitespace-only token lookup with deterministic multilingual terms.

## PR #45 capabilities

The package absorbs NFKC normalization, canonical JSON hashing, content-addressed atom/relation/packet IDs, deterministic idempotency and the semantic expectations represented by Cases A-F.

## Explicit exclusions

- generated `pipeline_output/`
- `_push_pr.py` and report-generation helpers
- generated SQLite files and snapshots
- old nested package layout
- any authority promotion or credential-value transport

PR #46 remains the historical source for the candidate memory base, and PR #45 remains the historical capability source. This package is the single Phase 3 implementation target; it does not create a second memory authority.
