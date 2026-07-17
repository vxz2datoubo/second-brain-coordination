# 洛雪 v2.0 代码模块元数据

<!--
META:
  version: 2.0
  author: QClaw
  generated: 2026-06-17
  status: implemented
  target: 洛雪 AI 女友 v2.0
  chinese_chars: ~1800
-->

## 模块总览

| # | 文件 | 行数 | 字节 | 角色 | 状态 |
|---|---|---|---|---|---|
| 1 | `screen_observer.py` | 543 | 22039 | 屏幕观察 + 显著性 | ✅ 跑通 |
| 2 | `proactive_engine.py` | 396 | 16407 | 主动搭话决策 | ✅ 跑通 |
| 3 | `conflict_system.py` | 363 | 13065 | 冲突/和解 | ✅ 跑通 |
| 4 | `workbuddy_bridge.py` | 343 | 15925 | 第二大脑同步 | ✅ 跑通 |
| 5 | `main_v2.py` | 245 | 11236 | 集成主入口 | ✅ 跑通 |
| 6 | `test_e2e_v2.py` | 130 | 3889 | 端到端测试 | ✅ 通过 |
| 7 | `test_proactive.py` | 50 | 1377 | Proactive 单元测试 | ✅ 通过 |
| 8 | `test_conflict.py` | 38 | 1028 | Conflict 单元测试 | ✅ 通过 |
| **合计** | | **2,108** | **84,966** | | |

## 模块详细说明

### 1. ScreenObserver (543 行)

**核心类**：
- `ScreenObserver` - 屏幕观察主类
- `WindowsAPI` - Windows API 封装 (GetForegroundWindow, GetLastInputInfo)
- `VisualHash` - dHash 感知哈希 (8x8)
- `ScreenObservation` - 观察数据类
- `ChangeLevel` - 变化级别枚举

**关键方法**：
- `capture_screenshot()` - PIL ImageGrab 截图
- `is_dnd(app, title)` - DND 检测
- `compute_salience()` - 显著性评分 (5 维度加权)
- `is_duplicate(visual_hash)` - 哈希去重 (汉明距离)
- `observe()` - 单次观察 (截→识→评→重→存)
- `start_loop(callback)` - 后台循环
- `_write_to_bridge()` - 写入 bridge

**统计**：
- 截 1 张图耗时 < 100ms
- 显著性计算 < 5ms
- dHash 计算 < 10ms
- 单次 observe 总耗时 < 150ms

### 2. ProactiveEngine (396 行)

**核心类**：
- `ProactiveEngine` - 主动搭话决策主类
- `RelationshipSnapshot` - 关系四维快照
- `ProactiveMessage` - 主动消息对象
- `RelationshipTier` - 5 档关系 (sweet/daily/cold/conflict/angry)
- `Config.FREQ_TIERS` - 5 档频率配置

**关键方法**：
- `should_proactive(obs)` - 8 道门控检查
- `generate_message(obs)` - 模板生成主动消息
- `handle_user_input_in_conflict(text)` - 冲突期回应
- `attempt_reconcile()` - 主动和解尝试
- `_detect_trigger()` - 触发类型识别
- `_extract_variables()` - 模板变量提取
- `get_stats()` - 统计接口

**5 档频率配置**：
```python
{
    "sweet":    {"max_per_hour": 20, "min_interval_sec": 60,   "salience_threshold": 0.4},
    "daily":    {"max_per_hour": 8,  "min_interval_sec": 300,  "salience_threshold": 0.6},
    "cold":     {"max_per_hour": 2,  "min_interval_sec": 1200, "salience_threshold": 0.8},
    "conflict": {"max_per_hour": 0,  "min_interval_sec": 99999, "salience_threshold": 999},
    "angry":    {"max_per_hour": 0,  "min_interval_sec": 99999, "salience_threshold": 999},
}
```

### 3. ConflictSystem (363 行)

**核心类**：
- `ConflictSystem` - 冲突与和解主类
- `ConflictLevel` - 5 级冲突强度
- `ConflictTrigger` - 触发器枚举
- `ConflictState` - 冲突状态持久化
- `TriggerDetector` - 关键词触发检测

**触发器检测**：
- HURTFUL_PATTERNS: "你不懂", "你怎么不去死", "跟你说话真累"...
- RUDE_WORDS: "滚", "傻逼", "闭嘴", "讨厌你"...
- APOLOGY_PATTERNS: "对不起", "我错了", "抱歉"...
- KIND_PATTERNS: "辛苦了", "谢谢你", "爱你"...

**关键方法**：
- `on_user_input(text)` - 处理用户输入
- `_apply_trigger()` - 应用触发强度
- `_update_credit()` - 更新善意积分
- `tick(hours)` - 时间衰减
- `get_reconcile_probability()` - 和解概率
- `accept_reconcile()` - 接受和解
- `save_state()` / `_load_state()` - 持久化

