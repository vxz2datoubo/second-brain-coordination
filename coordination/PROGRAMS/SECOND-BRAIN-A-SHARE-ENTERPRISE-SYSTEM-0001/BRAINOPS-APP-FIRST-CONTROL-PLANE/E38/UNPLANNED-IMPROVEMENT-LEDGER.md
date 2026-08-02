# E38 Unplanned Improvement Ledger

## R0-001: stable missing-policy result

- Trigger: a real public transport read reached the active route but initially
  compressed its empty actor policy into a generic semantic rejection.
- Boundary tests: same E38 trust goal; same source paths; no authority increase;
  reversible and covered by deterministic tests; no new dependency or cost.
- Action: normalize an empty actor list to
  `route_authorized_actor_policy_missing`.
- Validation: full 103-test suite and a second public read both passed.
- Rollback: revert the final E38 substantive commit.
- Outcome: retained. The result is actionable for GPT and cannot be mistaken
  for a network outage.

No other autonomous remediation was used.
