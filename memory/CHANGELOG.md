# CHANGELOG — 量化系统永久记忆变更日志

> 维护者: WorkBuddy
> 位置: F:\aidanao\memory\CHANGELOG.md

## candidate — QMEM-20260716-0002 (proposed, pending_user_confirmation)

- Codex 首次完整架构审阅：母系统对象模型、数据层边界、策略生命周期、验证结果分类
- 第一阶段建设顺序调整：统一对象模型→规则引擎→Replay+Validation
- 暂不迁移 brain_core/bulletin/data 到 memory 目录
- 永久记忆总纲确认为导航索引，非运行配置

## v1.0 — 2026-07-16

- 创建 `QUANT-SYSTEM-MASTER-MEMORY.md`（来源: ChatGPT/Codex 协作产出）
- 部署记忆基础设施: patches/, CHANGELOG.md, SOURCE-REGISTRY.csv, DECISION-LOG.jsonl
- 应用 ST 规则修正补丁 PATCH-0001：旧"ST=5%"和"ST仅收盘清算"全部删除；当前基线改为上下10%；运行时以真实涨跌停价字段优先
- 应用 D-0004-v3 审核决策记录：7阻断/7高优/3审计矛盾，候选包暂不批准合并
- 初始 SOURCE-REGISTRY 登记
