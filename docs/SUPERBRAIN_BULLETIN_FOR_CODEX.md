# 🧠 SuperBrain 第二大脑 — 工程公告板

> **受众**: Codex、WorkBuddy、QClaw、所有后续 AI Agent
> **最后更新**: 2026-07-11 18:00
> **状态**: 🟢 Phase 0-7 全部完成 (88 E2E / 88 passed)
> **版本**: v1.0 (blueprint §18 complete)

---

## 🏗️ 架构总览

```
F:\aidanao\              ← SuperBrain 项目根目录
├── server.py            ← HTTP API 服务 (8766端口)
├── brain_core/
│   └── contracts.py     ← 数据契约 (所有 @dataclass)
├── core/
│   ├── memory.py        ← MemoryEngine + FeedbackLoop
│   ├── graph.py         ← KnowledgeGraph (JSON持久化)
│   ├── digest.py        ← TextDigester / FileDigester
│   ├── tfidf.py         ← BM25 搜索引擎
│   ├── syncer.py        ← WorkBuddySyncer
│   ├── events.py        ← EventEngine + 冲突检测
│   ├── tasks.py         ← TaskEngine (任务管理)
│   ├── emotion.py       ← EmotionEngine (情绪感知)
│   ├── goals.py         ← GoalEngine (目标/推演) — Phase 5
│   ├── agents.py        ← 多Agent协作 — Phase 6
│   ├── self_evolve.py   ← MAPE-K 自我进化 — Phase 7
│   ├── memory_health.py ← MemoryHealthManager
│   ├── fast_index.py    ← FastIndex
│   ├── human_thinking.py← HumanThinkingEngine
│   ├── verify.py        ← SelfVerify
│   ├── cognitive.py     ← CognitiveEngine
│   ├── actr.py          ← ACT-R Memory
│   └── evolve.py        ← EvolutionEngine (基础评估)
├── data/                ← 持久化数据 (JSON)
│   ├── graph.json       ← 知识图谱
│   ├── agent_weights.json
│   ├── decision_audit/  ← 决策审计记录
│   ├── repair_tickets/  ← 维修票据
│   ├── diagnosis/       ← 自诊断记录
│   ├── regression_tests/← 回归测试用例
│   └── repair_backups/  ← 修复前备份
└── docs/                ← 工程文档
    ├── implementation_status.md
    ├── roadmap_status.md
    ├── decision_log.md
    ├── repair_tickets.md
    └── mock_interface_registry.md
```

## 🔌 外部集成

```
F:\aipengyou\              ← MaiBot 项目
└── plugins\
    └── superbrain_bridge\ ← 桥接插件 (v0.4.0)
        ├── _manifest.json
        ├── plugin.py      ← 10个 @Tool
        └── ...
```

---

## 📊 引擎清单 (按 Phase)

| Phase | 引擎 | 文件 | 行数 | API数 |
|-------|------|------|------|-------|
| 0 | 工程台账 + 插件骨架 | — | — | — |
| 1 | 记忆桥 + BrainBridgeClient | plugin.py | ~1200 | 3 Tool |
| 2-3 | EventEngine + TaskEngine | events.py, tasks.py | ~800 | 10+ |
| 4 | EmotionEngine | emotion.py | ~500 | 9 |
| 5 | GoalEngine | goals.py | ~600 | 15 |
| 6 | 多Agent Orchestra | agents.py | ~540 | 6 |
| 7 | MAPE-K 自我进化 | self_evolve.py | ~640 | 18 |

---

## 🚀 启动方式

```powershell
# 1. 确保用的是 MaiBot 的虚拟环境
& "F:\aipengyou\.venv\Scripts\python.exe" F:\aidanao\server.py
# 监听: http://127.0.0.1:8766

# 2. 验证存活
Invoke-RestMethod http://127.0.0.1:8766/api/v0/status
# → {"version": "v0.1"}

# 3. 运行完整 E2E
& "F:\aipengyou\.venv\Scripts\python.exe" C:\Users\Administrator\.qclaw\workspace\sessions\tmp\phase7_e2e_test.py
```

## 🧪 E2E 测试脚本位置

```
C:\Users\Administrator\.qclaw\workspace\sessions\tmp\
├── phase4_e2e_test.py    ← 情绪引擎 (12 tests)
├── phase5_e2e_test.py    ← 目标推演 (19 tests)
├── phase6_e2e_test.py    ← 多Agent (27 tests)
└── phase7_e2e_test.py    ← 自我进化 (30 tests)
```

---

## 🔑 关键 API 端点 (全部)

### Phase 4 — 情绪感知
```
GET  /api/emotion/snapshot    — 情绪快照
GET  /api/emotion/trend       — 趋势
GET  /api/emotion/timeline    — 时间线
GET  /api/emotion/breathing   — 呼吸建议
GET  /api/emotion/health      — 关系健康
POST /api/emotion/record      — 记录情绪
POST /api/emotion/event       — 触发情绪事件
GET  /api/emotion/stress-test — 压力测试
POST /api/emotion/policy      — 策略管理
```

