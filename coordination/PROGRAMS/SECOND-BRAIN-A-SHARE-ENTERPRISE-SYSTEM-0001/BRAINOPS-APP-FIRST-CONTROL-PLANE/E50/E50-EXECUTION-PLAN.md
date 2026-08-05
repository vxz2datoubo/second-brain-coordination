# E50 Execution Plan: Trusted Provider and Executable Release Validation

## Authority and frozen source

- Task: `CODEX-BRAINOPS-TRUSTED-PROVIDER-ATTESTATION-CORRECT-GIT-GRAPH-CLEAN-CLONE-REPRODUCTION-AND-STRICT-RECEIPT-VALIDATION-CLOSURE-0046-E50`
- Route epoch: `52`
- Canonical main at claim: `7481fb645e8fd7b032fab6451128eecfadfedfaa`
- Frozen E49 receipt head: `ee702cc596fd4aec3a0f9940f63ba914d5cb1bbd`
- Boundary: synthetic, public-safe engineering only; `research_only / NO_TRADE`.

E50 imports selected source paths and exact blobs from the frozen E49 receipt
head through an explicit manifest. It does not merge, rebase, cherry-pick, or
modify E49.

## Root correction

The E49 ancestry check compared stdout from `git merge-base --is-ancestor` to
the plan SHA. The command communicates ancestry through its exit status:
`0` is ancestor, `1` is not ancestor, and other results are unavailable. E50
will implement that distinction and prove it on a real temporary graph.

Provider authority uses the approved alternative to a direct provider adapter:
GPT creates a post-run, canonical-`main` attestation with immutable source
commit, blob and payload identities. The external envelope only carries those
identities and a byte-identical payload; it is not authority by itself. An
arbitrary JSON document, a caller marker, task-branch data, or an in-job
success statement is never final provider authority.

## Delivery stages

1. **Selected import and failing tests**
   - Import only E49 BrainOps modules and their required tests; record each
     selected path and blob hash.
   - Add initially failing tests for valid and invalid real git graphs, forged
     provider documents, strict receipt documents, and clean-clone execution.

2. **Trusted provider and graph contract**
   - Add a read-only GitHub REST adapter that records endpoint identity,
     response digest, requested head, and immutable run/job/artifact facts.
   - Correct ancestor evaluation by subprocess return code and preserve
     `not_ancestor` separately from command failure.
   - Reject branch-authored provider evidence in final validation.

3. **Strict receipt and clean-clone contract**
   - Parse every required receipt document, reject empty or malformed content,
     and cross-bind task, route epoch, agent, heads, provider facts, marker,
     and byte-exact completion signal.
   - Execute the documented final verifier command in an ephemeral clean clone
     with trusted provider material held outside the repository.

4. **Mutation and CI evidence**
   - Require active kills for ancestry stdout/return-code mistakes, forged
     provider documents, source substitution, schema omission, field changes,
     text-only commands, clean-clone bypass, completion-signal mismatch, and
     post-receipt commits.
   - Run exact-head Python 3.11 and 3.13 CI before and after the sole receipt.

5. **Receipt and independent review**
   - After tested-head CI succeeds, create exactly one nonempty receipt-only
     commit under `E50/RECEIPT/`.
   - Wait for receipt-head CI, then stop for GPT remote-head recheck. No
     post-receipt commit is allowed.

## Acceptance and exclusions

The final positive real graph must return `READY_FOR_INDEPENDENT_REVIEW`; a
non-ancestor graph, forged provider source, malformed receipt, stale command,
or changed remote branch head must fail closed. The implementation will not
invoke live authority, Canary, app automation, real Codex CLI, credentials,
accounts, orders, funds, market data, or trading.

## Recovery and reporting

Every material checkpoint records tests, failures, UNKNOWNs, changed paths,
and rollback. If the route changes, preserve the work with a visibility packet
instead of modifying frozen E49 or a later route.
