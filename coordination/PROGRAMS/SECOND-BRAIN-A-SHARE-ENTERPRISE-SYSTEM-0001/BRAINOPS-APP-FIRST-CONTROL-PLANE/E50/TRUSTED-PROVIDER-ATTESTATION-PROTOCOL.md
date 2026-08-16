# E50 Trusted Provider Attestation Protocol

## Purpose and authority

E50 never treats a branch-authored JSON file, a workflow's self-declared
success, or a caller-provided envelope as final provider authority. After the
receipt-head CI runs, GPT alone creates a public-safe attestation on canonical
`main` at:

```text
coordination/PROVIDER-ATTESTATIONS/CODEX-E50-POST-RUN-PROVIDER-ATTESTATION.json
```

The committed payload must be one canonical JSON object followed by exactly one
newline. It binds the E50 task, route, agent, exact completion signal, tested
provider record and receipt provider record. The receipt record includes the
receipt head, the remote branch head and one completed-success run with both
Python 3.11 and 3.13 jobs and non-expired evidence artifacts.

## External verification envelope

The verifier receives an **external** JSON envelope, outside the clean clone:

```json
{
  "source_commit": "<canonical-main-attestation-commit>",
  "source_path": "coordination/PROVIDER-ATTESTATIONS/CODEX-E50-POST-RUN-PROVIDER-ATTESTATION.json",
  "source_blob_sha1": "<git-blob-sha1>",
  "payload_sha256": "<sha256-of-canonical-json-without-newline>",
  "payload": { "<byte-identical-committed-payload>": true }
}
```

The verifier performs a read-only `git fetch origin main`, proves that
`source_commit` is an ancestor of that fetched main, resolves the named blob,
and requires byte-for-byte equality between the committed payload and the
canonicalized envelope payload. The envelope cannot turn an uncommitted or
task-branch document into authority.

## Receipt binding and command

The receipt's `PROVIDER-EVIDENCE-TESTED-HEAD.json` contains only the tested
head's provider facts. GPT's canonical-main payload carries that document
byte-for-byte under `provider_evidence.tested`, plus receipt-head run facts
under `provider_evidence.receipt`. This avoids an impossible self-reference in
a receipt commit that cannot know its own final SHA before creation.

The final receipt must document this executable command shape exactly:

```text
python -m brainops_control_plane.e50_release_verifier --repository-root . --trusted-attestation <absolute-external-envelope> --base-head <base> --plan-head <plan> --tested-head <tested> --receipt-head @HEAD
```

The command is executed only in an ephemeral clean clone. It returns
`READY_FOR_INDEPENDENT_REVIEW` only after all topology, receipt, source,
provider and completion-signal checks pass.

## Failure and recovery boundary

Missing canonical-main attestation, a changed source blob, a non-main source,
changed provider facts, an unexecutable command, a post-receipt commit or an
unavailable Git graph fails closed. Once the E50 receipt commit is created,
Codex must not patch it: a later defect becomes a successor task. This protocol
stores no credentials, account data, market data or private provider payloads.
