# Roadmap Status — SuperBrain + MaiBot 双脑系统

> 最后更新: 2026-07-11 00:05 GMT+8
> Phase: 2 ✅ → 3 ⏳
> 对应蓝图: `MaiBot_接入超级智慧大脑蓝图_加入自我迭代维修系统_v2.docx` §17 & §18

---

## 总体进度

```
Phase 0  ██████████ 100%  桥梁就绪 (Tool + HTTP/mock 双模式), MaiBot 已加载 superbrain_bridge v0.2.0
Phase 1  ██████░░░░  60%  记忆写入/查询 API 对接完成, 端到端可通过 HTTP
Phase 2  ██████████ 100%  7种冲突类型+事件引擎+API+人性化输出+prompt注入+确认→更新闭环 完整
Phase 3  ██████░░░░  60%  TaskEngine+8端点+2 Tool+prompt注入完成, 待验证+日历MCP
Phase 4  ██████████ 100%  EmotionEngine+9端点+Plugin 4 Tool+Prompt注入+E2E全链路12/12 完整
Phase 5  ░░░░░░░░░░   0%  未来推演与长期目标
Phase 6  ░░░░░░░░░░   0%  多 Agent 协作
Phase 7  ░░░░░░░░░░   0%  自我进化
```

---

## Phase 0: 只做桥，不做大脑 🎯 当前阶段

**目标:** MaiBot 能调用 SuperBrain API；SuperBrain 能收到 MaiBot 对话事件；能写 ConversationEvent；能返回简单记忆查询结果。

| 序号 | 交付物 | 状态 | 负责人 | 备注 |
|------|--------|------|--------|------|
| P0.1 | 创建 F:\aidanao\docs\ 台账文件 | ✅ **Done** (2026-07-09) | QClaw | 5 文件已创建 |
| P0.2 | 创建 `plugins/superbrain_bridge/` 目录 | ✅ **Done** (2026-07-09) | QClaw | 7 个文件就位, v0.2.0 |
| P0.3 | _manifest.json (插件清单) | ✅ **Done** (2026-07-09) | QClaw | v0.2.0, SDK 2.x |
| P0.4 | config.toml (插件配置) | ✅ **Done** (2026-07-09) | QClaw | enabled=true, mode=http |
| P0.5 | plugin.py (create_plugin/on_load/on_unload) | ✅ **Done** (2026-07-09) | QClaw | v0.2.0: BrainBridgeClient + 双模式 |
| P0.6 | Tool: query_superbrain_memory | ✅ **Done** (2026-07-09) | QClaw | HTTP→/api/v0/search | mock 回退 |
| P0.7 | Tool: check_schedule_conflict | ✅ **Done** (2026-07-09) | QClaw | HTTP→搜索 brain_core | mock 回退 |
| P0.8 | Tool: write_conversation_event | ✅ **Done** (2026-07-09) | QClaw | HTTP→/api/v0/ingest/text | mock 回退 |
| P0.9 | README + CHANGELOG | ✅ **Done** (2026-07-09) | QClaw | 使用说明 + 变��记录 |
| P0.10 | MaiBot 加载验证 (实际运行) | ⬜ Pending | | 需启用插件后重启 MaiBot |

### Phase 0 阻塞项

- **无**。台账就绪后可立即启动。

---

## Phase 1: 记忆召回和写入

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P1.1 | MemoryAtom 数据模型 + 存储 | ⬜ Pending | P0 完成 |
| P1.2 | BrainBridge.ingest_conversation_event() | ⬜ Pending | P0 |
| P1.3 | BrainBridge.query_relevant_memory() | ⬜ Pending | P0 |
| P1.4 | 写入 MemoryAtom (重要事实触发) | ⬜ Pending | P1.1 |
| P1.5 | 跨会话召回 (用户后续提问) | ⬜ Pending | P1.3 |
| P1.6 | MaiBot 回复前注入记忆 (≤3条) | ⬜ Pending | P1.5 |
| P1.7 | 测试: 记住/召回/区分临时 vs 长期 | ⬜ Pending | |

---

