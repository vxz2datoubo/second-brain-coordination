# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-18T01:25:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE` | 142 | `READY_AFTER_ACTIVATION_MERGE` | `true` | #393 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `REMEDIATION_ACTIVE` | `true` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `R142_RESERVED_AFTER_ACTIVATION_MERGE / DIRECT_USER_START_REQUIRED` | `true` | USER_DIRECT_START -> CODEX_PROJECT_PLAN_M0 |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | EXPLICIT_USER_START_THEN_SIGNAL_TOWER_PREFLIGHT_AND_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 4 paths | epoch 142 · #393/#None |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各 Agent 看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R142 activation 已 canonical**：当前 main `cb3dbd30892adbb59683fc91252a38b0868149a9`。R142 Codex route/claim 已建立，但用户尚未给 Codex direct-start，因此 R142 还没有实际 executor 开工。
- **R142 采用【Codex模式：项目计划模式】**：后续 direct-start 后才从 M0 fresh reconcile / plan 开始；当前不授权 QQ 接管 R142。
- **QCLAW R60 已由用户在 2026-08-18 重新授权继续**：仍是 Issue `#296`、Draft PR `#304`、route epoch `60`、branch `qclaw/p2-retrieval-adversarial-benchmark-r60`，只修 GPT review `4936644607` 已确认的 Q60-B01/B02/B03 和相应回归。
- **R60 原 `60/60 PASS` 继续视为无效 false-green evidence**，不能因为恢复执行而复活；90-case corpus 仅保留为 candidate benchmark material，必须对当前 merged P2 runtime fresh rerun。
- **R60 关键修复**：完整检查 atoms/relations/conflicts/unknowns/provenance/admission telemetry/trust-gate；fixture 必须持久化真实 mutated state；forbidden oracle 必须从实际 persisted canonical IDs/receipts 解析，不能依赖 optional `id_hint`。
- **旧的 QQ quota hold 已被当前用户指令替代**：当前 exact quota 未知，但用户明确确认算力充足；不虚构具体额度。
- **资源边界**：QCLAW task Python cap 2、combined CPU-bound workers cap 1、禁止 nested pools；若出现真实 local-heavy collision，fail closed 或退回 bounded single-worker/lightweight work。Codex R142 当前未 direct-start。
- **隐私与权限**：QCLAW 不读真实 private user source/store，不改 Phase-3/Codex/R142 runtime，不做 formal promotion，不碰 production/permissions/trading，不 self-merge。
- **Signal Tower 普通模式仍是 on-demand**，Signal ≠ Task；QCLAW R60 修复不改变 R142 的 Signal intake 架构。
- **保留 finding/gate**：`R138-F01`、`R139-STAGE-B`、`R140-MODEL-VERSION-AUTHORITY`、`IAGL-R141-UNKNOWN-007`、`IAGL-STAGE-B` 继续有效。

## QCLAW R60 remediation evidence

- Issue: `#296`
- Draft PR: `#304`
- Task: `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60`
- Route epoch: `60`
- Existing reviewed head: `ec5b7dc1fcdfdd5f379ae3c2f2f0410e5ec7013b`
- GPT review: `4936644607`
- Disposition: `QCLAW_R60_CHANGES_REQUIRED_HARNESS_FALSE_GREEN`
- Required blockers: `Q60-B01`, `Q60-B02`, `Q60-B03`
- Resume baseline main: `cb3dbd30892adbb59683fc91252a38b0868149a9`
- Same branch: `qclaw/p2-retrieval-adversarial-benchmark-r60`
- Merge authority: **NONE**

## R142 status

- Issue: `#393`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE`
- Route epoch: `142`
- Activation merge main: `cb3dbd30892adbb59683fc91252a38b0868149a9`
- Codex direct user start: **NOT GIVEN**
- S0C source write authority: **NONE unless later GPT scope expansion**
- W3/domain write authority: **NONE**
- Private bridge / daemon / production / trading authority: **NONE**
- Codex merge authority: **NONE**

## 下一关

QCLAW 先 fresh reconcile current main / route / Draft PR #304 / branch / then-current merged P2 runtime，再在同一 R60 中修复 B01-B03、运行真实 runnable benchmark 和规定回归，推送同一 PR #304。完成后只发 `QCLAW_P2_RETRIEVAL_ADVERSARIAL_BENCHMARK_R60_READY_FOR_GPT_REVIEW` 并停止，等待 GPT exact-head 独立验收；不得自行 merge。
