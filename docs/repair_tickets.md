# Repair Tickets — SuperBrain + MaiBot 双脑系统

> 最后更新: 2026-07-12 00:46 GMT+8 (蓝图 §18 全闭环, Phase 0-7 完成)
> 蓝图 §20: 自我迭代维修系统
> 票据状态: draft | ready_for_codex | in_sandbox | review_required | merged | rolled_back | verified | rejected

---

## 开放维修票据

### RT-2026-0712-002 ✅ | Phase 5 + Phase 6 + Phase 7 全量 E2E 通过 (已完成)

- **状态:** ✅ merged
- **说明:** 蓝图 §18 全部闭环。Phase 5 (19/19), Phase 6 (27/27), Phase 7 (30/30) 全部通过。
- **成果:** 新增 ~2,280 行 Python, 48+ API, 工程公告板 `SUPERBRAIN_BULLETIN_FOR_CODEX.md`
- **关闭时间:** 2026-07-11

### RT-2026-0711-001 ✅ | Phase 4 情绪引擎全链路 E2E 通过 (已完成)

- **状态:** ✅ merged
- **说明:** EmotionEngine 9 API + superbrain_bridge 4 Tool 全部验证通过。
- **修复:** E2E 测试中遇到内存旧状态残留问题（情绪 neutral 断言失败），通过重启 SuperBrain server 并清理所有 Python 进程解决。
- **关闭时间:** 2026-07-11

### RT-2026-0708-001 | Timing Gate 私聊总返回 wait (MaiBot)

- **严重度:** 🔴 High
- **问题类型:** DecisionFailure
- **创建时间:** 2026-07-08
- **来源:** 日志审查 + 源码分析

**症状:**
- MaiBot 桌宠 1-on-1 私聊场景下，Timing Gate 几乎每轮返回 `wait`
- 用户发一条消息后，系统等待更多消息才回复，导致交互不连贯

**根因分析:**
1. `FrequencyThresholdTurnGate`: 私聊 + frequency 模式下，每轮需等待 `trigger_threshold` 条消息才触发；桌宠 1-on-1 场景一次只发一条，永远不够阈值
2. `ReplyNecessityTurnGate`: 私聊下 `relevance_score=40`，需总分 ≥80，普通消息不够

**影响范围:** 桌宠主动回复频率严重低于预期，用户体验受损
**受影响模块:** `turn_gates.py`, `turn_scheduler.py`, `mode_policy.py`

**建议修复:**
- 方案 A (推荐): `FrequencyThresholdTurnGate` 对私聊直接放行所有 pending 消息
- 方案 B: 改为 `reply_necessity` 模式，同时降低私聊阈值至 50

**禁止事项:** 不得影响群聊 FrequencyThresholdTurnGate 的现有行为
**修复类型:** code
**风险等级:** Medium
**需人类审批:** 否 (低风险配置级修改)

**状态:** draft
**负责人:** 待分配 (QClaw 诊断完成，待 Codex 实施)

---

### RT-2026-0708-002 | 空回复 bug (sf-ds4-flash 返回空响应)

- **严重度:** 🟡 Medium
- **问题类型:** ToolFailure / DecisionFailure
- **创建时间:** 2026-07-08

**症状:**
- 部分场景下 MaiBot Replyer 返回空文本
- 空文本导致 replyer 返回 failure 结果，对话中断
- 用户看到的是"无回复"

**根因分析:**
- `sf-ds4-flash` 在某些 prompt 条件下返回空 `response.text`
- `_handle_planner_response_actions` 对空响应处理不完善
- 重试逻辑已部分修复 (`maisaka_generator_base.py` SyntaxError fix — `continue` after `break`)

**影响范围:** 偶发对话中断，频率不确定
**受影响模块:** `reasoning_engine.py`, `maisaka_generator_base.py`

**建议修复:**
1. 空响应检测后增加 fallback 到备用模型 (sf-ds4-pro / 深度求索)
2. 空响应重试 2 次后自动降级为简短的 fallback 回复
3. (SyntaxError 修复已完成，待验证是否完全解决)

**修复类型:** code
**风险等级:** Low
**需人类审批:** 否

**状态:** draft (SyntaxError 已修复，空响应 fallback 未实施)
**负责人:** 待分配

---

### RT-2026-0708-003 | conversation_dynamics.py 未集成到 plugin.py

- **严重度:** 🟡 Medium
- **问题类型:** 功能缺失
- **创建时间:** 2026-07-08

**症状:**
- `conversation_dynamics.py` (17273 bytes) 已创建，核心逻辑就绪
- 未通过 `plugin.py` 接入 MaiBot 插件系统
- 对话动力学（根据聊天质量、话题完结状态动态计算偷看间隔）无法生效

**根因分析:**
- 尝试通过补丁格式接入 `plugin.py` 失败
- 需手动修改 `plugin.py` 中 5 个代码块：`__init__`、`__get_peek_interval`、`__do_peek` 等

