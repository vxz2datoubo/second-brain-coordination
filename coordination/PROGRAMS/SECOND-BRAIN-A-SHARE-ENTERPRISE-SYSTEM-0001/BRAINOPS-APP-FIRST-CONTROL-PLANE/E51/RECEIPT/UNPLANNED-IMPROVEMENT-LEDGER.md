# E51 Unplanned Improvement Ledger

task_id: CODEX-BRAINOPS-PROVIDER-OBSERVABLE-WINDOWS-EXACT-COMMAND-INDEPENDENT-VERIFICATION-AND-E50-MERGE-CANDIDATE-CLOSURE-0047-E51
route_epoch: 53
agent_id: CODEX
tested_head: 8853d436bb06dd3bcfb8a36e419cb1470cf3c75e
completion_signal: CODEX_BRAINOPS_E51_E50_PROVIDER_OBSERVABLE_FINAL_VERIFICATION_READY_FOR_GPT_REVIEW
receipt_commit_identity: EXTERNAL_POST_PUSH_GIT_FACT

1. The first workflow revision used `runner.temp` in a job-level expression,
   which GitHub rejected before any job. E51 now resolves `RUNNER_TEMP` inside
   the PowerShell execution step. The corrected provider run is retained.
2. Windows emits CRLF through a piped Python stdout stream. E51 preserves raw
   bytes and records their hash, then applies only CRLF-to-LF normalization for
   the pre-existing canonical E50 stdout digest. The command argv is unchanged.
3. Provider artifacts originally contained disposable clone scaffolding. The
   upload rule now excludes `scratch/**`; final artifacts contain five evidence
   files only and remain independently readable.
