# R137 scope and postflight audit

agent_id: `CODEX`

Allowed implementation changes are confined to the R137 provider, the existing
R136 gateway adapter, package export, R137 tests, this R137 evidence folder and
its dedicated read-only CI workflow. The provider has no generic URL input,
credential input, private-repository support, write method, daemon, scheduler,
Control Tower decision, release authorization or merge behavior.

The old `F:\aidanao` worktree was not modified. The task uses only the isolated
clone at `F:\aidanao-worktrees\standalone-clones\r137-authority-live-observation-provider`.
Generated `__pycache__` entries remain unstaged and are not task deliverables.

Required final checks are intentionally pending until the implementation is
closed: Python 3.11/3.13 compile and tests, Phase-3 adapter/integrated
regression, YAML parsing, public-safety/privacy, placeholder/TODO/shadow/scope
audit, `git diff --check`, exact-head CI and an implementation PR. A PASS for a
mechanism test is not a policy PASS or a formal release.

R2 remains inside the same allowlist: proof binding, tree response validation,
test fixture/regressions, dedicated workflow checkout and R137 task evidence.
It does not add a provider, credential, host, endpoint, write method or new
authority. The next postflight replaces these pending statements only after the
R2 commit has remote exact-head evidence.
