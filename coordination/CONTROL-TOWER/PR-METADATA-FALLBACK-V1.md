# PR Metadata Fallback V1

Status: `BOUNDED_FALLBACK_TRANSPORT / NO_NEW_AUTHORITY`

## Purpose

Preserve a two-lane execution strategy for narrow GitHub pull-request metadata operations:

1. **Primary lane**: native ChatGPT GitHub Connector / canonical platform tooling.
2. **Fallback lane**: official GitHub API through `gh api`, used only after the primary lane returns a concrete transport/schema failure.

The fallback is not a second governance system. It carries no review, merge, code-write, branch-write, release, route, task, or domain authority.

## V1 supported operation

Only:

`mark_ready_for_review`

No merge, close, reopen, retarget, reviewer mutation, branch mutation, content write, release, or issue state mutation is supported.

## Mandatory gates

Before fallback execution:

- primary connector attempt must have failed for the requested operation;
- repository and PR number must be explicit;
- expected exact head SHA must be explicit;
- live PR must be `open`, `unmerged`, and match the exact head;
- GitHub CLI authentication must already exist outside this repository; no token is stored here.

After mutation:

- fresh PR readback is mandatory;
- exact head must still match;
- `draft` must be false;
- otherwise result is fail-closed.

## Audit receipt

A successful or idempotent execution returns `PR_METADATA_FALLBACK_RECEIPT/v1` with:

- operation
- repository
- PR number
- expected head
- before/after head
- before/after draft state
- transport identity
- status
- all-false authority vector
- deterministic receipt digest

The receipt is execution evidence only. It cannot authorize merge or review acceptance.

## Transport

V1 uses the official GitHub GraphQL mutation:

`markPullRequestReadyForReview`

The mutation response is not trusted alone. The postcondition is established by a separate REST PR readback.

## Failure semantics

Any of the following produces `FAIL_CLOSED` and no downstream authority:

- malformed expected SHA
- closed or merged PR
- head mismatch before mutation
- GitHub authentication/API failure
- GraphQL error
- head movement after mutation
- PR still Draft after mutation
- malformed readback

## Security / authority locks

The implementation must always report all of these as false:

- creates_task
- creates_route
- creates_work_claim
- grants_execution
- grants_code_write
- grants_branch_write
- grants_review_accept
- grants_merge
- grants_release
- expands_permissions

## Intended operational use

Example after a native Connector schema failure:

```bash
python coordination/CONTROL-TOWER/pr_metadata_fallback.py \
  --repo vxz2datoubo/ai-world-simulation-engine \
  --pr 96 \
  --expected-head 8651edec3ce0b9d3f140f4f920817e4abfa5830e \
  --operation mark_ready_for_review
```

The operator must then continue the ordinary governed canonicalization flow. This tool never merges the PR.
