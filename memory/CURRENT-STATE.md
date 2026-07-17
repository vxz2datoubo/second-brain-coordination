# CURRENT-STATE — 量化系统当前状态

> 每次重大任务开始前，Codex 和 WorkBuddy 优先读取本文件。
> 维护者: WorkBuddy | 更新: 2026-07-16 05:12 UTC+8

## 系统阶段

| 维度 | 状态 |
|------|------|
| 研究 | ✅ Active（消息面衰减分类、FIFO资金池） |
| 回测 | ✅ Active（news_nextday fwd1-5、筹码消化剖面） |
| 仿真 | ❌ 未开始 |
| 影子模式 | ❌ 未开始 |
| 实盘 | ❌ 未开始（手动自由裁量） |

## 组织治理

| 项目 | 状态 |
|------|------|
| 四方协作协议 | ⏳ 候选版已完成；ChatGPT审核不通过（D-0004-v3: 7阻断），等待修订后重审 |
| 根 AGENTS.md | ❌ 未激活候选版 — 当前仍为旧版交易系统手册 |
| 交易子系统 AGENTS.md | ❌ 同上 |
| CHATGPT-BRAIN-PROTOCOL | ❌ 同上 |

## 核心数据能力

| 能力 | 状态 |
|------|------|
| L1 实时行情（TDX/WeStock） | ✅ |
| 四渠道资金流（WeStock 实时 + Tushare T+1） | ✅ |
| 10档盘口快照（TDX） | ✅ |
| 消息面量化（769篇，22维指数） | ✅ |
| L2 逐笔成交 | ❌ GAP — 等待 TdxQuant/eltdx PoC |
| L2 逐笔委托 | ❌ GAP |
| 集合竞价实时委托流 | ❌ GAP — 仅快照差分 |
| Point-in-Time 数据 | ❌ GAP |

## 当前阻塞项

| # | 阻塞项 | 优先级 |
|---|--------|:------:|
| 1 | L2 逐笔成交不可达 | P0 |
| 2 | 无 Git 仓库 | P1 |
| 3 | 候选协议包审核未通过 | P0 |
| 4 | 回测无 walk-forward 验证 | P1 |
| 5 | 无真实交易成本建模（仅 FIFO 引擎有） | P1 |

## 活跃服务

| 服务 | 端口 | 状态 |
|------|------|:----:|
| SuperBrain | 8766 | ✅ |
| MaiBot WebUI | 8000-8001 | ✅ |
| TTS Bridge | 9881 | ✅ |
| TDX 客户端 | 14571 | ✅ |
| Codex App | — | ⚠️ 侧装版，待升级 |

## 最近完成的任务

- WB-HANDOFF-0001 — 系统审计交接包
- ORG-CODEX-MERGE-0002 — 规则拆分审计
- ORG-CODEX-REVIEW-PACK-0003 — 候选协议审查包
- QUANT-MEMORY-SETUP-0001 — 永久记忆系统初始化 + ST修正

## 下一步优先级

1. 修订候选协议（回应 D-0004-v3 的 7 个阻断问题）
2. TdxQuant/eltdx PoC — L2 逐笔数据
3. 初始化 Git 仓库
4. 添加 walk-forward 回测框架

---

> 详细系统状态见: `coordination/SYSTEM-STATE.md`
> 记忆总纲见: `memory/QUANT-SYSTEM-MASTER-MEMORY.md`
