# Test Run Receipt — E30

`agent_id: CODEX`

## Primary status

- `task_id`: `CODEX-PEOS-0010-E29-WPDCR-ARCHIVE-MANIFEST-CURRENT-REVIEW-PACKET-AND-RECEIPT-TRUTH-CLOSURE-0022-E30`
- `route_epoch`: `31`
- `reviewed_base`: `d64c1ee2d3fc3e6a70a5b20d0720de60d320970a`
- `status`: `IN_PROGRESS`
- `authority`: `CANDIDATE_ONLY`
- `activation`: `DISABLED`
- `boundary`: `PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE`
- `completion_signal`: `CODEX_E30_PEOS_0010_E29_WPDCR_ARCHIVE_MANIFEST_PACKET_AND_RECEIPT_TRUTH_READY_FOR_GPT_REVIEW`

The E30 primary tested commit and tree are pending the substantive commit.
They must be filled before the receipt-only commit and may not use an older
E29 or pre-E29 identity.

## Commands

```text
python -B coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL/run_all_tests.py
python -B coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL/ci_verify.py --changed-files <changed-files.txt> --commit <tested-commit> --tree <tested-tree>
```

## Current local evidence

- E30 focused evidence tests: `12/12 PASS`;
- full local suite: `NOT_COMPLETE` because the selected local Python environment
  lacks the already-declared CI dependency `jsonschema==4.25.1`;
- no dependency was installed or changed by E30;
- remote Python 3.11/3.13 evidence remains required after push.

## E30 evidence requirements

- three distinct archive root identities;
- root-contained command, exit code, stdout hash and stderr hash per root;
- identical relative artifact path/size/SHA256 set in all roots;
- non-empty autonomy and model-profile WPDCR overlays;
- fail-closed negative tests for stale identity, repeated roots, external paths,
  artifact drift, missing stream hashes, non-zero exits, stale remaining work
  and wrong completion signal.

## Historical lineage (not primary)

The following values are retained only for lineage and cannot satisfy E30:

- E29 functional tested head: `686518aa93e37613d6c8e4ab936d0fdd816b403c`;
- E29 receipt head: `d64c1ee2d3fc3e6a70a5b20d0720de60d320970a`;
- earlier pre-E29 receipt evidence is historical and not an E30 authority.

## Safety

No real/private data, credentials, production, account, order or trade path was
accessed. K3/K4 and Shadow remain disabled. The Draft PR must not be merged by
this task.
