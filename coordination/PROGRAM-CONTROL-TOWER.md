# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T18:26:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER` | 137 | `PREPARED_NON_EXECUTABLE` | `false` | #360 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `READY` | `READY` | `false` | RESERVATION_MERGE_THEN_FRESH_ROOT_PROVIDER_BOOTSTRAP_AND_EXPLICIT_R137_ACTIVATION |
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
| `LANE-A-HARNESS-INTEGRATION` | `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` | `CODEX` | `LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION` | 6 paths | epoch 137 · #360/#None |
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

- **R136 已完整完成并关闭**。Implementation PR #356 merge `54c99780ad6d1a1cc8a035a18130f26b2f91eb62`；post-merge closure PR #357 merge `16f158e1123fa6b52c1a489ddd53093a91270624`；Issue #353 已 completed。
- **R137 Phase A 架构已完成**。Issue #358；架构 PR #359 exact head `93b5170989da4c101e5dc54ed07333bc2f4b184d`，review `4945958232`，Control Tower CI `31941554619`，merge `a065cc8eb4d978bef78543f2536d12d659067829`。
- **R137 当前仅进入 A1 非执行预留**。Issue #360；Codex route epoch 137 为 `PREPARED_NON_EXECUTABLE / execution_allowed=false / runtime_code_change_allowed=false`。Lane A 只占用未来写入表面，不允许实际写代码。
- **根信任启动门仍未满足**。当前 reservation reconciliation 不是 `ROOT_PROVIDER_BOOTSTRAP`。预留 merge 后必须重新观察新的 canonical main 与 route/task/claim/lane/architecture blobs，再生成一次性、不可复用、带 expiry/nonce 的 root-provider bootstrap。
- **用户批准的是顺序，不是此刻的 Codex 开工命令**：Authority-bound Live Observation Provider 先于 Domain Capability Execution Provider。R137 必须在 bootstrap 成为 canonical 后再等用户明确 launch。
- **历史能力只做精确来源复用**：E38 PR #117 transport blob 为 `ADAPT_AND_RETEST`；E39 PR #121 route-readiness blob 仅 selective reference，旧的“non-None approval 即算存在”语义明确禁止；E50/E51 暂无代码导入权。
- **V1 trust class**：`PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1`。它是 public GitHub read-only、on-demand、串行 evidence provider，不声称抵御 hostile same-process Python monkeypatch，也不引入 private credentials。
- **AI Film 仍是独立 domain authority**，R137 只把其 exact main 作为 read-only freshness reference，不写 AI Film。
- **Domain Capability Execution Provider 继续 NOT_AUTHORIZED**，必须排在 R137 被独立验收并合并之后。
- **Harness/H2/H7/private W3/domain write/daemon-webhook-polling/production/permissions-secrets/Formal Skill/trading 均未授权**。
- **Lane B 继续 user-held / NO_TRADE**；Lane C 继续 closed/frozen。

## R137 reservation evidence

- Parent architecture issue: `#358`
- Reservation issue: `#360`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER`
- Route epoch: `137`
- Mode: `【Codex模式：项目计划模式】`
- Architecture merge: `a065cc8eb4d978bef78543f2536d12d659067829`
- Architecture blob: `3543cd3a14bc0f6c24d35a480569dce767637a4c`
- Threat model blob: `eea5b8c1ce529b1a9266528499de3a3c18225e9b`
- Source selection blob: `18e35b8007be32e422b73a08fe1d3977aabff060`
- Planning reconciliation: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R137-PLANNING.yaml`
- Reservation reconciliation: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R137-RESERVATION.yaml`
- Planned implementation branch: `codex/r137-authority-live-observation-provider`
- Current execution authority: **NONE**

## 下一关：ROOT_PROVIDER_BOOTSTRAP

预留 PR 合并后，GPT 必须从 GitHub 当前真实状态重新生成启动根证据，至少绑定：
1. 新 `main` exact SHA；
2. exact `ACTIVE-CODEX-TASK` / route / task brief / Work Claim / Program Lane blobs；
3. exact architecture / threat model / source selection blobs；
4. exact future implementation allowlist；
5. task_id / epoch 137 / Issue #360 / planned branch；
6. issued_at / expires_at / nonce / one-time unconsumed state；
7. same-agent / O0-O4 / resource / private-secret boundary重新扫描；
8. 用户未来明确的 R137 launch ref。

在上述 bootstrap 尚未 canonical 且用户尚未明确 launch 前：**不要让 Codex 开工。**
