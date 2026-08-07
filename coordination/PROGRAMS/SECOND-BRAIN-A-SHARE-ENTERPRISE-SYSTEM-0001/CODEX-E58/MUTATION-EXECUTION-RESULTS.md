# E58 genuine mutation execution evidence

| Field | Value |
| --- | --- |
| agent_id | `CODEX` |
| execution mode | Sequential temporary-copy mutations under `SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK` |
| catalog digest | `60d903f93584cbcc2bd8247aca81fffb1bd4e4662e94b51f56a5afb94a834e5b` |
| preflight / postflight Python count | `0 / 0` |
| peak task-owned child workers | `1` |
| unrelated processes terminated | `0` |
| mutation meaning | `killed=true` means the selected regression test rejected the temporary mutant; it does not mean a system process was terminated. |

Every mutation changed only a temporary copy of
`src/e58_runtime/semantic_execution.py`; each selected regression test exited
`1`; each temporary source was restored byte-for-byte before cleanup.

| Mutation | Audit blocker | PID | Before | Mutated | Restored | Selector |
| --- | --- | ---: | --- | --- | --- | --- |
| `E58-M-B1-CALLER-RECEIPT` | `E57-B1-CALLER-AUTHORED-EVALUATOR-RECEIPT` | 19520 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `33c77f0875adeec30b1afa90463cd4a9b1d47093dd7699993474e993985ff4a8` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_caller_constructed_receipt_is_rejected` |
| `E58-M-B2-NONOPPOSING-CONFLICT` | `E57-B2-NON-OPPOSING-CONFLICT` | 13844 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `f51dbcbc59b7692c36c0af30a3135609529a9cf33ec32209f913aa74096f2d71` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_unrelated_sources_are_not_a_conflict` |
| `E58-M-B3-CIRCULAR-RELATION` | `E57-B3-CIRCULAR-RELATION-EVIDENCE` | 20524 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `b09d7f7d7fbdaaa2235b14b0916f96d2dd0778afe4cc1162fbcb958d88ccf083` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_relation_rejects_unrelated_validated_subjects` |
| `E58-M-B4-ARBITRARY-POLICY` | `E57-B4-UNVERIFIED-REDACTION-POLICY` | 28256 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `4a3e664d6621a38069f178398679d88ca958c2bc6f74656a793228f3c475b1e3` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_redaction_rejects_unknown_policy` |
| `E58-M-B5-ISSUER-ON-VERIFIER` | `E57-B5-NO-PUBLIC-VERIFIER-ONLY-CAPABILITY` | 21280 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `df82047204cf2cb302350a7906795c5450e4869cfd319f6906dd323017c4219c` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_verifier_capability_has_no_issue_method` |
| `E58-M-B6-DROP-TERMINATOR-OWNERSHIP` | `E57-B6-JSONL-WHOLE-SOURCE-OWNERSHIP-INCOMPLETE` | 21364 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `1afe5ffd46fe578734f1405f3c1d95398b33ea8fd59cc7ec4e30461e3d91bea3` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_blank_lines_and_crlf_are_owned` |
| `E58-M-B7-ALLOW-ISOLATED-HIGH-SURROGATE` | `E57-B7-SURROGATE-EDGE-NOT-CLOSED` | 24540 | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `2d97b3142c87239273327b7ebea59886b101a5ace124b0a81217fc9c82c98d1e` | `3a19f9c4a1de43daf5d74eaaa7484f0a7ae04dbd80a91f4c8ff54cb3ffe95e8b` | `test_isolated_high_surrogate_is_stable_error` |

All replacements occurred exactly once. All seven results have `exit_code=1`,
`killed=true`, and `restored_exactly=true`.
