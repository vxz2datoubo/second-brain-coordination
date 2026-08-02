# E40R1 Unplanned Improvement Ledger

## B-E40R1-001: Accepted Control-plane Reuse

- Classification: `B_LEVEL_REUSE_REQUIRED_FOR_SINGLE_AUTHORITY`
- Change: imported the accepted E35-E39 BrainOps control-plane source and tests
  from frozen PR #121 into the sole E40R1 task-owned program directory.
- Reason: the accepted source was not on the E40R1 main baseline. Reusing it
  prevents a second evidence, reservation, or route-proof runtime.
- Alternatives considered: reimplementing the control plane (rejected: creates
  duplicate authority); copying unrelated old workflow files (rejected: outside
  the E40R1 allowlist).
- Evidence: 126 local tests and the E40R1 exact-head workflow.
- Rollback: revert the E40R1 substantive commit.

## A-E40R1-001: Workflow Reference Migration

- Classification: `A_LEVEL_TASK_BOUNDARY_ADJUSTMENT`
- Change: historical E37/E39 workflow-reference tests now inspect
  `brainops-e40r1.yml`, the only workflow E40R1 is authorized to add.
- Reason: their prior E38/E39 workflow targets are not part of this task's
  permitted paths.
- Validation: the full 126-test suite passes.
- Rollback: revert the E40R1 substantive commit.
