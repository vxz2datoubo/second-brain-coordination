# 本地知识候选仓分期实施计划

> `agent_id: WORKBUDDY` | `task: PHASE0`

## 当前状态

QCLAW 桥接可运行、输出存在，但完全扁平、无结构化知识包能力。需要从零搭建候选仓基础设施。

## Phase 0（本轮）：审计与设计 ✅

- [x] 审计 QCLAW 入口、输出、运行时、磁盘
- [x] 设计目录结构、状态机、合同、隐私分级
- [x] 识别未知项和风险
- [ ] 提交到独立分支并创建 PR

## Phase 1：本地候选仓 Shell

**目标**: 创建目录结构 + SQLite状态库 + 基础Python模块

```
F:/aidanao/qclaw-knowledge/
├── 00-inbox-raw/
├── 01-processing/
├── 02-candidate-packets/
├── 03-review-queue/
├── 04-approved-local/
├── 05-sync-outbox/
├── 06-synced/
├── 07-quarantine/
├── 08-rejected/
├── manifests/
├── state/
│   └── state.sqlite
└── logs/
```

**交付**:
- `init_knowledge_repo.py` — 创建目录+SQLite表
- `state_machine.py` — 状态迁移引擎
- `packet_validator.py` — LearningPacket schema验证
- 目录 `README.md` 和 `.gitkeep` 文件

## Phase 2：QCLAW输出包装层

**目标**: 让 QClawBridge.ask() 的原始输出自动生成结构化LearningPacket

**核心模块**: `qclaw_packet_wrapper.py`
- 拦截 QClawBridge.ask() 输出
- 提取source_artifacts（提示词内容哈希+来源）
- 生成atoms/relations（调用QCLAW本身做结构化）
- 打隐私/许可标签
- 写入JSONL到 02-candidate-packets/

**风险**: QCLAW的atom提取质量需要人工抽检。建议先跑小批量验证。

## Phase 3：审核与质量

**目标**: 人工/治理层审核队列

- 03-review-queue/ 展示所有 REVIEW_REQUIRED 的packet
- 提供命令行审核工具: `review_packet.py <packet_id> approve|reject|quarantine`
- 统计分析: 每日产出量、审核通过率、常见问题类型

## Phase 4：同步出站箱

**目标**: 冻结批次 + Git同步准备

- Freeze: 从approved-local复制到sync-outbox，生成SyncBundle
- Preflight: 自动检查隐私、许可、冲突、重复、Schema迁移
- Dry-run: 比较本地manifest与远端（未来）
- 批次可审查、可回滚

## Phase 5：Git + Supabase + 生产化

- 私有Git仓库创建
- Git写入 + PR流程
- Supabase投影
- 检索一致性验证
- 监控: packet积压、同步延迟、冲突率、磁盘增长

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| QCLAW atom提取质量差 | Phase 2人工抽检, 低质量回退到QUARANTINE |
| 隐私泄露 | Phase 1强制RESTRICTED_NEVER_SYNC扫描, Phase 4 preflight |
| 磁盘增长 | 日志轮转, manifest压缩, 过期raw归档 |
| QCLAW配置腐败 | Phase 1在桥接层增加配置健康检查 |
| 知识分裂(QCLAW vs 8766) | Phase C对齐Schema, 统一atom_id命名空间 |

## 时间估算

| Phase | 估算工作量 | 依赖 |
|-------|----------|------|
| Phase 1 (Shell) | 2-3天 | 本轮设计 |
| Phase 2 (Wrapper) | 3-5天 | Phase 1 |
| Phase 3 (Review) | 1-2天 | Phase 2 |
| Phase 4 (Sync) | 3-5天 | Git仓库创建 |
| Phase 5 (Production) | 5-10天 | Supabase/Docker环境 |
