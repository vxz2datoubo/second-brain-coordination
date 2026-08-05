# E44 Exact-Head Receipt

- task_id: `CODEX-BRAINOPS-DURABLE-CHALLENGE-LEDGER-OWNER-SPECIFIC-TERMINAL-EVIDENCE-AND-CAPABILITY-GATE-CLOSURE-0040-E44`
- agent_id: `CODEX`; reviewer: `GPT`; route epoch: `46`; issue: `#138`; PR: `#139` Draft.
- canonical base and both observed remote-main reads: `1b61357b150ee5bf818a207c60b4b05b017e1cd7`.
- plan commit: `b11287914f48de595df6dddabd1e11cc0df38af4`.
- delivered substantive commit: `1f3e379efd9149722d7f3f210562fd91221e2da0`.
- delivered parent: `b11287914f48de595df6dddabd1e11cc0df38af4`.
- delivered tree: `2347987c7fa1e4b7e83907ed92e86790729b754f`.
- exact changed-file count: 25, limited to the E44 program surface and
  `.github/workflows/brainops-e44.yml`.

## Local Exact-Head Evidence

```text
PYTHONPATH=<program>/src py -3.12 -m unittest discover -s <program>/tests -p "test_e44_*.py" -v
exit=0; 83 tests; combined stream SHA-256=1f689d377c63c32cdca5931a05b3c57da44ccf92ea1ef7824bbac5f1792d99c3

PYTHONPATH=<program>/src py -3.13 -m unittest discover -s <program>/tests -p "test_e44_*.py" -v
exit=0; 83 tests; combined stream SHA-256=db1b1320568516000cf825ca7ab6a717a967f2622080397c44298e3e7956da4b
```

## GitHub Exact-Head Evidence

- workflow: `BrainOps E44 durable challenge contracts`.
- run `30771933119`, head `1f3e379efd9149722d7f3f210562fd91221e2da0`:
  Python 3.11 PASS and Python 3.13 PASS.
- run `30771929982`, same head: Python 3.11 PASS and Python 3.13 PASS.
- visibility comments: PR #139 comment `5160824688`; Issue #138 comment
  `5160824791`.

## Boundaries, Findings And Handoff

- No live authority write, Canary, App/Automation/CLI invocation, credential,
  private configuration, account, market-data or trade action occurred.
- The run retained two implementation discoveries: hash-typed recovery storage
  identity and same-object evidence-family/exit-code binding.
- Remaining UNKNOWNs are preserved in `UNKNOWN-REGISTRY.yaml`; this receipt
  does not claim a live trust root or runtime capability.
- Completion signal for GPT second pass:
  `CODEX_BRAINOPS_E44_DURABLE_CHALLENGE_OWNER_TERMINAL_CAPABILITY_GATE_READY_FOR_GPT_REVIEW`.
- Rollback: revert the receipt-only commit, then the substantive commit. No
  external authority state exists to restore.