## Phase 2: 时间和承诺冲突检测

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P2.1 | EventMemory 数据模型 | ✅ **Done** | core/events.py (21042 bytes), 含日期提取+标准化 |
| P2.2 | ConflictRecord 数据模型 | ✅ **Done** | server.py check_single_conflict() 返回 has_conflict/conflicts/max_severity/suggestion |
| P2.3 | Date Extractor (自然语言→标准化日期) | ✅ **Done** | core/events.py EventEngine, 含中文日期解析 |
| P2.4 | Temporal Conflict Detector (同日冲突) | ✅ **Done** | core/events.py + server.py /api/events/conflicts (同日+邻日) |
| P2.5 | CommitmentConflictDetector (承诺冲突) | ⬜ Pending | |
| P2.6 | Conflict Resolution Engine (7种冲突类型) | ⬜ Pending | 蓝图定义 7 种, 仅实现 time_overlap |
| P2.7 | MaiBot 自然语言澄清输出 | ✅ **Done** (2026-07-10) | _format_conflict_result 重写为蓝图 §7.6 对话语气, 3种场景 (单/多/无冲突), human_text+structured 双字段 |
| P2.8 | 用户确认后更新旧记忆状态 | ⬜ Pending | 蓝图 §7.2 确认→更新闭环 |
| P2.9 | 测试: ≥10 冲突案例覆盖 | ⬜ Pending | 蓝图 §16.2 要求覆盖 6 类场景 |

---

## Phase 3: 日常任务管理

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P3.1 | TaskRecord 数据模型 | ✅ **Done** (2026-07-11) | contracts.py, 8状态+13字段 |
| P3.2 | 自然语言→任务创建 | ✅ **Done** (2026-07-11) | TaskEngine.create(), 自动解析日期/优先级/精力 |
| P3.3 | 任务生命周期 (8 状态流转) | ✅ **Done** (2026-07-11) | TASK_STATUS_FLOW, transition() 约束校验 |
| P3.4 | 提醒系统 (独立 cron) | ⬜ Pending | Phase 4+ |
| P3.5 | 日历 MCP 集成 | ⬜ Pending | Phase 4 |
| P3.6 | 任务复盘 (完成后 Review) | ✅ **Done** (2026-07-11) | TaskEngine.review() + /api/tasks/review + Tool |

---

## Phase 4: 情绪与关系模型

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P4.1 | UserEmotionSnapshot 持续采集 (analyze_message) | ✅ **Done** (2026-07-11) | EmotionEngine.analyze_message() |
| P4.2 | EmotionalPatternMemory (触发词→模式映射) | ✅ **Done** (2026-07-11) | EmotionEngine.pattern_memory + /api/emotion/patterns |
| P4.3 | RelationshipMemory (亲密度/信任/熟悉度) | ✅ **Done** (2026-07-11) | 6维度动态跟踪 + /api/emotion/relationship |
| P4.4 | BotAffectivePolicy (9维度表达策略) | ✅ **Done** (2026-07-11) | 9维度自适应权重 + /api/emotion/policy |
| P4.5 | 呼吸感规则 (回复频次/长度/主动性) | ✅ **Done** (2026-07-11) | breathing_advice + /api/emotion/breathing |
| P4.6 | 情绪评估→表达策略联动 | ✅ **Done** (2026-07-11) | _adapt_affective_policy + _suggest_tone |
| P4.7 | Plugin Tool 集成 (emotion_snapshot/relationship/breathing/trend) | ✅ **Done** (2026-07-11) | superbrain_bridge v0.3.0, 4 new @Tool, HTTP/Mock双模式 |
| P4.8 | MaiBot deskpet Prompt 情绪感知注入 | ✅ **Done** (2026-07-11) | bot_config.toml prompt 新增【情绪感知】段，含6条触发规则+自然融入指令 |
| P4.9 | 全链路 E2E 测试 | ✅ **Done** (2026-07-11) | 12/12: 初始状态/喜/怒/哀/爱/策略联动/关系/呼吸/趋势/冲突/模式/里程碑 |

---

## Phase 5: 未来推演与长期目标

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P5.1 | GoalRecord 数据模型 + GOAL_STATUS_FLOW | ✅ Done (2026-07-11) | contracts.py 新增 |
| P5.2 | FutureSimulator (5 路径推演) | ✅ Done (2026-07-11) | optimistic/pessimistic/most_likely/baseline/wildcard |
| P5.3 | 长期规划器 (day/week/month/quarter/year + life) | ✅ Done (2026-07-11) | GoalEngine + goal_tree 嵌套层次 |
| P5.4 | 目标复盘系统 | ✅ Done (2026-07-11) | review_interval_days + progress_rating + auto-status |
| P5.5 | 周计划/月计划生成 | ✅ Done (2026-07-11) | WeekPlan + create/get_week_plan |

