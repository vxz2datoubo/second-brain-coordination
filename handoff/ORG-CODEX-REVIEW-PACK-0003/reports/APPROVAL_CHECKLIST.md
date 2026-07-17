# APPROVAL_CHECKLIST — ORG-CODEX-MERGE-0002

> 用户审查清单。打勾代表批准。

---

## 一、结构审查

| # | 事项 | 状态 |
|---|------|:--:|
| A1 | 理解新 AGENTS.md 的四角色模型（用户/ChatGPT/Codex/WorkBuddy） | ☐ |
| A2 | 理解旧版 481 行规则被拆分为 7 个独立文件 | ☐ |
| A3 | 理解 AGENTS.merged-candidate.md 仅含协调协议+安全+研究不变式，不含具体交易参数 | ☐ |
| A4 | 理解交易参数已移至 `config/trading/*.yaml`（可独立版本管理） | ☐ |

## 二、规则审查

| # | 事项 | 状态 |
|---|------|:--:|
| B1 | 全局不变量（5条）确认无误，无遗漏 | ☐ |
| B2 | 风控参数（12条）已正确迁移到 YAML，数值无误 | ☐ |
| B3 | 研究假设（19条）降级为待验证——接受此分类 | ☐ |
| B4 | 工作流预设（12条）降级为流程文档——接受 | ☐ |
| B5 | 废弃规则（5条）确认可以移除 | ☐ |

## 三、冲突审查

| # | 事项 | 状态 |
|---|------|:--:|
| C1 | Wyckoff Phase 从"强制前提"改为"模型特征/假设"——接受 | ☐ |
| C2 | Codex 从 WorkBuddy 下属变为对等首席工程师——接受 | ☐ |
| C3 | QClaw 从协议文档中移除——接受 | ☐ |
| C4 | 信号格式从"+1/0/-1 必须"改为"保留原始值，+1/0/-1 为展示便利"——接受 | ☐ |
| C5 | 全面分析 15 项技能从强制改为上下文动态决定——接受 | ☐ |
| C6 | 买入/卖出"红线"中未验证项降级为假设——接受 | ☐ |

## 四、执行动作（批准后）

| # | 动作 | 执行人 |
|---|------|--------|
| D1 | `cp AGENTS.merged-candidate.md AGENTS.md` | WorkBuddy |
| D2 | `cp daytrade_system/AGENTS.candidate.md daytrade_system/AGENTS.md` | WorkBuddy |
| D3 | `cp CHATGPT-BRAIN-PROTOCOL.candidate.md CHATGPT-BRAIN-PROTOCOL.md` | WorkBuddy |
| D4 | `cp config/trading/*.candidate.yaml config/trading/*.yaml` (去掉 .candidate 后缀) | WorkBuddy |
| D5 | 更新 `coordination/SYSTEM-STATE.md` 状态为 ACTIVE | WorkBuddy |
| D6 | 存档旧版 `handoff/backup/AGENTS.pre-coordination.md` 和 `AGENTS.candidate.md` | WorkBuddy |

## 五、风险提示

| # | 风险 | 缓解 |
|---|------|------|
| R1 | 旧版交易规则从 AGENTS.md 移除后，老工作流可能找不到引用 | TRADING-GOVERNANCE.md 保存了完整流程 |
| R2 | 新协议要求 Codex 独立角色，但未部署 Codex App | 不影响；文档待 App 到位后激活 |
| R3 | 部分参数 YAML 标注 `candidate_pending_validation` | 表示这些参数需进一步验证再激活 |

---

**审查人签名**: ☐ 波仔 (用户)

**批准日期**: ______________
