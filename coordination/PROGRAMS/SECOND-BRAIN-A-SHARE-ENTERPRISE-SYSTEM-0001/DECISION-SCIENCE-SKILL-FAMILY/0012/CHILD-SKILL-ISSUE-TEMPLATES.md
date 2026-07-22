# Child Skill Issue Template

Use one Issue per authorized phase or vertical skill. Creating Issues is outside
this D0 task.

```yaml
task_id: "<stable task id>"
skill_id: "<DS id or D1>"
mode: "project_plan_then_target_execution"
boundary: "research_only / NO_TRADE"
owner: "CODEX"
reviewer: "GPT"
authoritative_base_sha: "<remote main sha>"
reuse_contracts:
  - "<canonical owner and exact interface>"
forbidden_duplication:
  - "memory"
  - "market facts"
  - "hard risk"
  - "portfolio allocation"
  - "execution / OMS"
inputs:
  - "<versioned contract>"
outputs:
  - "<versioned candidate contract>"
unknowns:
  - "<unresolved evidence or rule>"
tests:
  - "schema round-trip"
  - "UNKNOWN preservation"
  - "point-in-time leakage guard"
  - "negative and adversarial cases"
acceptance:
  - "actual command, environment, exit code and artifact hash"
rollback:
  - "freeze/unregister candidate without erasing evidence"
stops:
  - "credential, broker, service or trade path required"
  - "canonical ownership conflict"
  - "official rule or point-in-time evidence missing"
```

Every child task must bind its own `TaskImpactForecast`, isolated `codex/`
branch/worktree and explicit write scope. No child task inherits an authorization
to implement another child.

