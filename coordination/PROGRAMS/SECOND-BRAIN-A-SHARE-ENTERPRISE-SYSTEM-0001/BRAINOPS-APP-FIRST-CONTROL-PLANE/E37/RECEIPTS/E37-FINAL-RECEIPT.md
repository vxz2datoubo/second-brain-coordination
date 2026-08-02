# E37 Final Evidence Receipt

## Identity and topology

- Task: `CODEX-BRAINOPS-CANARY-NONCE-AUTHORITY-AND-ROUTE-PROOF-CLOSURE-0032-E37`
- Agent: `CODEX`; requested profile: `gpt-5.6-sol/max/X4_MAXIMUM/P1_ENHANCED_BOUNDED`; actual profile: `ACCESS_NOT_EXPOSED`.
- Route epoch / Issue / Draft PR: `38` / `#114` / `#115`.
- Branch: `codex/brainops-canary-authority-proof-0032-e37`.
- Remote main at lease claim: `2dafb6383ceac86b2e06b16110067a6229a4d467`.
- Remote main before receipt: `4daccc90c36d2be510a3e1e607e216ed3ddf1a30`.
- Route recheck result: same E37 task, epoch, branch, READY status, execution allowed, and both automatic-dispatch and canary-execution false.
- Imported immutable source: PR `#113`, tested `7012ed7681d16d936d3ea5ce1311c13b5be46337`, receipt `d22aeffc30e5848f2e0cbdb22742ad129f386275`.
- Delivered and tested head: `0221d629a80afe1232ebe4b1e05a77af64940851`.
- Tested parent: `b38cfd6eb121fc0d942cd9eb8e30bcdbe9809ed0`.
- Tested tree: `d360e55583c1416f394fc81b463afe3a00dc5b98`.
- This receipt is the required single non-empty evidence-only commit. Its full SHA/tree are bound after push in the PR and Issue #114 anchor comment; no later commit is permitted.

## Delivered behavior

1. Approval consumption is unique on task, route epoch, canary ID, and nonce,
   and is inserted atomically with the event reservation and verified route
   evidence.
2. Approval acceptance requires a transient read-only comment document whose
   repository, issue/comment IDs, actor, issued time, body SHA256, canonical
   reference, and exact binding-payload hash all match the bound approval.
3. Route acceptance requires `refs/heads/main`, the exact expected main SHA,
   both canonical route paths, recomputed Git SHA1 blob identities, recomputed
   SHA256 content identities, and a non-future observation no older than 300
   seconds.
4. No canary, dispatch, App Automation, Codex CLI, GPT auto-review, service,
   credential, account, order, or trade was invoked.

## Exact changed files in the tested commit

```text
.github/workflows/brainops-e37.yml
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E37/AI_HANDOFF.yaml
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E37/IMPLEMENTATION-DESIGN.md
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E37/STATUS.yaml
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/E37/WPDCR-REPORT.md
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/canary.py
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/models.py
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/proofs.py
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/store.py
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests/test_e36_canary.py
coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests/test_e37_authority_proof.py
```

## Test evidence

- Local command: `py -3.13 -m unittest discover -s coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/BRAINOPS-APP-FIRST-CONTROL-PLANE/tests -p test_*.py -v`; exit `0`; `103` tests passed.
- Local compile command: `py -3.13 -c "import pathlib, py_compile; ...glob('*.py')"`; exit `0`.
- Required remote E37 workflow: [run 30721817476](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/30721817476), checkout `0221d629a80afe1232ebe4b1e05a77af64940851`, pull-request event, conclusion `success`.
- Remote jobs: Python 3.11 `91426733326` success; Python 3.13 `91426733335` success. Each ran the 103-test suite and source compilation on the tested head.
- Two independent local Git archive roots used the exact tested SHA. Both archives had SHA256 `c01bfc6228bcfbf762e4d7a560e8de533b2b3c2d77b96d220229ab1e21737daf`, size `971788` bytes, `420` extracted files, test exit `0`, and normalized output hashes: stdout `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; stderr `abf288ec21904fc978c4d3af4331e8dc076560538de206dda7cafaf63ebdd37b` after replacing only the elapsed-duration field.
- Local Python 3.11 is unavailable; this is a retained environment limitation, not a substitute or skipped CI requirement.

## Failures, skips, UNKNOWN, and recovery

- No test failures or intentional skips remain in the final tested head.
- Initial archive-harness attempts exposed Windows archive-extraction latency,
  native-stderr handling, and an unavailable convenience hash API. They did not
  alter the repository. The final archive run used process redirection and a
  compatible SHA256 implementation, then passed twice.
- Unknowns retained: signed webhook verification, live canary execution, and
  an automatic remote transport fetcher. They remain outside this task.
- Rollback: revert E37 task-owned commits in reverse order; PR #113 remains
  immutable and no live state needs restoration.

## Completion boundary

`CODEX_BRAINOPS_E37_CANARY_NONCE_AUTHORITY_ROUTE_PROOF_READY_FOR_GPT_REVIEW`

This is a pre-canary security closure only. Stop after publishing the receipt
and request GPT's independent second pass.
