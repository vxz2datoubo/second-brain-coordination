# E57 Receipt Boundary

## Identity and boundary

| Field | Value |
| --- | --- |
| Task | `CODEX-E56-POST-RECEIPT-ORDINARY-CALLER-CAPABILITY-REGISTRY-SEMANTIC-RECORD-RAW-DECODED-DUAL-PROVIDER-ANCHOR-AND-RECEIPT-CLOSURE-0053-E57` |
| Agent | `CODEX` |
| Route epoch | `59` |
| Canonical main read before receipt | `437b0f7e1a78d868342a0a4b205e47ffb719aebb` |
| Tested parent | `7eb7f0fd4bb2e60622bd4f177a128355a39d0430` |
| Tested parent tree | `207f5383ed02314565c27fab2faeb92df95f3d1f` |
| Tested Provider run | `31123089194` |
| Tested Provider status | `completed/success` |
| Completion signal reserved for the external anchor | `CODEX_E57_CAPABILITY_REGISTRY_SEMANTIC_RECORD_DUAL_PROVIDER_RECEIPT_AUTHORITY_READY_FOR_GPT_REVIEW` |

This commit is intentionally a receipt-only direct child of the tested parent. It
does not assert that receipt-head Provider evidence already exists. The receipt
head must obtain, and be independently checked against, a separate seven-job,
thirteen-artifact Provider run before an external completion anchor is published.

## Tested-head evidence independently reconstructed

The tested evidence was downloaded through public GitHub Actions artifact APIs
into a temporary directory. Verification code was expanded from an exact
`git archive` of the tested parent rather than loaded from the mutable worktree.
All thirteen archives, their required inner payloads, and the compare payload
were read as bytes.

| Check | Result |
| --- | --- |
| Expected jobs | `7`, all `success` |
| Expected artifacts | `13`, all downloaded |
| Canonical inner payloads | `6`, byte-identical |
| Canonical SHA-256 | `4dbd42dee9255bfa41896fb431323089e569dccf9a65ebf8635662e59e57e619` |
| Provider compare artifact | `8975000691` |
| Provider compare payload SHA-256 | `a9df6c4b1829c7b54798e6dc141aade54c550c905baf29632a6482037427ccd5` |
| Provider verifier-output SHA-256 | `a52af31b8a085d273aa19a47167d81b44089e7d4b91671c25d46733073f0b6b2` |
| Independent proof digest | `2b9f6fbb9e844ebdc91734b188849c024e68567679d9f38d385d734afabc321d` |
| Independent proof JSON SHA-256 | `ddce06b7038d135e8e070ce1324208e4cebf694fac54d12e83c51007ad7f9994` |

The public checkpoint packets are recorded on Issue #190 and Draft PR #191:
`5209634942` and `5209635162`.

## Commands and results

| Operation | Result |
| --- | --- |
| `git fetch origin main --prune` and route re-read | exit `0`; route remained `READY` with `execution_allowed: true` |
| `git archive --format=tar 7eb7f0fd...` then isolated extraction | exit `0`; archive SHA-256 `30da33956e40367d50bca1ed4cd1c20c908ae7952abeb95aa4d98a83e1426699` |
| Public Actions API retrieval for run/jobs/artifacts | exit `0`; exact head, seven jobs and thirteen artifacts verified |
| Isolated byte verification | evidence proof written in temporary storage; six canonical bytes equal and compare payload agreed |
| Earlier local product exercise | two runs exited `0`; `55` unittest cases and `15` genuine mutations per run; identical canonical SHA-256 above |

## Preserved negative evidence

1. The task-local collector expected `gh api --output`, but installed GitHub CLI
   `2.96.0` rejects that flag. A temporary binary-stdout downloader was used for
   the frozen tested-head verification; no source change was made during this
   receipt transition.
2. An initial Windows archive pipe invocation had a quoting failure before any
   artifact download. The subsequent `Start-Process` byte redirection and
   extraction succeeded.
3. Historical run `31120300037` remains a preserved external-infrastructure
   failure: hosted runner action download reported `Service Unavailable` before
   product execution. It does not count as tested or receipt evidence.

## Receipt-head obligations

After this receipt commit is pushed, the only permitted completion path is:

1. obtain a separate exact-receipt-head Provider run;
2. independently download all thirteen receipt artifacts and verify their ZIP
   and required inner bytes;
3. verify the tested and receipt evidence sets together, then execute exact
   topology and history-hygiene checks;
4. publish the literal completion anchor to Issue #190 and Draft PR #191;
5. make no later commit, merge, force-push, rebase, amend, or history rewrite.
