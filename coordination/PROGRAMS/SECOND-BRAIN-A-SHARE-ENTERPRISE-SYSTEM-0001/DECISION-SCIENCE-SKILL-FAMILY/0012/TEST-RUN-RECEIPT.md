# Test Run Receipt

`agent_id: CODEX`

`task_id: CODEX-W12-D0-COMBINED-SKILL-GAP-AND-LOCAL-REALITY-AUDIT-0013B`

`run_at: 2026-07-22 Asia/Shanghai`

`boundary: research_only / NO_TRADE`

## Environment

- Windows PowerShell `5.1.22621.6133`
- Python `3.13.13`
- Node `20.17.0`
- Git `2.47.0.windows.1`
- GitHub CLI `2.96.0`

## Executed Suites

| Scope | Working directory | Command | Result | Exit |
|---|---|---|---|---:|
| Phase 3 local adapter lineage | `F:/aidanao-codex-w12-d0-0013b/coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION` | `python run_all_tests.py` | 98 passed: 12 P1 + 25 P2 + 61 adapter | 0 |
| PR #57 canonical Phase 3 lineage | `F:/aidanao-codex-w12-d0-0013b/coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-INTEGRATED-OFFLINE-MEMORY` | `python run_all_tests.py` | 183 passed | 0 |
| PR #58 candidate worktree | `F:/aidanao-codex-p4-full-knowledge-gateway-0007/coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-3-INTEGRATED-OFFLINE-MEMORY` | `python run_all_tests.py` | 299 passed | 0 |
| Accessible local governance subset | `F:/aidanao` | `python -m unittest -q tests.test_indicator_knowledge_schema tests.test_foundation_data_governance tests.test_v01_super_brain tests.test_storage tests.test_realtime_l2_aggregate` | 59 passed | 0 |

The PR #58 suite includes the canonical memory lineage and is not added to it as
an independent capability count. The adapter plus PR #58 total is 397 distinct
tests. The local 59-test subset is a separate accessible-local evidence run.

## Known Limitation

A prior shared-root full discovery run exceeded 244 seconds and was safely
terminated. Its state is `TIMEOUT / NOT_PASSED`; this report does not convert it
to a pass. No broker, account, credential, realtime service or order path was
used by any listed command.
