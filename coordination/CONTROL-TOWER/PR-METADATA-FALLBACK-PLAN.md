# PR Metadata Fallback V1 Implementation Plan

State: `IMPLEMENTED_CANDIDATE / AWAITING_INDEPENDENT_REVIEW`

## User direction
Maintain two execution lanes and prefer the best/fastest/highest-value path. Use a governed fallback only when the primary native path is concretely unavailable.

## Scope
Implement one bounded fallback operation for GitHub PR metadata:

- `mark_ready_for_review`

The fallback must use official GitHub API semantics, exact-head fencing, before/after readback, deterministic receipts, and all-false authority.

## Non-goals

- no merge operation
- no code/content write operation
- no branch/ref mutation
- no issue state mutation
- no reviewer mutation
- no release authority
- no credentials in repository
- no replacement for the native Connector

## Acceptance

1. primary/fallback policy documented;
2. exact-head fence before and after mutation;
3. open/unmerged precondition;
4. idempotent already-ready result;
5. fail closed on GraphQL/readback/head movement/postcondition errors;
6. deterministic receipt with explicit all-false authority;
7. Python 3.11/3.13 focused CI;
8. independent exact-head review before canonicalization.

## Operational incident motivating V1

The native ChatGPT GitHub Connector `markPullRequestReadyForReview` wrapper failed on an obsolete `Repository.fullDatabaseId` response selection while PR #96 in `vxz2datoubo/ai-world-simulation-engine` remained Draft. The fallback is designed to avoid coupling the governed canonicalization pipeline to one connector response-schema defect.
