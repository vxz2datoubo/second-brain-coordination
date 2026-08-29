# PR Metadata Fallback V1

Status: `BOUNDED_FALLBACK_TRANSPORT / NO_NEW_AUTHORITY`

## Purpose

Preserve a two-lane execution strategy for narrow GitHub pull-request metadata operations:

1. **Primary lane**: native ChatGPT GitHub Connector / canonical platform tooling.
2. **Fallback lane**: official GitHub API through `gh api`, used only after the primary lane has a concrete transport/schema failure that has been registered as canonical incident evidence.

The fallback is not a second governance system. It carries no review, merge, code-write, branch-write, release, route, task, or domain authority.

## V1 supported operation

Only:

`mark_ready_for_review`

No merge, close, reopen, retarget, reviewer mutation, branch mutation, content write, release, or issue state mutation is supported.

## Mechanical primary-failure eligibility

Fallback eligibility is **not** a caller-supplied boolean, dataclass, receipt, URI, or free-form string.

The runtime always reads the fixed registry:

`vxz2datoubo/second-brain-coordination@main:coordination/CONTROL-TOWER/PR-METADATA-FALLBACK-INCIDENTS.json`

A fallback operation is eligible only when canonical `main` contains exactly one `ACTIVE / SINGLE_TARGET_EXACT_HEAD` incident matching all of:

- repository
- PR number
- expected exact head
- operation
- `primary_transport=CHATGPT_GITHUB_CONNECTOR`
- non-empty failure fingerprint
- non-empty evidence references

The caller cannot choose an alternate registry path/ref and cannot submit its own primary-failure evidence object. A target that is not already registered on canonical main fails closed before the PR is mutated.

This makes the fallback an incident-scoped transport exception rather than a standing second write lane. Registering a new incident requires the ordinary governed canonicalization path for this repository.

## Mandatory live-state gates

Before mutation:

- canonical incident eligibility must pass;
- repository and PR number must match that incident;
- expected exact head SHA must match that incident;
- live PR must be `open`, `unmerged`, and match the exact head;
- GitHub CLI authentication must already exist outside this repository; no token is stored here.

After mutation **and after an idempotent already-Ready observation**:

- a second fresh PR readback is mandatory;
- exact head must still match;
- PR must still be open and unmerged;
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
- canonical incident id
- canonical incident-registry ref
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
- no unique matching ACTIVE canonical incident
- closed or merged PR
- head mismatch before mutation
- GitHub authentication/API failure
- GraphQL error
- head movement after mutation or idempotent readback
- PR re-drafted after idempotent readback
- PR closed/merged after idempotent readback
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

The current canonical incident candidate is scoped only to AWRSE PR #96 exact head `8651edec3ce0b9d3f140f4f920817e4abfa5830e`, whose native Connector Ready mutation failed on the `Repository.fullDatabaseId` schema selection.

After this fallback and its incident registry are independently accepted and canonicalized, the bounded invocation is:

```bash
python coordination/CONTROL-TOWER/pr_metadata_fallback.py \
  --repo vxz2datoubo/ai-world-simulation-engine \
  --pr 96 \
  --expected-head 8651edec3ce0b9d3f140f4f920817e4abfa5830e \
  --operation mark_ready_for_review
```

The operator must then continue the ordinary governed canonicalization flow. This tool never merges the PR.