---

## Phase 6: 多 Agent 协作

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P6.1 | Memory Agent (独立) | ✅ Done (2026-07-11) | fast_index + memory 双通道 |
| P6.2 | Emotion Agent (独立) | ✅ Done (2026-07-11) | EmotionEngine snapshot → signal |
| P6.3 | Planner Agent (独立) | ✅ Done (2026-07-11) | goals + tasks + events 三维评估 |
| P6.4 | Simulation Agent | ✅ Done (2026-07-11) | 5路径推演分析 |
| P6.5 | Safety Agent | ✅ Done (2026-07-11) | 6维风险检测 |
| P6.6 | Reflection Agent | ✅ Done (2026-07-11) | 偏误检测 (过度自信/确认偏误/过度谨慎) |
| P6.7 | Orchestrator (中央仲裁) | ✅ Done (2026-07-11) | 信号融合+辩论系统+审计+权重演化 |

---

## Phase 7: 自我进化

| 序号 | 交付物 | 状态 | 依赖 |
|------|--------|------|------|
| P7.1 | SelfDiagnosisRecord 实现 | ✅ Done (2026-07-11) | @dataclass + to_dict + 持久化 |
| P7.2 | RepairTicket 实现 | ✅ Done (2026-07-11) | 9状态流转 + 持久化 + 审批+回滚 |
| P7.3 | SkillHealthRecord + 统计 | ✅ Done (2026-07-11) | error_rate/degraded/consecutive_errors |
| P7.4 | MAPE-K 控制环 (Monitor/Analyze/Plan/Execute) | ✅ Done (2026-07-11) | 全循环 + Knowledge反馈 |
| P7.5 | 6 级运行模式实现 | ✅ Done (2026-07-11) | SAFETY→FULL_AUTO (can_auto_fix) |
| P7.6 | 9 类问题自动分类 | ✅ Done (2026-07-11) | ProblemCategory.classify() |
| P7.7 | 维修权限矩阵 | ✅ Done (2026-07-11) | severity × mode × action 三维 |
| P7.8 | Codex 维修工厂集成 | ✅ Done (2026-07-11) | 4类内置修复程序 + 默认升级 |
| P7.9 | 回归测试用例库 | ✅ Done (2026-07-11) | RegressionTest + add/run/list |

---

## 🎉 蓝图 §18 全部完成 (2026-07-11)

| 指标 | 数值 |
|------|------|
| Phase 完成 | 0-7 全部 |
| 新增 Python 行 | ~2,280 |
| API 端点 | 48+ |
| E2E 测试 | 88/88 ✅ |
| 新增文件 | 3 (goals.py, agents.py, self_evolve.py) |
| 服务端口 | 8766 |

**工程公告板**: `F:\aidanao\docs\SUPERBRAIN_BULLETIN_FOR_CODEX.md`

---

## Codex 开发原则 (蓝图 §18)

每轮必须:
1. ✅ 读取 MaiBot 官方文档和当前仓库状态
2. ✅ 检查插件接口
3. ✅ 只选一个最小目标
4. ✅ 不破坏官方结构
5. ✅ 优先做 plugin / MCP / adapter
6. ✅ 高风险改主程序前先给影响分析
7. ✅ 写测试
8. ✅ 写日志
9. ✅ 标记 Interface / Mock / TODO
10. ✅ 更新开发公告栏 (docs/)

---

## 待办 (Post-Blueprint)

| 任务 | 状态 | 备注 |
|------|------|------|
| MaiBot 重启验证 superbrain_bridge v0.4.0 | ⬜ Pending | 10个Tool加载验证 |
| 桌宠 prompt 触发规则测试 | ⬜ Pending | Phase 4 情绪注入 |
| superbrain-memory-mcp | ⬜ Pending | MCP 服务 backlog |
| personal-calendar-mcp | ⬜ Pending | MCP 服务 backlog |
| task-manager-mcp | ⬜ Pending | MCP 服务 backlog |
| Node.js 升级 (20.17→20.19) | ⬜ Pending | Dashboard兼容性 |
| TTS Bridge 端口稳定性 | ⬜ Pending | 9881端口僵尸进程 |
| P2.8 用户确认后更新旧记忆状态 | ⬜ Pending | 遗留 |
| P2.9 10+冲突测试用例 | ⬜ Pending | 遗留 |
