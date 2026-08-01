# Test Run Receipt - E31

agent_id: CODEX
actual_executor: CODEX
reviewer: GPT

## Route

- task_id: CODEX-PEOS-0010-E30-COMMITTED-WPDCR-ARCHIVE-ROOT-AND-RECEIPT-ANCHOR-TRUTH-CLOSURE-0023-E31
- route_epoch: 32
- reviewed_base: 93b61b055e13c04431236214a599a9f0f325b3ce
- tested_substantive_commit: fb30f1b8edc04ba2b4f50f1d45303145d9706d5e
- tested_substantive_tree: 288ba2d8e111cb11d51e4f40bbbc6fa5a88f308c
- receipt_parent_commit: fb30f1b8edc04ba2b4f50f1d45303145d9706d5e
- status: FINAL
- authority: CANDIDATE_ONLY
- activation: DISABLED
- boundary: PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE
- completion_signal: CODEX_E31_PEOS_0010_COMMITTED_WPDCR_ARCHIVE_ROOT_AND_RECEIPT_ANCHOR_TRUTH_READY_FOR_GPT_REVIEW

## Local verification

- focused E30 and E31 evidence tests: 37/37 PASS;
- full candidate suite: 116/116 PASS;
- Python syntax check: PASS;
- YAML parse: PASS;
- candidate ci_verify.py: PASS, 116 cases, 24 Python files, 18 strict YAML files, 0 secret matches, 0 raw captures;
- local workflow correction: PASS;
- local run used declared CI dependencies and no production integration.

## Remote verification

- workflow run: 30680004228, conclusion success;
- Python 3.11 job: 91314979165, 116/116 PASS;
- Python 3.13 job: 91314979146, 116/116 PASS;
- Python 3.11 artifact: 8811864904, digest sha256:a69cf56cd28f383dfcf708b1e585ecefb05de329985b73fb05929b963e567a97;
- Python 3.13 artifact: 8811865481, digest sha256:143a9b85d203cc703b3f2bbb04cf90a3e476ce544814a9f159bfe99f61306ef;
- final manifest: status FINAL, 3 roots per job, 58 artifacts per root;
- archive content SHA256: 2cdcf3116b56b491830187be906873973ea484a1c3e3b0233ad7fb45f5fb2c93;
- archive size: 2058240 bytes;
- content-tree SHA256: 9a325b3a69723ad7bc24810e5ff1b6415b7ba32ab6d9ac5599a66f4dbf408ea7;
- artifact-set SHA256: c789408b028b35bd12a5721797fbf127e12fb73c4a06e1083da410094c06a1ed;
- all roots share archive/tree/content/artifact hashes and have distinct root_path_sha256 values;
- root job identities are candidate-evidence-py3.11 and candidate-evidence-py3.13.

## Retained negative evidence

- Earlier E31 workflow 30679560837 failed during context resolution because the old primary identity key remained in the workflow; this was corrected without rewriting history.
- The first green E31 archive run 30679651468 exposed a semantic identity defect: its manifest top-level tested identity still pointed to the historical parent and its job label was runner-path derived. R1 corrected both and run 30680004228 passed.
- E30 synthetic roots and list-only WPDCR remain historical rejected inputs.

## Scope and safety

- No real/private data, credentials, production, account, order or trade path was accessed.
- Adapters, cross-model evaluation, Shadow, canonical promotion and Gate C/D remain disabled.
- This receipt is not a merge or activation request.

## External binding

The receipt-only commit is intentionally bound to the current Draft PR #107 head after it is created. Its full SHA and tree are published in the PR and Issue comments and in the final task response.

