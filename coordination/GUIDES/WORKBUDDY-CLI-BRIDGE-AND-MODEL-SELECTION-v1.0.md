# WorkBuddy CLI Bridge and Model Selection v1.0

This guide defines the local execution bridge between canonical GitHub task state and WorkBuddy/CodeBuddy CLI. It is governance guidance, not an active task and not credential storage.

## 1. What GitHub can and cannot do

GitHub can publish canonical task state, route/claim/lease/snapshot/batch identity, model assignment and a launch intent. GitHub cannot by itself start a process on a user's workstation unless a local execution mechanism exists.

Supported execution patterns:

1. **Preferred: local canonical-task watcher.** A small local daemon/poller reads remote canonical `main`, validates the active WorkBuddy task and launches CodeBuddy only when all gates match.
2. **Alternative: explicitly governed self-hosted runner.** Use only with hardened trust boundaries. Do not make an unrestricted self-hosted runner on this public coordination repository the default.
3. **Manual start.** User launches CLI after GPT publishes the task. WorkBuddy still reads canonical GitHub task truth and executes without a second user start command.

## 2. Model selection

Governed WorkBuddy tasks must never leave the model implicit.

### DeepSeek V4 Pro

Use for core implementation, architecture-sensitive code, complex debugging, cross-module refactoring, migrations and long-horizon autonomous work.

Example primary launch:

```bash
codebuddy --model deepseek-v4-pro
```

### DeepSeek V4 Flash

Use for bounded repetitive work, fixtures, regression matrices, boilerplate, simple adapters, data/schema transforms, lint/type/docs cleanup and broad low-risk verification.

Example primary launch:

```bash
codebuddy --model deepseek-v4-flash
```

### Hybrid Pro + Flash

Use Pro as the primary/reasoning model and Flash as the lightweight/background model when one task contains a hard core plus a large repetitive tail.

Local environment example:

```bash
export CODEBUDDY_MODEL="deepseek-v4-pro"
export CODEBUDDY_BIG_SLOW_MODEL="deepseek-v4-pro"
export CODEBUDDY_SMALL_FAST_MODEL="deepseek-v4-flash"
export CODEBUDDY_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
codebuddy --model deepseek-v4-pro
```

The exact variables available in a deployed client must be verified against the installed WorkBuddy/CodeBuddy CLI version before relying on them.

## 3. Canonical watcher launch algorithm

A local watcher MUST fail closed.

1. Fetch remote canonical `main` from `vxz2datoubo/second-brain-coordination`.
2. Read `AGENTS.md` and `coordination/WORKBUDDY-TASK-ROUTER.md`.
3. Read `coordination/GOVERNANCE/GPT-WORKBUDDY-ENGINEERING-FACTORY-PROTOCOL-v1.0.yaml`.
4. Read `coordination/ACTIVE-WORKBUDDY-TASK.yaml`.
5. Require `status: READY` and `execution_allowed: true`.
6. Resolve and read the bound route, Work Claim, lease, reservation, prewrite snapshot and executable batch.
7. Verify exact identity agreement: repository, task_id, route_epoch, issue, base, branch, completion signal and lease fingerprint.
8. Verify model assignment exists and is one of the governed profiles.
9. Verify no newer canonical task supersedes the route.
10. Verify single-writer/write-scope constraints.
11. Verify implementation-branch creation/base rules.
12. Refuse to read API keys from GitHub task files. Credentials remain local only.
13. Create a local launch receipt keyed by `task_id + route_epoch + lease fingerprint` before launch to prevent duplicate execution.
14. Construct the CLI command using the governed model profile.
15. Launch WorkBuddy/CodeBuddy.
16. WorkBuddy immediately executes `读取任务` semantics from canonical GitHub state.
17. On completion/blocker, publish the governed return package and stop or continue only according to the batch contract.

## 4. Dispatch-to-command mapping

| model_profile | primary | local launch |
| --- | --- | --- |
| `DEEPSEEK_V4_PRO` | `deepseek-v4-pro` | `codebuddy --model deepseek-v4-pro` |
| `DEEPSEEK_V4_FLASH` | `deepseek-v4-flash` | `codebuddy --model deepseek-v4-flash` |
| `HYBRID_PRO_WITH_FLASH_LITE` | `deepseek-v4-pro` | Pro primary + local Pro reasoning / Flash lite bindings |

A bridge may add noninteractive flags only when the installed CLI supports them and the task boundary permits them. Noninteractive execution must never bypass HIGH/CRITICAL safety prompts.

## 5. Why a local watcher is preferred here

The coordination repository is public. A self-hosted runner attached to a public repository can create an unnecessarily large trust surface if workflow triggers or permissions are misconfigured. A local watcher can be narrower:

- read canonical main only;
- accept only one exact task schema;
- require explicit READY/execution_allowed/lease/model identity;
- keep credentials local;
- launch only preconfigured commands;
- write a local duplicate-launch receipt;
- refuse candidate-branch execution.

If a self-hosted runner is later adopted, it should be a separately governed capability with explicit repository/event/actor allowlists, isolated credentials, sandboxing and no generic shell execution from untrusted PR content.

## 6. New-window behavior

A new GPT engineering window should not ask the user to explain this workflow again. It must fresh-read canonical GitHub state, then decide:

- GPT direct implementation for small bounded work;
- V4 Pro for deep/core WorkBuddy work;
- V4 Flash for repetitive/low-risk WorkBuddy work;
- Hybrid for hard-core + bulk-tail tasks.

Before dispatching WorkBuddy, GPT must tell the user the exact chosen model profile and the reason.

A new WorkBuddy session should not rely on a pasted historical prompt as task truth. The prompt only bootstraps behavior; the task itself comes from canonical GitHub route/claim/lease/batch state.

## 7. Credential boundary

Never commit `DEEPSEEK_API_KEY`, `CODEBUDDY_API_KEY`, cookies, tokens, local auth databases or equivalent secrets to GitHub. Use local environment variables or local WorkBuddy/CodeBuddy model configuration.