**核心公式**：
```python
# 主动和解概率
P = base(0.1) + 0.6 * credit + 0.3 * min(time_elapsed, 4) / 4
if level >= 4: P *= 0.3
elif level >= 3: P *= 0.6
```

### 4. WorkBuddyBridge (343 行)

**核心类**：
- `WorkBuddyBridge` - Bridge 同步主类
- `Config` - 路径配置
- `BridgeWriteResult` - 写入结果
- `SCHEMA_MEMORY_V1` - JSON Schema 定义

**目录结构**：
```
F:\ai\shared\luoxue-bridge\
├── state/          # 实时状态
├── memories/inbox/ # 洛雪写
├── memories/outbox/# WorkBuddy 写
├── memories/index/ # 共享索引
├── decisions/      # 决策日志
├── observations/   # 屏幕观察
└── schema/         # Schema 定义
```

**API 方法**：
- `write_memory(type_, content, importance, ...)` - 写入记忆
- `read_outbox(since_ts)` - 读取 WorkBuddy 推送
- `write_state(name, data)` - 状态广播
- `write_emotion_state(pad, conflict, stage)`
- `write_relationship_state(intimacy, trust, fun, depth)`
- `write_proactive_state(hourly, tier, triggered, blocked)`
- `write_decision(trace)` - 决策日志
- `write_observation(obs)` - 观察日志
- `get_sync_status()` - 同步状态查询
- `clear_processed(node_ids)` - 清理 outbox

**Memory Schema** (WorkBuddy 必读):
```json
{
  "schema": "luoxue.memory.v1",
  "node_id": "lux_mem_<12hash>",
  "type": "event|preference|lesson|emotion|observation|conversation",
  "content": "string (5-1000)",
  "importance": 1-5,
  "emotion_vector": [P, A, D],
  "context": { "source": "...", "active_app": "...", ... },
  "luoxue_state": { "pad": [...], "conflict_level": 0-5, ... },
  "tags": [...],
  "ts": "ISO-8601"
}
```

### 5. MainV2 (245 行)

**核心类**：
- `LuoxueV2` - 集成主类
  - 复用 v1: PersonaEngine, EmotionEngine, MemoryAdapter, DecisionEngine
  - 新增 v2: ScreenObserver, ProactiveEngine, ConflictSystem, WorkBuddyBridge

**关键方法**：
- `on_observation(obs)` - 屏幕观察回调
- `on_user_input(text)` - 用户输入处理
- `_send_message(msg)` - 发送 (经 QQSafeChat)
- `_sync_state()` - 状态同步
- `start()` / `stop()` - 启动停止
- `get_full_status()` - 完整状态

## 集成测试结果

### test_e2e_v2.py 端到端测试

**"用户被骂"8 步流程**：

| 阶段 | 输入 | 预期 | 实际 |
|---|---|---|---|
| 1 | 甜蜜期观察 | 主动搭话 | ✓ "哔, 又上 bilibili?" |
| 2 | "你怎么不去死" | 触发 level=2, 主动拦截 | ✓ level=2, 拦截 |
| 3 | "我错了" | 道歉触发, 降级 | ✓ level=0 |
| 4 | "对不起, 你最好了" | credit 升 | ✓ credit=0.6 |
| 5 | 模拟冲突 5 | 主动拦截, 用户说话完全不理 | ✓ FURIOUS |
| 6 | 30 分钟后 | 和解概率 14.92% | ✓ |
| 7 | 用户接受和解 | 降级到 level=3 | ✓ |
| 8 | Bridge 同步 | 正常 | ✓ 7 条 inbox, 3 条 decisions |

## 运行方式

```bash
# 1. 单元测试
python F:\ai\girlfriend\test_proactive.py
python F:\ai\girlfriend\test_conflict.py

# 2. 端到端测试
python F:\ai\girlfriend\test_e2e_v2.py

# 3. 启动主循环 (需要 QQSafeChat 真实集成)
python F:\ai\girlfriend\main_v2.py
```

## 下一步

1. 接入 QQSafeChat 真实发送 (`qqsafe_chat_sender=实际函数`)
2. 接入 llama-server 替换模板为 LLM 主动生成
3. WorkBuddy 端启动 outbox 监听
4. 编写 pytest 单元测试
5. FastAPI 封装 (供远程/移动端调用)

## 文件清单 (绝对路径)

- `F:\ai\girlfriend\screen_observer.py`
- `F:\ai\girlfriend\proactive_engine.py`
- `F:\ai\girlfriend\conflict_system.py`
- `F:\ai\girlfriend\workbuddy_bridge.py`
- `F:\ai\girlfriend\main_v2.py`
- `F:\ai\girlfriend\test_e2e_v2.py`
- `F:\ai\girlfriend\test_proactive.py`
- `F:\ai\girlfriend\test_conflict.py`
- `F:\ai\shared\luoxue-bridge\` (运行时生成)
- `F:\ai\qclaw-output\luoxue-v2-architecture.md`
- `F:\ai\qclaw-output\luoxue-v2-modules.md` (本文件)
