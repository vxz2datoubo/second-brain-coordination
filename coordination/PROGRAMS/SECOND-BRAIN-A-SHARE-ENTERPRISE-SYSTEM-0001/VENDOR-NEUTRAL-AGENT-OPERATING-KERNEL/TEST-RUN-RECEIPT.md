# Test Run Receipt - E31

`agent_id: CODEX`

## Route

- `task_id`: `CODEX-PEOS-0010-E30-COMMITTED-WPDCR-ARCHIVE-ROOT-AND-RECEIPT-ANCHOR-TRUTH-CLOSURE-0023-E31`
- `route_epoch`: `32`
- `reviewed_base`: `93b61b055e13c04431236214a599a9f0f325b3ce`
- `status`: `IN_PROGRESS`
- `authority`: `CANDIDATE_ONLY`
- `activation`: `DISABLED`
- `boundary`: `PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE`
- `completion_signal`: `CODEX_E31_PEOS_0010_COMMITTED_WPDCR_ARCHIVE_ROOT_AND_RECEIPT_ANCHOR_TRUTH_READY_FOR_GPT_REVIEW`

## Local verification

- focused E30 and E31 evidence tests: `37/37 PASS`;
- full candidate suite: `116/116 PASS` after installing the already-declared CI test dependencies;
- Python syntax check: `PASS`;
- YAML parse: `PASS`;
- candidate `ci_verify.py`: `PASS`, 116 cases, 24 Python files, 18 strict YAML files, 0 secret matches, 0 raw captures;
- local execution used the preserved E30 receipt tree and the E31 in-progress contract. Remote dual-Python and clean archive values are recorded only after the substantive commit run.

## E31 evidence gates

- semantic WPDCR section payloads are required instead of a list of names;
- the archive contract requires three distinct root identities, root-path hashes,
  archive hashes, root-contained commands, stream hashes and complete per-file
  path/size/SHA256 equality;
- the tested substantive parent and later receipt head are separate identities;
- the receipt is externally bound to the Draft PR head; its full SHA is published
  outside the self-referential commit after the final green run;
- incomplete identity markers, non-FINAL manifests, root drift and partial
  artifact inventories fail closed.

## Safety and scope

No real/private data, credentials, production, account, order or trade path was
accessed. Adapters, cross-model evaluation, Shadow, canonical promotion and
Gate C/D remain disabled. This receipt is not a merge or activation request.
