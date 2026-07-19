# HARD_LIMIT_VS_HYPOTHESIS — 旧交易红线重新分类审计

> Task: ORG-CODEX-REVIEW-PACK-0003 | Date: 2026-07-16 03:55 UTC+8
> Purpose: 确认关键硬限制未被错误降级为研究假设

---

## Verification Target

逐条检查以下 9 项**绝对不应被降级**的硬限制在新候选协议中的状态。

---

## 1. 实盘审批

| 项目 | 值 |
|------|-----|
| 旧版表述 | 用户最终审批（超级博弈大脑要求"执行前检查"） |
| 新版位置 | `AGENTS.merged-candidate.md` §1 (Role: User: "Approves: real-money trading") + §5 (Safety: "User approval before any real-money trading") |
| 分类 | **hard_safety_limit** |
| 是否被错误降级 | ❌ NO — 在新版协议中**升级**为显式全局安全规则 |

## 2. T+1 约束

| 项目 | 值 |
|------|-----|
| 旧版表述 | "不得忽视A股T+1与交易时段差异，直接套用美股逻辑" |
| 新版位置 | `AGENTS.merged-candidate.md` §5 + §6 (A-share T+1 listed as global invariant) AND `daytrade_system/AGENTS.candidate.md` §A-share market invariants |
| 分类 | **regulatory_or_market_constraint** |
| 是否被错误降级 | ❌ NO — 在两个层面（全局不变式 + 交易子系统）都保留 |

## 3. 涨跌停与停牌

| 项目 | 值 |
|------|-----|
| 旧版表述 | 旧版 AGENTS.md 未显式提及（由 WorkBuddy 技能文档隐含） |
| 新版位置 | `AGENTS.merged-candidate.md` §6 (Price limits & suspensions as global invariant) AND `daytrade_system/AGENTS.candidate.md` §Price limits, §Suspensions |
| 分类 | **regulatory_or_market_constraint** |
| 是否被错误降级 | ❌ NO — 在新版中**首次显式文档化**并升级为全局不变式 |

## 4. 账户最大风险

| 项目 | 值 |
|------|-----|
| 旧版表述 | "总持仓上限90%" (硬编码在 AGENTS.md 中) |
| 新版位置 | `config/trading/risk_limits.candidate.yaml` (max_total_exposure: 0.90) |
| 分类 | **operational_limit** |
| 是否被错误降级 | ❌ NO — 迁移为可配置参数，数值和来源保持不变。参数本身仍是硬限制（只是格式从硬编码改为 YAML） |

## 5. 单日亏损熔断

| 项目 | 值 |
|------|-----|
| 旧版表述 | "日亏熔断线 2%，超限全天停止" |
| 新版位置 | `config/trading/risk_limits.candidate.yaml` (daily_drawdown_circuit_breaker: 0.02) |
| 分类 | **operational_limit** |
| 是否被错误降级 | ❌ NO — 迁移为 YAML 可配置参数 |

## 6. 最大订单规模

| 项目 | 值 |
|------|-----|
| 旧版表述 | "单笔金额 5000元 (±1000)" |
| 新版位置 | `config/trading/risk_limits.candidate.yaml` (single_trade_amount: 5000) |
| 分类 | **operational_limit** |
| 是否被错误降级 | ❌ NO |

## 7. 密钥安全

| 项目 | 值 |
|------|-----|
| 旧版表述 | 旧版 AGENTS.md 未显式规则化（WorkBuddy 运行时约束和 CHATGPT-BRAIN-PROTOCOL 中有隐含提及） |
| 新版位置 | `AGENTS.merged-candidate.md` §5 (Safety: "No credential storage in plain text") |
| 分类 | **hard_safety_limit** |
| 是否被错误降级 | ❌ NO — 在新版中**首次显式文档化**为全局安全规则 |

## 8. 未来数据泄漏禁止

| 项目 | 值 |
|------|-----|
| 旧版表述 | "无未来函数" (仅回测脚本注释中) |
| 新版位置 | `AGENTS.merged-candidate.md` §6 (Quant research invariants: "No look-ahead leakage") AND `daytrade_system/AGENTS.candidate.md` §Data quality: "Look-ahead leakage: Zero tolerance" |
| 分类 | **hard_safety_limit** |
| 是否被错误降级 | ❌ NO — 在新版中**升级**为全局研究不变式 + 交易子系统硬要求 |

## 9. 生产回滚

| 项目 | 值 |
|------|-----|
| 旧版表述 | 隐含于"自进化机制"（可回退参数） |
| 新版位置 | `AGENTS.merged-candidate.md` §4 (Task packet protocol: scope, allowed/forbidden files) AND `daytrade_system/AGENTS.candidate.md` §Production readiness gates |
| 分类 | **operational_limit** |
| 是否被错误降级 | ❌ NO — 通过任务协议和生产门控机制隐式保护 |

---

## 最终结论

| # | 硬限制 | 旧版状态 | 新版状态 | 被错误降级？ |
|---|--------|----------|----------|:----------:|
| 1 | 实盘审批 | 隐含 | **显式升级** | NO |
| 2 | T+1 | 明确 | 保留 + 扩展 | NO |
| 3 | 涨跌停/停牌 | 隐式 | **首次文档化** | NO |
| 4 | 账户最大风险 | 硬编码 | YAML 可配置 | NO |
| 5 | 单日熔断 | 硬编码 | YAML 可配置 | NO |
| 6 | 最大订单量 | 硬编码 | YAML 可配置 | NO |
| 7 | 密钥安全 | 隐式 | **首次文档化** | NO |
| 8 | 未来数据泄漏 | 隐式(脚本) | **升级为全局不变式** | NO |
| 9 | 生产回滚 | 隐式 | 任务协议保护 | NO |

**✅ 确认：9项关键硬限制均未被错误降级。相反，其中4项从旧版的隐式/硬编码状态被升级为显式文档化的全局规则。**
