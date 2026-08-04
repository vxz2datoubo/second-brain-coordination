# E51 Execution Plan: Provider-Observable E50 Final Verification

## Identity and boundary

- **Task:** `CODEX-BRAINOPS-PROVIDER-OBSERVABLE-WINDOWS-EXACT-COMMAND-INDEPENDENT-VERIFICATION-AND-E50-MERGE-CANDIDATE-CLOSURE-0047-E51`
- **Route epoch:** `53`
- **Claimed canonical main:** `bfcb7f65c3f1d862bcd17df2319803000c5c0ec9`
- **Frozen source:** E50 receipt head `9e87bc2f6e705b65a35b92f09d7e7848abc5768a`
- **Scope:** provider-observable, public-safe verification only.

E51 does not change, merge, rebase, cherry-pick, or otherwise mutate E50. It
does not access credentials, accounts, market data, orders, or trading. A local
success report is not final evidence: the required final facts must be readable
from a GitHub `windows-latest` run, job log, and uploaded artifact.

## Delivery topology

1. This commit changes this plan file only.
2. One implementation commit adds only the E51 verification workflow and
   public-safe E51 verification support files under the authorized E51 subtree.
3. GitHub Actions must execute the exact E50 receipt command on Windows for
   Python 3.11 and 3.13 at the implementation head.
4. After both jobs and their artifacts are independently visible, one nonempty
   receipt-only commit records immutable run, job, artifact, command, digest,
   outcome, negative-case, and unknown evidence. The receipt is final.

## Independent verification algorithm

For each matrix job, the workflow will:

1. Check out the exact event head and record the actual checkout SHA.
2. Re-fetch the canonical repository and prove the remote E50 branch resolves
   to the frozen receipt SHA before and after verification.
3. Re-read the canonical-main attestation from its fixed commit and path;
   independently check the fixed blob SHA-1 and payload SHA-256.
4. Create a disposable clone with `git -c core.longpaths=true`, then check out
   exactly the frozen E50 receipt head. The long-path setting is scoped to the
   disposable clone operation.
5. Generate the five-field envelope outside that clone from the canonical
   attestation bytes only: `source_commit`, `source_path`,
   `source_blob_sha1`, `payload_sha256`, and `payload`.
6. Materialize that envelope at the literal Windows path recorded in E50's
   committed `RECEIPT-MANIFEST.json`. No substitute path or verifier argv is
   permitted.
7. Load the `reproduction_command` JSON array from that manifest, replace only
   the manifest's documented `@HEAD` token with the disposable clone's verified
   E50 receipt head, and execute the resulting argv unchanged from the clone.
8. Require exit `0`, empty stderr, the canonical READY JSON line, and stdout
   SHA-256 `0e1c50869dd3818fa98794f6de671daefc11df3e5a19a161428c75fc1beee7e0`.
9. Run isolated negative variants for blob, payload, receipt head, completion
   signal, and a synthetic post-receipt commit. Each must fail nonzero and be
   recorded without masking the positive result.
10. Upload a public-safe artifact preserving exact argv, remote facts, clone
    head, attestation facts, envelope digest, stdout, stderr, exit codes, and a
    minimal environment summary.

## Fail-closed checks

The workflow fails rather than silently adapting when any canonical ref,
attestation commit/path/blob/payload digest, manifest shape, literal envelope
path, command token, checkout SHA, E50 remote head, expected stdout, stderr,
or negative-case behavior disagrees. It must not use event text, branch-local
copies, or reconstructed semantic equivalents as a substitute for the frozen
E50 facts.

## Acceptance and recovery

Acceptance requires both Windows Python matrix jobs at the exact tested head,
then both again at the final receipt head, plus independently readable logs and
artifacts. A failed exact-path materialization is evidence of a real portability
limit, not permission to change E50's command.

Rollback is isolated: delete only the unmerged E51 branch/PR after GPT review.
E50 remains frozen and byte-identical throughout. Completion is reported only
with `CODEX_BRAINOPS_E51_E50_PROVIDER_OBSERVABLE_FINAL_VERIFICATION_READY_FOR_GPT_REVIEW` and requires GPT's second pass.
