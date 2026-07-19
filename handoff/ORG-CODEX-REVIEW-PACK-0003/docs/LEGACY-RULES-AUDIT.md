# LEGACY-RULES-AUDIT — 旧版 AGENTS.md (481行) 逐条分类审计

> Audit date: 2026-07-16 03:44 UTC+8
> Source: `handoff/backup/AGENTS.pre-coordination.md` (v2026-07-05)
> Auditor: WorkBuddy
> Task: ORG-CODEX-MERGE-0002

## Classification Legend

| Class | Meaning |
|-------|---------|
| **global_invariant** | 全局不可违反原则 |
| **risk_parameter** | 可调整的仓位/风控/时间参数 |
| **research_hypothesis** | 需回测验证的假设 |
| **workflow_preset** | 工作流预设（非铁律） |
| **deprecated_or_conflicting** | 过时/冲突/证据不足 |

---

## 1. 核心目标

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R01 | "自我进化的A股T仓交易系统，以第二大脑知识库为核心" | deprecated_or_conflicting | ❌ | — | 模糊概念 | 与四方协作协议冲突（不再以"第二大脑"为中心） | 废弃 |

## 2. A股权威准则优先级

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R02 | "交易系统最高准则: SYSTEM_REPLICATION_FOR_CODEX.md" | deprecated_or_conflicting | ❌ | — | 外部文件引用，未维护 | AGENTS.md 本身就是最高准则 | 废弃引用 |
| R03 | "冲突时以该文档为准" — priority rule | global_invariant | ✅ | AGENTS.merged-candidate.md | N/A | 与新指令优先级一致 | 迁移到全局指令优先级章节 |
| R04 | "不得把OHLCV冒充为真DDX/DDY" | global_invariant | ✅ | AGENTS.merged-candidate.md | MF r=0.294 已验证 | 无 | 保留为量化研究不变量 |
| R05 | "不得忽视A股T+1与交易时段差异" | global_invariant | ✅ | AGENTS.merged-candidate.md + daytrade_system/AGENTS.candidate.md | 已验证（市场规则） | 无 | 迁移到全局研究不变量 |
| R06 | "不得把单技能信号直接变成交易结论" | global_invariant | ✅ | AGENTS.merged-candidate.md | 已验证（多样性原则） | 无 | 保留为全局规则 |
| R07 | "交易子系统挂接母系统协议" | workflow_preset | ⚠️ | TRADING-GOVERNANCE.md | 设计意图 | 无需再以"母系统"为中心 | 降级为架构文档 |

## 3. 核心参数

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R08 | 单笔金额 5000元 (±1000) | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 用户设定 | 无 | 迁移为可配置参数 |
| R09 | 单日T仓上限 3笔 | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 用户设定 | 无 | 迁移为可配置参数 |
| R10 | 总持仓上限 90% | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 用户设定 | 无 | 迁移为可配置参数 |
| R11 | 日亏熔断线 2% | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 用户设定 | 无 | 迁移为可配置参数 |
| R12 | 昆仑优先级 60%, 蓝标 40% | risk_parameter | ✅ | config/trading/strategy_parameters.candidate.yaml | 用户设定 | 固定权重受限单票组合 | 迁移为可配置参数 |
| R13 | 倒T优先 | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 未经系统化回测 | 无 | 标记为"部分验证：待回测" |

## 4. 买入红线

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R14 | "大盘下跌趋势禁止追高买入" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 需要定义"大盘下跌趋势"的精确量化标准 | 待验证 |
| R15 | "开盘30分钟内禁止买入（除非已有持仓做T）" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 无量化证据 | 待验证，保留做T豁免 |
| R16 | "持仓当日跌幅超5%禁止补仓" | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 经验规则 | 无 | 迁移为可配置参数 |
| R17 | "跌幅超7%必须检查是否止损" | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 经验规则 | 无 | 迁移为可配置参数 |
| R18 | "涨停板次日不追高" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 无量化验证 | 待验证 |
| R19 | "追涨次日只卖不买" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 无 | 待验证 |

## 5. 卖出红线

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R20 | "大盘大跌禁止恐慌性卖出" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | "大盘大跌"无精确定义 | 待验证 |
| R21 | "盈利未达2%禁止卖出" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 与做T逻辑冲突（有时微利即出） | 待验证并量化 |
| R22 | "卖出后30分钟内禁止接回" | risk_parameter | ✅ | config/trading/session_windows.candidate.yaml | 经验规则 | 无 | 迁移为可配置冷却窗口 |
| R23 | "连续3日下跌才考虑止损" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 可能与日亏熔断线冲突 | 待验证 |

## 6. 时间窗口

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R24 | T1-T8 时间窗口定义 | workflow_preset | ✅ | config/trading/session_windows.candidate.yaml | 用户策略 | 无 | 迁移为可配置参数 |

## 7. 交易规则

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R25 | "正T谨慎：仅buy_score>40时考虑" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | buy_score定义不明确，无回测支撑 | 无 | 待验证并定义buy_score |
| R26 | "卖飞处理：等回落1%再追回" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 经验规则 | 无 | 待验证 |
| R27 | 置信度等级 A++/A/B/C/D 及阈值 | risk_parameter | ✅ | config/trading/strategy_parameters.candidate.yaml | 用户设定 | 无 | 迁移为可配置参数 |
| R28 | 市场状态分类 TREND_UP/DOWN/HIGH_VOL/LOW_VOL/EXTREME | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 未定义分类算法 | 无 | 需量化定义后验证 |

