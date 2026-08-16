# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T08:50:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-PLANE-S0D-READ-ONLY-CROSS-REPO-SHADOW` | 135 | `READY` | `true` | #348 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `false` | S0D_EXACT_HEAD_GPT_REVIEW_NO_AUTO_S0E_H2_H7 |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 2 paths | epoch 135 · #348/#None |
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

- **S0C 已完成并关闭**。PR #346 merge `336430024faf7ed8ba93b0a102e5e245d08df2f4`；closure PR #347 merge `4aaff242f3fcd67fe68c9c711bcaec5de4947630`。
- **R135 S0D Phase A 已 canonical**。PR #349 head `25d6570e86233b30e9d3be59cc14dd1f3b0ebf69`，Control Tower `31918034024` 双版本 PASS，merge `0f70131362eb5be2f78b246531e3368e4a854595`。
- **Phase B fresh cross-repo reconciliation：PASS**。AI Film main 仍为 `44c383afd2207a97caf45b1b0da6ee1dece43a76`，远端 open PR 观察为 0，`PROJECT_INDEX.yaml` 仍是 source authority，blob `a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19`。
- **S0D 激活边界**：一轮式、exact-commit-bound、AI Film read-only；共享层只允许 metadata/IDs/status/hashes/locators/opaque refs，不复制完整剧本、角色、地图、资产、导演系统正文。
- **S0D 唯一写入面**：Second Brain `S0D-READ-ONLY-SHADOW` + workflow。AI Film 的 commit/branch/issue/PR/comment/label/file/settings mutation 全部禁止。
- **Codex active lease**：epoch 135 / Issue #348 / `READY / execution_allowed=true`，但真正开工仍需要用户把完整 R135 Launch Envelope 发到 **second-brain-coordination** Codex 窗口。
- **S0E / Harness Runtime / H2 / H7 / private-chat ingestion / W3 write / domain write / production / trading：均未授权**。
- **Lane B：继续 user-held / NO_TRADE**。Lane C Foundation 继续 closed/frozen。

## R135 Phase B evidence

- Bootstrap receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R135.yaml`
- Activation receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R135-ACTIVATION.yaml`
- Second Brain post-Phase-A main: `0f70131362eb5be2f78b246531e3368e4a854595`
- AI Film activation source SHA: `44c383afd2207a97caf45b1b0da6ee1dece43a76`
- Source authority blob: `a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19`
- QCLAW execution: false
- WorkBuddy execution: false
- unknown local/unpushed AI Film Codex activity: launch-time fail-closed requirement

## 启动前最后一关

Phase B activation PR 必须：
1. exact-head Control Tower Python 3.11/3.13 全绿；
2. GPT compare main/head and expected-head merge；
3. merge 后重新确认 canonical `ACTIVE-CODEX-TASK` 为 epoch 135 / READY / execution_allowed=true；
4. 用户发送完整 R135 Launch Envelope；
5. Codex 首先重新检查 repo/task/epoch/issue/source commit 与本地 AI Film Codex collision，任一不符就返回 `WRONG_REPOSITORY_OR_ROUTE_OR_LEASE_CONFLICT`；
6. 完成后只进入 GPT exact-head review，不自行 merge，不自动进入 S0E/H2/H7。