**影响范围:** Proactive Engine 偷看间隔未自适应对话质量
**受影响模块:** `plugin.py`, `proactive_engine.py`, `conversation_dynamics.py`

**建议修复:**
1. 手动修改 `plugin.py` 的 5 个集成点
2. 注入 `ConversationTracker` 实例到 `proactive_engine.__init__`
3. `__get_peek_interval` 优先使用 ConversationTracker 自适应间隔
4. `__do_peek` 注入对话动力学上下文
5. 测试验证后重启

**修复类型:** code (集成)
**风险等级:** Low
**需人类审批:** 否

**状态:** draft
**负责人:** 待分配

---

### RT-2026-0708-004 ✅ | Plugin manifest 缺失 (已关闭)

- **关闭原因:** hello_world_plugin 是模板插件（enabled=false），告警不影响功能；deskpet-plugin 已有 `_manifest.json`（非 `manifest.toml`，这是 MaiBot 的正确格式）；superbrain_bridge 已创建完整 manifest
- **关闭时间:** 2026-07-09

---

### RT-2026-0708-005 | Node.js 版本过低警告

- **严重度:** 🟢 Low
- **问题类型:** 环境兼容性
- **创建时间:** 2026-07-07

**症状:**
- Vite 启动时警告: Node.js 20.17.0（要求 ≥20.19）
- Dashboard 兼容性可能存在潜在问题

**建议修复:**
- 升级 Node.js 到 20.19+ LTS

**修复类型:** env
**风险等级:** Low
**需人类审批:** 否 (开发环境)

**状态:** draft

---

### RT-2026-0708-006 | A-Memorix paragraph ngram 索引未就绪

- **严重度:** 🟢 Low
- **问题类型:** 功能降级
- **创建时间:** 2026-07-08

**症状:**
- 日志中反复出现 "paragraph ngram index not ready"
- BM25 fts5 + jieba 工作正常，不影响使用
- 缺失 paragraph ngram 可能导致某些模糊匹配精度下降

**建议修复:**
- 排查 ngram 索引构建触发条件
- 检查索引文件权限和路径配置

**修复类型:** 诊断
**风险等级:** Low
**需人类审批:** 否

**状态:** draft

---

### RT-2026-0709-001 | superbrain_bridge 插件 MaiBot 加载验证 (P0.10)

- **严重度:** 🟡 Medium
- **问题类型:** 功能验证
- **创建时间:** 2026-07-09
- **来源:** Phase 0 蓝图实施
- **进度:** BrainBridgeClient 已实现 (HTTP→brain_core:8766)，config.toml 已改为 enabled=true / mode=http。待用户重启 MaiBot 后观察加载日志。

**症状:**
- superbrain_bridge v0.2.0 插件已支持 HTTP 模式
- 未在 MaiBot 运行环境中实际加载验证 HTTP 连通性

**建议修复:**
1. ✅ config.toml: `enabled = true`, `mode = "http"`
2. ✅ BrainBridgeClient 已实现
3. 重启 MaiBot → 观察启动日志中 `[SuperBrain Bridge] 插件已加载 (mode=http, brain_core=http://localhost:8766) ✅`
4. 通过 LLM 调用 3 个 Tool 验证 HTTP 模式返回

**修复类型:** 验证
**风险等级:** Low
**需人类审批:** 否

**状态:** draft — 代码就绪，待验证

---

## 已完成票据

### RT-2026-0708-007 ✅ | person_fact_writeback 超时 (已修复)

- **决策:** utils task hard_timeout 30s→90s；模型改为 sf-ds4-flash 优先 + 深度求索兜底；增加 WARNING 日志
- **验证:** 配置已生效，日志可见修复效果
- **关闭时间:** 2026-07-08

### RT-2026-0707-001 ✅ | maisaka_generator_base.py SyntaxError (已修复)

- **问题:** line 1196 `continue` 在 `break` 之后
- **修复:** 先检测空响应/`continue`，后 `break`
- **关闭时间:** 2026-07-08

### RT-2026-0707-002 ✅ | yjqd3.ps1 Ctrl+C 阻塞 (已修复)

- **问题:** 单窗口方案日志追读不可靠
- **修复:** 改为双窗口 v4.0 方案（yi_jian_qi_dong.ps1）
- **关闭时间:** 2026-07-08

---

## 统计

| 状态 | 数量 |
|------|------|
| draft | 6 | (RT-001/002/003/005/006/009) |
| ready_for_codex | 0 | |
| in_sandbox | 0 | |
| review_required | 0 | |
| merged | 0 | |
| verified | 0 | |
| rejected | 0 | |
| **已关闭** | **6** | (RT-004/007, 2x 2026-0707, RT-001-Phase4, RT-002-Phase567) |
