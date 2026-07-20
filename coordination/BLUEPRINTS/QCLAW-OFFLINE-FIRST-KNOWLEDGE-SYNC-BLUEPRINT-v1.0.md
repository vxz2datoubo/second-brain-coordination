# QCLAW本地优先知识消化与批量同步蓝图 v1.0

> `agent_id: GPT`
>
> 定位：让QCLAW可以长期离线消化知识，先形成可验证的候选知识包，待私有Git、对象存储和Supabase条件具备后再安全、幂等、可回滚地批量同步。
>
> 边界：`research_only / NO_TRADE`。本蓝图不授权上传私人知识、创建云项目、读取凭证或把本地候选直接升级为权威事实。

## 一、第一性原理

QCLAW的价值是把原始材料加工成结构化候选知识，不是充当最终记忆权威。同步系统必须解决五个问题：

1. **身份**：每个原始工件、知识原子、关系、技能和知识包都有稳定ID与内容哈希；
2. **权威**：QCLAW本地输出默认是candidate，不能覆盖本地或云端权威知识；
3. **边界**：私人、敏感、许可受限材料必须在上传前分级；
4. **幂等**：同一批内容反复同步不能制造重复知识；
5. **可回滚**：云端同步失败或知识判断错误时，可以回到明确的Git版本而不修改原始材料。

因此采用：

```text
原始材料
→ 本地不可变收件箱
→ QCLAW消化与质量审查
→ 候选知识包
→ 本地审核与冲突队列
→ 同步出站箱
→ 私有Git候选分支/PR
→ 审核后成为权威版本
→ Supabase可重建检索投影
→ 多AI只读调用
```

## 二、本地目录与状态机

真实路径由WorkBuddy现场核验，公开仓库只使用逻辑别名：

```text
<QCLAW_KNOWLEDGE_ROOT>/
├── 00-inbox-raw/             # 原始材料，只追加，不覆盖
├── 01-processing/            # 临时处理区，可清理重建
├── 02-candidate-packets/     # QCLAW候选知识包
├── 03-review-queue/          # 人工或治理层待审
├── 04-approved-local/        # 已通过本地审核、尚未同步
├── 05-sync-outbox/           # 已冻结的同步批次
├── 06-synced/                # 已绑定Git提交和远端回执
├── 07-quarantine/            # 格式、隐私、许可、冲突异常
├── 08-rejected/              # 拒绝或保留，不能静默删除
├── manifests/                # 哈希、来源、批次和状态清单
├── state/                    # 游标、幂等键、锁和恢复点
└── logs/                     # 脱敏运行与错误日志
```

知识包状态：

```text
RECEIVED
→ PROCESSING
→ CANDIDATE
→ REVIEW_REQUIRED
→ APPROVED_LOCAL
→ FROZEN_FOR_SYNC
→ SYNCED_TO_GIT
→ PROJECTED_TO_SERVING
```

旁路状态：`QUARANTINED / REJECTED / CONFLICT / SUPERSEDED / FAILED_RETRYABLE / FAILED_FINAL`。

任何状态变化都通过新事件记录，不直接改写历史。

## 三、候选知识包合同

每个 `LearningPacket` 至少包含：

```yaml
packet_id:
schema_version:
source_artifacts:
  - source_id:
    source_hash:
    source_type:
    source_reference_local:
    source_time:
    event_time:
    license_class:
    privacy_class:
processed_by: QCLAW
processor_version:
processed_at:
base_knowledge_revision:
status: candidate
atoms: []
relations: []
structures: []
skills: []
retrieval_index: []
unknowns: []
conflicts: []
quality_audit: {}
write_proposal:
  auto_accept_candidate: []
  human_review_required: []
  reject_or_hold: []
content_hash:
idempotency_key:
```

高阶结构和技能必须追溯到 `atom_id`；每个事实有来源，每个假设有验证路径；冲突并列保存，不静默覆盖。

## 四、隐私与许可分级

同步前每个源工件和知识包必须标记：

- `PUBLIC_SAFE`：允许进入公开协调仓库的Schema、代码或脱敏摘要；
- `PRIVATE_KNOWLEDGE`：只允许进入私有Git知识仓库；
- `SENSITIVE_LOCAL_ONLY`：仅本地保存，不上传云端；
- `RESTRICTED_NEVER_SYNC`：凭证、浏览器会话、账户、个人隐私、真实交易数据等；
- `LICENSE_RESTRICTED`：只同步自有摘要、引用、哈希和来源元数据，不上传原文或受限数据；
- `UNKNOWN_CLASSIFICATION`：进入隔离区，禁止同步。

公开仓库永远不能承载私人知识正文、原始账户数据、许可不明行情或受保护总蓝图正文。

## 五、同步批次合同

批量同步不是直接复制目录。每次生成不可变 `SyncBundle`：

```yaml
bundle_id:
created_at:
source_machine_alias:
base_git_revision:
packet_ids: []
packet_hashes: []
source_manifest_hash:
schema_versions: {}
privacy_summary: {}
license_summary: {}
conflicts: []
unknowns: []
idempotency_key:
dry_run_result:
approval_status:
target:
  private_git_repository:
  branch:
  serving_projection:
rollback_revision:
```

