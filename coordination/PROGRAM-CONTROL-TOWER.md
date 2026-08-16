# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T22:02:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R138-DOMAIN-CAPABILITY-EXECUTION-PROVIDER` | 138 | `READY` | `true` | #366 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `true` | CODEX_IMPLEMENTATION_COMPLETION_SIGNAL_THEN_INDEPENDENT_GPT_EXACT_HEAD_REVIEW_NO_MERGE |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | EXPLICIT_USER_START_THEN_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | CONSUME_FROZEN_BOUNDARIES; REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 6 paths | epoch 138 · #366/#None |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R136 已完成并关闭**。
- **R137 已实现、验收、合并并 post-merge closed**。Accepted head `a7789864eac267c569503342a66a961985a27745`; implementation merge `54ba6c31240d4b262c65d142be446e6b5ea5d90b`; closure PR #365 merge `758064867bc51eb765f73b9b4941a575edbdfb1e`; final closure main `8d69e3b7c27ac8f4fb42a15b8065be8738a9afa2`。
- **R138 architecture 已接受并合并**。Issue #366；PR #367 exact head `233bd9fe817e45d1dbf837c116de498206db6f52`；merge `e76fe35d720f5f4739f80c62d3e6204f8fe52d9b`。
- **R138 非执行 reservation 已 canonical**。PR #368 merge `4dba0bdafec22a878c2de4cb25bc5d0b47c0fe8a`；post-reservation reconciliation PR #370 merge `98cb9265e526bc2f0707579dd7fe06b90dfdc44c`。
- **用户已明确启动 R138**：`启动 R138`。该命令只授权 R138 activation，不授权实现结果 merge 或任何后继任务。
- **fresh R137 provider activation observation 已真实完成**。Evidence-only PR #371 exact head `2942a2e3dd9e6cc1f4d96ec584275fbd43320aa4`，workflow `31951628708`；Python 3.11/3.13 均通过 R137 49/49 + R136 47/47，并分别产生新的 mechanism-backed proof；两者都观察到 canonical main `98cb9265e...`、R138 task、epoch 138。PR #371 已关闭且未 merge，临时 invoker 没进入 main。
- **R138 activation reconciliation 已生成**：`coordination/CONTROL-TOWER/R138-ACTIVATION-RECONCILIATION.yaml`。同代理、资源、O0-O4、私有/密钥、域 authority 和 AI Film 只读边界扫描没有发现当前 blocker。
- **R138 当前 activation 状态**：`READY / execution_allowed=true / runtime_code_change_allowed=true`，但只有本 activation PR exact-head CI 通过并由 GPT merge 后才成为 canonical execution authority。
- **唯一实现写面仍是 6 个 exact paths**。不能借 activation 扩成 generic shell/network、private repo/token、AI Film/domain/W3 write、Harness/H2/H7、daemon/live/production、permission/secret、Formal Skill、trading 或 Codex merge。
- **V1 primary class**：`EXACT_REPOSITORY_EXECUTABLE`。Tool/connector class 仍 contract-only；model-mediated cognitive scans 没有 domain-owned executable contract 时必须保持 `UNKNOWN`。
- **执行成功 ≠ 结论正确**。CapabilityExecution evidence 只证明 exact governed capability 真的跑过；process compliance 与 outcome quality 永久分离。
- **AI Film 继续独立 authority**，exact reference `44c383afd2207a97caf45b1b0da6ee1dece43a76`；Golden Case ingestor 只是候选 named executable smoke，不得证明无关认知扫描。
- **persistent R137 workflow invoker hardcode gap 继续保留**：provider 本体已证明 successor-capable，但旧永久 wrapper 固定 R137/137。R138 activation 使用的临时 successor-capable invoker 已关闭未合并；未来 wrapper 泛化需单独治理，不能静默混入 R138 实现。
- **Lane B 继续 user-held / NO_TRADE**；Lane C closed/frozen。

## R138 activation evidence

- Issue: `#366`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R138-DOMAIN-CAPABILITY-EXECUTION-PROVIDER`
- Route epoch: `138`
- Mode: `【Codex模式：项目计划模式】`
- Activation base main: `98cb9265e526bc2f0707579dd7fe06b90dfdc44c`
- Activation reconciliation: `coordination/CONTROL-TOWER/R138-ACTIVATION-RECONCILIATION.yaml`
- Fresh evidence PR: `#371` / **CLOSED_UNMERGED**
- Fresh evidence head: `2942a2e3dd9e6cc1f4d96ec584275fbd43320aa4`
- Fresh workflow: `31951628708`
- Py3.11 job: `95175843553`
- Py3.13 job: `95175843672`
- Py3.11 proof: `provider://r137/evidence/r137:2ba08eeeb1846e5f075f6531#sha256=2e6204cbfaff2a4834a0b28955b4e436f855967fc17529f347d149584ce309e9`
- Py3.13 proof: `provider://r137/evidence/r137:59cbd8250f1f232d2fb40c0a#sha256=d0cce4e61c1582ce1fb7361a70ae2ad3b96525a1bdc29a829bf3146801e10bd6`
- Planned implementation branch: `codex/r138-domain-capability-execution-provider`
- Execution authority after activation canonical merge: **R138_BOUNDED_IMPLEMENTATION_ONLY**
- Codex merge authority: **NONE**

## 下一关：完成 activation，再交给 Codex

1. activation PR 必须 exact-head 通过 Program Control Tower Python 3.11 + 3.13；
2. GPT 对 exact head 独立检查 diff、route/claim/lane/receipt 一致性与 main drift；
3. GPT 以 expected head merge activation；
4. merge 后重新确认 canonical `main` 与 `ACTIVE-CODEX-TASK` 已变为 R138 `READY`；
5. GPT 给出完整 R138 Launch Envelope，Codex 在正确 Second Brain workspace 核对 repo/task/epoch/issue/branch/local process/lease 后开工；
6. Codex 第一项 material work 前必须先创建 `R138/EXECUTION-PLAN.yaml`；
7. Codex 只允许 6 个 exact write paths，单 local heavy stage、single-worker default、no nested pools、no global kill Python；
8. 完成后只回传 `R138_DOMAIN_CAPABILITY_EXECUTION_PROVIDER_READY_FOR_GPT_REVIEW` 和证据，不得自行 merge。