## 8. 认知决策系统 + 自进化机制

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R29 | 认知引擎/推理引擎 API 端点 | deprecated_or_conflicting | ❌ | — | 未部署，未验证 | 无 | 废弃 |
| R30 | 自进化机制 (日/周/月级) | workflow_preset | ⚠️ | TRADING-GOVERNANCE.md | 未实现 | 无 | 降级为治理文档 |
| R31 | 进化触发条件表格 | risk_parameter | ✅ | config/trading/risk_limits.candidate.yaml | 经验规则 | 无 | 迁移参数 |

## 9. 超级博弈大脑 Codex 调用指南

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R32 | Codex 5步自动调用流程 | workflow_preset | ⚠️ | daytrade_system/AGENTS.candidate.md | 原API可能未完全实现 | 新协议中Codex角色完全不同 | 重写为TASK-PACKET协议 |
| R33 | API端点: /api/super/think, /api/detective/investigate 等 | deprecated_or_conflicting | ❌ | — | 未验证部署状态 | 冲突（新协议中Codex不做这些） | 废弃，等待重新实现 |
| R34 | 快速判断规则表格（Codex遇6种情况先查大脑） | workflow_preset | ⚠️ | daytrade_system/AGENTS.candidate.md | 设计意图 | Codex新角色下需重新定义 | 重写 |

## 10. Wyckoff / 资金 / 筹码 相关

| # | 原文摘要 | 对应现有技能/规则 | 分类 | 保留 | 新位置 | 证据 | 建议 |
|---|----------|-------------------|------|:--:|--------|------|------|
| R35 | "特大单/大单=纯机构(散户无法伪装)" | fund-chip-linkage | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 部分验证（阈值定义有分歧） | 标记"部分验证：待回测" |
| R36 | "大小单同向=3.8x增强" | a-share-call-auction | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 无量化验证脚本 | 降级为待验证 |
| R37 | "DDX=多信号验证器(非独立择时)" | 多技能引用 | workflow_preset | ⚠️ | STRATEGY-HYPOTHESES.md | 已验证WeStock data_technical可获取 | 保留为研究参考 |
| R38 | "OHLCV代理无效(MF r=0.294)" | 多技能引用 | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 有r值声明但无完整验证脚本 | 需独立复现 |
| R39 | "四渠道共识>分歧: 大小单同向=3.8x增强" | 四渠道相关技能 | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | 同上R36 | 待验证 |

## 11. 全面分析协议

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R40 | "全面分析→必须调用15项技能" | workflow_preset | ⚠️ | STRATEGY-HYPOTHESES.md | 工作流设计 | 固定15项可能过拟合 | 降级为工作流预设，非全局铁律 |
| R41 | "蓝标对比"作为15项之一 | workflow_preset | ⚠️ | STRATEGY-HYPOTHESES.md | 仅适用两票组合 | 不可泛化 | 标记为"当前持仓特定" |
| R42 | "每项必须输出+1/0/-1判定" | workflow_preset | ⚠️ | STRATEGY-HYPOTHESES.md | 设计约定 | 与新版"保留原始数值"冲突 | 标注冲突 |

## 12. 实时监控铁律

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R43 | "看昆仑→必查板块排行+涨跌5%板块+5条新闻+大盘" | workflow_preset | ⚠️ | TRADING-GOVERNANCE.md | 操作规范 | 仅适用300418 | 降级为操作流程 |
| R44 | "板块异动>5%→立即预警" | workflow_preset | ⚠️ | TRADING-GOVERNANCE.md | 已验证有用 | 无 | 保留为监控规则 |
| R45 | ""钱去哪了"优先级 > "DDX怎么样"" | workflow_preset | ⚠️ | TRADING-GOVERNANCE.md | 经验 | 无 | 保留为操作优先级 |

## 13. 消息面分类铁律

| # | 原文摘要 | 分类 | 保留 | 新位置 | 证据 | 冲突 | 建议 |
|---|----------|------|:--:|--------|------|------|------|
| R46 | "新闻动量型/滞后型/资金技术型分类" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | ✅ 已有回测输出 | 适用性限定在300418和300058 | 已验证→可升级，标注样本量小 |
| R47 | "持有期策略P&L作为可交易性闸门" | research_hypothesis | ⚠️ | STRATEGY-HYPOTHESES.md | ✅ 已有回测 | 样本仅60-74活跃日 | 保留，标注经济幅度中等 |

---

## 总结

| 分类 | 数量 | 处理方式 |
|------|:----:|----------|
| global_invariant | 5 | → AGENTS.merged-candidate.md |
| risk_parameter | 12 | → config/trading/*.yaml |
| research_hypothesis | 19 | → STRATEGY-HYPOTHESES.md + 回测验证 |
| workflow_preset | 12 | → TRADING-GOVERNANCE.md + daytrade_system/AGENTS.candidate.md |
| deprecated_or_conflicting | 5 | → 废弃 |
| **合计** | **47** | |