同步顺序：

1. 冻结出站箱和生成SHA-256清单；
2. Schema、引用、隐私、许可、秘密和重复检查；
3. `dry-run` 比较远端权威版本，生成新增、补充、冲突和无变化清单；
4. 用户或治理层批准涉及私人知识外传的批次；
5. 写入私有Git独立分支并创建PR，不直接写main；
6. 合并后记录Git commit，移动本地状态为 `SYNCED_TO_GIT`；
7. 从该Git revision幂等投影到Supabase；
8. 验证检索一致性后标记 `PROJECTED_TO_SERVING`。

## 六、目标存储分工

### 1. 本地QCLAW候选仓

- 保存原始工件、候选知识包、隔离内容和同步状态；
- 允许离线持续工作；
- 在云端权威库建立前，`approved-local`只是临时受控版本，不是长期企业权威。

### 2. 私有Git知识仓库

- 保存审核通过的结构化知识、Schema、关系、技能、冲突和版本历史；
- 是未来唯一知识权威源；
- 使用分支、PR、提交和回滚；
- 不适合存放巨大二进制、许可受限原文或高频运行日志。

### 3. 对象存储或本地归档

- 存放经批准的大型原始工件、音视频、PDF、快照和备份；
- Git只保存内容哈希、对象ID、权限和来源；
- 未建立安全对象存储前，大型私人原文继续留在本地。

### 4. Supabase

- 作为全文、结构化、关系和向量检索的可重建服务投影；
- 每条记录必须带Git commit、路径、内容哈希和投影版本；
- 不能成为独立写入权威，也不能反向覆盖Git历史。

### 5. 公开协调仓库

- 只保存协议、Schema、代码、任务、脱敏报告和Manifest摘要；
- 绝不保存私人知识正文。

## 七、离线积累与以后批量上传

允许QCLAW在完全离线情况下持续消化，条件是：

1. 原始材料不可变保存并有哈希；
2. 每个候选包记录处理器版本和基础知识版本；
3. 不在本地静默覆盖旧知识；
4. 已批准与待审核内容分区；
5. 出站箱在上传前重新做隐私、许可、Schema、重复和冲突检查；
6. 大批量同步拆成可审查的小批次，不进行一次不可回滚的巨型提交。

推荐批次按主题、项目、时间窗口或来源拆分，每批控制在可人工审查和可回滚范围内。Git大仓膨胀时，原始大文件转对象存储，Git保留结构化知识和引用。

## 八、双向同步与冲突

云端权威库建立后：

- 本地QCLAW每次处理前记录 `base_knowledge_revision`；
- 同步前先拉取远端最新权威版本；
- 远端发生变化时做三方比较：本地基础版本、远端当前版本、本地候选；
- `DUPLICATE / SUPPLEMENT / REFINEMENT / CONFLICT / CORRECTION / OUTDATED` 分别处理；
- 冲突不得由QCLAW自动裁决为事实，进入审核队列；
- 云端删除不直接物理删除本地原始来源，使用废弃或撤回事件。

## 九、失败恢复与可观测性

必须记录：

- 每批数量、大小、处理耗时、失败数、重试数；
- 原始工件到知识包到Git提交到投影记录的完整谱系；
- 同步游标、锁、重试退避和断点续传；
- 重复率、冲突率、隔离率、审核通过率和检索一致性；
- 任何秘密扫描、隐私分类或许可检查失败。

同步失败时，出站箱保持冻结，不重复生成新ID；用同一幂等键重试。远端部分成功时以Git提交事实为准进行恢复，不凭本地日志猜测。

## 十、角色分工

- **QCLAW**：知识消化、候选包生成、质量审查、冲突与未知项提出；
- **WorkBuddy**：本地目录、运行环境、批次构建、文件权限、备份和现场同步验证；
- **Codex**：Schema、验证器、去重/冲突算法、Git同步器和投影代码；
- **GPT**：架构、任务影响预测、批次验收、知识治理和工程学习；
- **用户**：私人知识外传、云端存储、权威知识合并和重大成本的最终批准。

## 十一、实施阶段

- `Q0`：现场只读审计QCLAW实际入口、输出、目录、数据格式和运行方式；
- `Q1`：建立本地候选仓、状态机、Manifest与LearningPacket Schema；
- `Q2`：本地离线消化MVP，完成重复运行稳定性和无覆盖测试；
- `Q3`：批次冻结、隐私/许可/秘密检查和dry-run；
- `Q4`：私有Git测试仓小批量同步与PR回滚验证；
- `Q5`：Supabase测试投影和从Git重建；
- `Q6`：多AI只读调用、来源与版本回显；
- `Q7`：增量同步、冲突处理、离线恢复和批量扩容。

## 十二、重大风险门禁

以下动作必须先通知用户并取得批准：

- 将私人或敏感知识离开本机；
- 创建私有云仓库、对象存储或Supabase并产生费用；
- 首次大批量上传；
- 修改知识权威源、保留策略或加密密钥；
- 删除、覆盖或迁移本地原始材料；
- 任何真实交易、账户、持仓或凭证相关数据进入处理链。

当前只建立架构和本地只读审计任务，不触发上述风险。
