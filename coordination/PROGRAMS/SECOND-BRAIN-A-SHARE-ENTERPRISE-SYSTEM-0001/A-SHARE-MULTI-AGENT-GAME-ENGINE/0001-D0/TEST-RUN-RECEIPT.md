# Test Run Receipt

Status: `TESTED_PENDING_RECEIPT_ANCHOR`.

This receipt covers the complete D0 delivery surface at tested commit
`e5ac551e15d804417f1e1c1d8fa77f0032a7bb23`. The receipt-anchor commit is
created separately and must change only receipt metadata; it is intentionally
not amended into the tested commit.

## Executed validation

| Check | Result | Evidence |
| --- | --- | --- |
| Strict YAML parsing, including duplicate-key rejection fixture | PASS | 24 YAML files parsed; fixture rejected duplicate keys. |
| JSON parsing | PASS | 1 JSON Schema parsed. |
| Required deliverable presence | PASS | 36 required files present. |
| Cross-contract token coverage | PASS | Required latent-type, evidence, A-share constraint and gate tokens present. |
| Git whitespace check | PASS | `git diff --check` returned exit code 0. |
| Allowed-path review | PENDING_FINAL_RECHECK | Re-run after receipt-anchor commit. |
| Generic public-safety review | PARTIAL_EVIDENCE | SHA-shaped strings were reviewed as Git provenance only; no value-bearing credential scan was executed. |

The first strict validation run failed closed because the literal
`HiddenTypePosterior` was missing from the archetype ontology. The ontology was
corrected by making both required candidate contract types explicit, then the
full validator passed. This finding is preserved rather than silently erased.

## Command evidence

1. `python -` with the inline strict package validator: exit code `0`.
   Normalized stdout SHA256:
   `e2d3db208d6361f35cc32082d4abd032da297ab2f90cf34c9c1fe055f378589b`.
   Normalized stderr SHA256:
   `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
   Output: `static-contract-validation: PASS`; `required-files: 36`;
   `yaml-files: 24`; `json-files: 1`; `duplicate-key-rejection: PASS`.
2. `git diff --check`: exit code `0`.
3. `rg -n --pcre2 '[A-Fa-f0-9]{40}' <D0-path>`: exit code `0`; only expected
   Git provenance identifiers were observed during review.

Two attempts to capture a broader scan through the shell tool were blocked by
the local tool policy before execution. They are recorded as
`NOT_EXECUTED_TOOL_POLICY_BLOCKED`, not as passed scans. No real data, replay,
backtest, MARL, account or trade test was run because D0 explicitly prohibits
those activities.
