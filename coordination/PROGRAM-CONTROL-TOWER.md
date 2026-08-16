# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T18:34:35+08:00`
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
| `LANE-A-HARNESS-INTEGRATION` | `READY` | `READY` | `false` | EXPLICIT_USER_R137_LAUNCH_THEN_FRESH_GPT_ACTIVATION_AND_FULL_LAUNCH_ENVELOPE |
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

- **R136 已完整完成并关闭**。Implementation PR #356 merge `54c99780ad6d1a1cc8a035a18130f26b2f91eb62`；post-merge closure PR #357 merge `16f158e1123fa6b52c1a489ddd53093a91270624`。
- **R137 Phase A 架构已完成**。Issue #358；PR #359 merge `a065cc8eb4d978bef78543f2536d12d659067829`。
- **R137 A1 非执行预留已完成**。Issue #360；reservation PR #361 exact head `1126e0b4f736932142b6c2512ef1e5b1713ed85d`，review `4945973134`，Control Tower CI `31941978570`，merge `7b0996a98fc908b2afad6be7775eafc74381e648`。
- **ROOT_PROVIDER_BOOTSTRAP 已由 GPT 直接观察生成**：`ROOT-PROVIDER-BOOTSTRAP-R137-0001`。它绑定 post-reservation main、exact task/route/claim/lane/architecture、实现 allowlist、expiry 与 nonce；它不是普通 live proof，也不能授权 R138。
- **R137 仍然没有开工权限**：`PREPARED_NON_EXECUTABLE / execution_allowed=false / runtime_code_change_allowed=false`。Bootstrap 只是根信任证据，不是执行开关。
- **现在唯一下一门是用户明确 launch**。用户此前的“按这个顺序继续”只批准顺序与治理推进，不自动解释成“现在让 Codex 写实现”。用户明确 launch 后，GPT 还要重新检查 current main、bootstrap 未过期/未消费/未撤销、route/task/claim/lane/agent/resource/O0-O4/private-secret 边界，再通过一个独立 activation transition 把 epoch 137 变成可执行。
- **V1 trust class**：`PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1`，public GitHub read-only/on-demand/serial。它不声称用 Python 私有对象抵御 hostile same-process code，也不引入 private repo token。
- **E38/E39 历史能力只做 exact source reuse**：E38 transport = ADAPT_AND_RETEST；E39 仅 selective reference，旧 non-None approval 语义禁止；E50/E51 仍无代码导入授权。
- **AI Film 继续独立 authority**，bootstrap 重新确认其 main 仍为 `44c383afd2207a97caf45b1b0da6ee1dece43a76`，只读 freshness reference，不写域仓库。
- **Domain Capability Execution Provider 继续 NOT_AUTHORIZED**，必须等 R137 被独立验收/merge/closure 后单独开门。
- **Harness/H2/H7/private W3/domain write/daemon-webhook-polling/production/permissions-secrets/Formal Skill/trading 均未授权**。
- **Lane B 继续 user-held / NO_TRADE**；Lane C closed/frozen。

## R137 root bootstrap evidence

- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER`
- Issue: `#360`
- Route epoch: `137`
- Mode: `【Codex模式：项目计划模式】`
- Reservation merge: `7b0996a98fc908b2afad6be7775eafc74381e648`
- Bootstrap receipt: `coordination/CONTROL-TOWER/ROOT-PROVIDER-BOOTSTRAP-R137.yaml`
- Bootstrap ID: `ROOT-PROVIDER-BOOTSTRAP-R137-0001`
- Bootstrap nonce SHA-256: `547deb3e8723500d032632a5f0d069f0018ad09c7ab23e2f5c3aa2e94a70e20e`
- Issued: `2026-08-16T10:34:35Z`
- Expires: `2026-08-17T10:34:35Z`
- Consumed: `false`
- Revoked: `false`
- User launch received: **false**
- Current execution authority: **NONE**

## 下一关：用户明确启动 R137

只有用户明确说“启动 R137”或等价指令后，GPT 才能进入 activation：
1. re-fetch 当前 `main`；
2. verify bootstrap 文件仍 canonical、未过期/未撤销/未消费；
3. re-fetch exact ACTIVE-CODEX / route / task / claim / lane；
4. re-scan QCLAW / WorkBuddy / resource / O0-O4；
5. re-check private repo / credentials / permissions / secrets / domain write 都仍不需要；
6. 生成 GPT activation witness；
7. activation PR 将 R137 route/claim 从 reserved non-executable 切到 bounded executable；
8. exact-head Control Tower CI + 独立审查后 merge；
9. 再把完整 R137 Launch Envelope 给用户发进正确的 Second Brain Codex workspace。

在用户明确 launch 之前：**不要给 Codex 发实现提示词。**
