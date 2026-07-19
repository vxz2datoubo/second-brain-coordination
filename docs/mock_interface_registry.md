# Mock / Interface / Experimental Registry — SuperBrain + MaiBot 双脑系统

> 最后更新: 2026-07-09 03:20 GMT+8
> ⚠️ 关键规则: Mock / Interface / Experimental 禁止标记为 Done！
> 蓝图 §20: "不能把 Mock / Interface 写成完成"

---

## 使用说明

此文件登记所有系统中标注为 Mock、Interface（仅定义未实现）、Experimental 的组件。
目的是防止 Codex 或 AI 错误地将这些组件当作已完成功能，确保始终有清晰的"真实实现待办"追踪。

---

## Interface（接口已定义，无实现）

| ID | 名称 | 定义位置 | 接口签名 | 真实实现状态 | 备注 |
|----|------|----------|----------|-------------|------|
| IF-001 | BrainBridgeClient | 蓝图 §5.2 | ingest_conversation_event / query_relevant_memory / check_conflicts / ask_decision_support / plan_daily_task / simulate_future_outcomes / write_reflection / get_user_state | **NotStarted** | 8 个方法签名已定义，mcp/brain_bridge.py 有部分桥接代码待对齐 |
| IF-002 | EventMemory | 蓝图 §7.3 | event_id / title / start_time / end_time / date_precision / location / participants / status / confidence | **NotStarted** | 冲突检测核心模型，零实现 |
| IF-003 | ConflictRecord | 蓝图 §7.3 | conflict_id / conflict_type (7种) / severity / explanation / recommended_action | **NotStarted** | 零实现 |
| IF-004 | EmotionalState | 蓝图 §8.5 | valence / arousal / stress / anxiety / anger / sadness / excitement / fatigue / confidence | **Partial** | `human_thinking.py` 有部分实现，未完整对齐蓝图 |
| IF-005 | TaskRecord | 蓝图 §11.2 | task_id / title / description / due_at / priority / energy_level / status (10状态) / dependencies / related_goals | **NotStarted** | 零实现 |
| IF-006 | GoalRecord | 蓝图 §12.2 | goal_id / title / horizon (6级) / motivation / success_criteria / obstacles / status | **NotStarted** | 零实现 |
| IF-007 | UserEmotionSnapshot | 蓝图 §10.1 | user_id / valence / arousal / stress / fatigue / anxiety / anger / sadness / excitement / loneliness / confidence | **Partial** | `human_thinking.py` + `human-thinking-state.json` 有部分字段 |
| IF-008 | EmotionalPatternMemory | 蓝图 §10.2 | pattern_id / trigger / typical_state / helpful_response_style / harmful_response_style | **NotStarted** | 零实现 |
| IF-009 | BotAffectivePolicy | 蓝图 §10.3 | warmth / humor / directness / seriousness / brevity / initiative / emoji_level / challenge_level / comfort_level | **NotStarted** | 9 维度表达策略，零实现 |
| IF-010 | OrchestratorDecision | 蓝图 §13.2 | selected_agents / reason / required_tools / memory_queries / risk_level / user_confirmation_required | **NotStarted** | 多 Agent 编排器，零实现 |
| IF-011 | SelfDiagnosisRecord | 蓝图 §20.7 | diagnosis_id / problem_type (9类) / severity (4级) / symptoms / suspected_root_causes / recommended_action | **NotStarted** | 自我诊断核心模型，零实现 |
| IF-012 | RepairTicket | 蓝图 §20.7 | ticket_id / title / problem_statement / proposed_fix_type (7种) / risk_level / allowed_repair_scope / acceptance_tests | **NotStarted** | 维修票据核心模型，零实现 |
| IF-013 | SkillHealthRecord | 蓝图 §20.7 | skill_id / success_rate_7d / failure_rate_7d / user_correction_count_7d / health_status (5级) | **NotStarted** | 技能健康档案，零实现 |
| IF-014 | MCP 工具描述模板 | 蓝图 §9.2 | name / purpose / use_when / do_not_use_when / inputs / returns / safety | **NotStarted** | MCP 工具描述标准化，零实现 |
| IF-015 | 核心表 19 张 | 蓝图 §15.3 | conversation_events / memory_atoms / temporal_edges / person_profiles / emotion_snapshots / emotional_patterns / relationship_states / task_records / goal_records / calendar_events / commitment_records / conflict_records / decision_records / forecast_records / action_records / tool_call_traces / reflection_records / skill_registry / module_status / bulletin_state | **Partial** | 仅部分有 JSON 文件对应，无正式 schema |

---

## Mock（模拟实现，非真实功能）

| ID | 名称 | 位置 | Mock 内容 | 真实实现状态 | 备注 |
|----|------|------|-----------|-------------|------|
| MK-001 | ProceduralMemory (程序性记忆) | `core/` 多模块 | 依赖现有流程模拟，无独立实现 | **NotStarted** | 蓝图定义独立程序性记忆层 |
| MK-002 | superbrain_bridge 插件 Tool (Mock endpoint) | `F:\aipengyou\plugins\superbrain_bridge\plugin.py` | Phase 0 Mock: MemoryStore 内存模拟 + 3 Tool (query/check/write) | **Mocking** | Phase 0 骨架已完成，待 MaiBot 加载验证后推进 Phase 1 HTTP |

---

## Experimental（实验性，不稳定）

| ID | 名称 | 位置 | 实验内容 | 成熟度 | 备注 |
|----|------|------|----------|--------|------|
| EX-001 | conversation_dynamics.py | `F:\aipengyou\plugins\maibot_deskpet-plugin\conversation_dynamics.py` | 对话动力学: 根据聊天质量/话题完结/情绪自适间隔 | **Alpha** | 代码已创建(17273 bytes)，未集成到 plugin.py |
| EX-002 | news_radar.py | `F:\aipengyou\plugins\maibot_deskpet-plugin\news_radar.py` | 7 数据源新闻雷达 | **Beta** | 已集成，抖音成功/快手放弃 |
| EX-003 | info_feed.py | `F:\aipengyou\plugins\maibot_deskpet-plugin\info_feed.py` | 零 API 轻量信息反馈 | **Beta** | 已集成 |
| EX-004 | 抖音热搜 Direct API | `news_radar.py::_fetch_douyin_hotlist()` | aweme/v1/hot/search/list 官方 Android API | **Beta** | 零认证，不稳定（可能被限流） |
| EX-005 | ACT-R 认知模型 | `core/actr_memory.py` | ACT-R 记忆激活模型 | **Alpha** | 12787 bytes，单模块实现，未全局集成 |

---

## 统计

| 类别 | 数量 |
|------|------|
| Interface (接口已定义) | 15 |
| Mock (模拟实现) | 2 |
| Experimental (实验性) | 5 |
| **总计** | **22** |

**⚠️ 以上 22 个项目均不得标记为 Done。Done 仅用于真实实现且经过测试的组件。**