### Phase 5 — 目标推演
```
POST /api/goal/create         — 创建目标
GET  /api/goal/list           — 列表
GET  /api/goal/tree           — 目标树
POST /api/goal/transition     — 状态流转
POST /api/goal/milestone      — 里程碑
POST /api/goal/review         — 复盘
POST /api/goal/delete         — 删除(级联)
GET  /api/goal/stats          — 统计
GET  /api/goal/health         — 健康检查
GET  /api/goal/reviews-due    — 逾期复盘
POST /api/goal/simulate       — 未来推演(5路径)
GET  /api/goal/paths          — 已存推演路径
POST /api/goal/weekplan-create— 生成周计划
GET  /api/goal/weekplan       — 获取周计划
```

### Phase 6 — 多Agent
```
POST /api/agent/orchestrate   — 完整决策流程
GET  /api/agent/weights       — 权重快照
GET  /api/agent/stats         — 统计
POST /api/agent/outcome       — 记录结果+更新胜率
GET  /api/agent/audits        — 审计列表
GET  /api/agent/audit?id=xxx  — 单条审计
```

### Phase 7 — 自我进化
```
POST /api/evolve/cycle                    — MAPE-K 循环
GET  /api/evolve/diagnose                 — 自诊断
GET  /api/evolve/stats                    — 进化统计
GET  /api/evolve/mode                     — 查看模式
POST /api/evolve/mode                     — 设置模式
POST /api/evolve/circuit-breaker/reset    — 重置熔断
POST /api/evolve/skill-call               — 记录技能调用
GET  /api/evolve/tickets                  — 票据列表
GET  /api/evolve/ticket?id=xxx            — 单张票据
POST /api/evolve/ticket/update            — 更新票据
POST /api/evolve/ticket/approve           — 批准维修
POST /api/evolve/ticket/rollback          — 回滚修复
GET  /api/evolve/regression-tests         — 回归测试列表
POST /api/evolve/regression-tests/run     — 运行回归测试
POST /api/evolve/regression-tests/add     — 添加回归用例
```

---

## 🧬 核心设计决策

### 信号融合公式 (Phase 6)
```
Fusion_Score = Σ(W_i × Signal_i × Confidence_i) / Σ(W_i)
→ > +0.3 = proceed
→ < -0.3 = avoid
→ else  → 升级辩论 (Bull vs Bear → Judge)
```

### Agent 权重演化
- 滚动窗口 (10笔) `win_rate` → W_i
- 连续3错 → 权重减半 (熔断)
- 持久化: `data/agent_weights.json`

### MAPE-K 控制环 (Phase 7)
```
Monitor → Analyze → Plan → Execute
              ↑_______________↓
                 Knowledge Base

深度限制: 3层 (防无限递归)
熔断: 连续3次失败 → 暂停自动修复
备份: 修复前自动创建 .bak 快照
```

### 6 级运行模式
| 级别 | 模式 | 自动修复 |
|------|------|---------|
| 0 | SAFETY | 仅报告 |
| 1 | OBSERVATION | 记录日志 |
| 2 | DIAGNOSTIC | 分析报告 (默认) |
| 3 | ADVISORY | 生成建议，需确认 |
| 4 | SEMI_AUTO | 低风险(<3)自动 |
| 5 | FULL_AUTO | 全自动+回滚 |

---

## 📋 待办 / 下一步

### MaiBot 集成层 (尚未完成)
- [ ] MaiBot 重启后验证 superbrain_bridge plugin v0.4.0 加载
- [ ] 验证 10 个 Tool 全部可被 LLM 调用
- [ ] 桌宠 prompt 注入触发规则测试
- [ ] 完整对话→情绪记录→目标推演 E2E

### MCP 服务 backlog (Phase 8? 不在蓝图中)
- [ ] superbrain-memory-mcp (记忆查询 MCP)
- [ ] personal-calendar-mcp (日历 MCP)
- [ ] task-manager-mcp (任务管理 MCP)

### 性能优化
- [ ] 技能健康追踪集成到 superbrain_bridge（目前仅 record_skill_call API）
- [ ] Node.js version 升级 (20.17→20.19 Dashboard要求)

---

## ⚠️ 已知坑

1. **Python 环境**: 必须用 `F:\aipengyou\.venv\Scripts\python.exe`，系统 python 缺少依赖
2. **端口 8766**: 启动前 `taskkill /F /IM python.exe` 避免僵尸进程
3. **AW_PYTHON_BINARY**: 环境变量导致 Python stdout stderr 混入，不影响功能
4. **parse_qs**: GET 路由用 `parse_qs(p.query)` 传入，handler 从 dict 取参；参数值是 list 格式
5. **空回复防御**: 插件层面已有连续3次空回复自动重试
6. **TTS Bridge 端口 9881**: 偶尔被僵尸进程占用，启动脚本有按端口杀进程逻辑

---

## 📞 给后续 AI Agent 的话

如果你被派来做 SuperBrain 相关工作，按这个顺序了解：

1. **读本文件** ← 你在这里
2. **看 `F:\aidanao\docs\roadmap_status.md`** — Phase 状态
3. **看 `F:\aidanao\docs\implementation_status.md`** — 实现细节
4. **看 `F:\aidanao\docs\decision_log.md`** — 关键决策记录
5. **运行 server.py** 确认服务存活
6. **运行 phase7_e2e_test.py** 确认全量测试通过
7. **然后开始你的工作** 🚀

所有 Phase 0-7 已完成。当前最可能的工作方向：
- MaiBot 集成测试和调优
- MCP 服务开发
- 性能优化和健康监控完善
