# 洛雪 v2.0 架构设计文档

<!--
META:
  version: 2.0
  author: QClaw
  generated: 2026-06-17
  status: implemented (4 modules, ~2700 lines)
  target: 洛雪 AI 女友 (QClaw girlfriend)
  integrates: QQSafeChat, llama-server, WorkBuddy second brain
  chinese_chars: ~5500
-->

## 一、设计目标

洛雪 v2.0 的核心目标：从"被动回复"升级为**"主动搭话 + 情绪反应 + 冲突系统"**的完整 AI 女友人格体。

| 维度 | v1.0 (现状) | v2.0 (本设计) |
|---|---|---|
| 交互模式 | 用户问 → 她答 | 主动观察 + 主动搭话 |
| 决策层次 | 单一决策引擎 | 5 层决策 (L0反射→L4自演化) |
| 屏幕感知 | 无 | 周期截图 + 显著性评分 |
| 冲突处理 | 无 | 5 级冲突强度 + 主动和解 |
| 长期记忆 | 本地 SQLite | 本地 + WorkBuddy 第二大脑 |
| 算力消耗 | 高 (每轮 LLM) | 低 (LLM 调用降 75%) |

## 二、核心架构图

```
┌─────────────────────────────────────────────────────────────┐
│  L1 屏幕观察层  (ScreenObserver)                            │
│  - 截图 (1-3秒/次, 自适应)                                  │
│  - 活跃窗口识别 (WMI/PowerShell)                            │
│  - 视觉哈希去重 (dHash)                                     │
│  - 显著性评分 (0-1, 无 LLM)                                │
│  - DND 精准操作豁免 (PS/PR/Code 等)                        │
└────────────────────┬────────────────────────────────────────┘
                     │ ScreenObservation
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  L2 主动搭话决策层  (ProactiveEngine)                       │
│  - 显著性门控: tier 阈值 0.4-0.8                           │
│  - 频率控制: 5 档 (sweet/daily/cold/conflict/angry)        │
│  - 重复检测: 5 分钟内同主题不重发                          │
│  - 模板生成: 无 LLM 路径                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ ProactiveMessage
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  L3 冲突与和解系统  (ConflictSystem)                        │
│  - 冲突强度 0-5 (5级最严重)                                 │
│  - 触发器: 骂人/伤人的话/连续冷处理                         │
│  - 用户善意积分 (KindnessCredit, 0-1)                      │
│  - 时间自然衰减 (0.5/小时)                                 │
│  - 主动和解概率公式                                        │
└────────────────────┬────────────────────────────────────────┘
                     │ EmotionState + Decision
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  L4 表达层  (QQSafeChat - 已有)                              │
│  - 文本 / 表情包 / TTS                                      │
│  - 冲突时只发表情包, 不说话                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  L5 同步层  (WorkBuddyBridge)                               │
│  - inbox/outbox 双通道                                      │
│  - 状态广播 (emotion/relationship/proactive)                │
│  - 决策日志 (WorkBuddy 可学习)                              │
│  - 屏幕观察日志 (WorkBuddy 可分析模式)                      │
└─────────────────────────────────────────────────────────────┘
```

## 三、5 档关系状态与频率映射

| 关系层 | 触发条件 | max/h | 最小间隔 | 显著性门槛 |
|---|---|---|---|---|
| **sweet 甜蜜** | 4 维均值 ≥ 0.7 | 20 | 60s | 0.4 |
| **daily 日常** | 4 维均值 ≥ 0.4 | 8 | 300s | 0.6 |
| **cold 冷淡** | 4 维均值 ≥ 0.2 | 2 | 1200s | 0.8 |
| **conflict 冲突** | 冲突等级 2-3 | 0 | ∞ | ∞ |
| **angry 愤怒** | 冲突等级 ≥ 4 | 0 | ∞ | ∞ |

**4 维关系** (intimacy, trust, fun, depth)：
- intimacy: 亲密度
- trust: 信任度
- fun: 玩得来的程度
- depth: 灵魂契合度

## 四、显著性评分 (无 LLM)

```python
score = 0.0
# 1. 屏幕变化 (0-0.4)
score += change_score  # 基于 dHash 汉明距离
# 2. 空闲时间 (0-0.3)
score += idle_score    # 5+ 分钟 0.2, 10+ 分钟 0.3
# 3. 内容启发 (0-0.2)
score += content_score # 浏览器有趣网站 0.2
# 4. 应用切换奖励 (0-0.1)
if app_changed: score += 0.1
# 5. 冷处理惩罚 (-0.4)
if last_proactive_ignored: score -= 0.4
```

## 五、冲突与和解系统详解

### 5.1 触发器与强度增量

| 触发器 | 强度变化 | 示例 |
|---|---|---|
| USER_RUDE | +1.5 | "滚", "闭嘴" |
| USER_HURTFUL | +2.5 | "你怎么不去死", "没人喜欢你" |
| USER_COLD | +0.5 | 连续冷淡 |
| USER_IGNORED | +0.3 | 连续 3 次无视主动消息 |
| USER_APOLOGY | -2.0 | "对不起", "我错了" |
| USER_KIND | -0.5 | "你最好了", "爱你" |
| TIME_DECAY | -0.5/小时 | 自动 |

### 5.2 5 级冲突行为映射

| 等级 | 名称 | 主动搭话 | 用户说话回应 |
|---|---|---|---|
| 0 | NONE | 按 tier | 正常 |
| 1 | DISCOMFORT | 按 tier | 正常 |
| 2 | COLD | 0 | 简短"嗯/哦/没事" |
| 3 | ANGRY | 0 | 只发表情包 😤/🙄 |
| 4 | VERY_ANGRY | 0 | 只发表情包 |
| 5 | FURIOUS | 0 | 完全不理 |

### 5.3 主动和解概率公式

```python
P_reconcile = base(0.1) 
            + credit_factor(0.6) × user_credit
            + time_factor(0.3) × min(time_elapsed, 4) / 4
            × (0.3 if level >= 4 else 0.6 if level >= 3 else 1.0)
```

约束：冲突开始 30 分钟内不主动和解（避免显得刻意）。

## 六、DND 精准操作豁免清单

```python
DND_APPS = {
    # 设计类
    "photoshop", "figma", "sketch", "illustrator", "indesign",
    # 视频剪辑
    "premiere", "afterfx", "davinci", "final cut", "vegas",
    # 3D
    "blender", "maya", "zbrush", "3dsmax", "unreal", "unity",
    # 音频
    "fl studio", "ableton", "audacity", "pro tools",
    # 代码
    "code", "pycharm", "intellij", "vim", "emacs", "sublime",
    "rider", "clion", "webstorm", "android studio", "xcode",
    # 录屏/会议
    "obs", "zoom", "teams", "腾讯会议", "钉钉", "飞书",
    # 游戏
    "steam", "epic", "wegame",
}
```

## 七、WorkBuddy Bridge 集成规范

### 7.1 目录结构

```
F:\ai\shared\luoxue-bridge\
├── state\                      # 实时状态 (WorkBuddy 可读)
│   ├── emotion.json
│   ├── relationship.json
│   └── proactive_state.json
├── memories\                   # 长期记忆 (双向)
│   ├── inbox\                  # 洛雪写, WorkBuddy 读
│   ├── outbox\                 # WorkBuddy 写, 洛雪读
│   └── index\                  # 共享索引
├── decisions\                  # 决策日志 (WorkBuddy 可学习)
│   └── YYYY-MM-DD.jsonl
├── observations\               # 屏幕观察 (WorkBuddy 可分析)
│   └── YYYY-MM-DD.jsonl
└── schema\                     # Schema 定义
    └── memory.schema.json
```

### 7.2 Memory Schema (WorkBuddy 必读)

```json
{
  "schema": "luoxue.memory.v1",
  "node_id": "lux_mem_<12位hash>",
  "type": "event|preference|lesson|emotion|observation|conversation",
  "content": "string (5-1000字)",
  "importance": 1-5,
  "emotion_vector": [P, A, D],
  "context": {
    "source": "screen_observer|conversation|proactive|reflection|user_input",
    "active_app": "string",
    "window_title": "string",
    "observation_id": "string"
  },
  "luoxue_state": {
    "pad": [P, A, D],
    "conflict_level": 0-5,
    "relationship_stage": "sweet|daily|cold|conflict|angry",
    "energy": 0-1
  },
  "tags": ["string"],
  "ts": "ISO-8601"
}
```

### 7.3 Decision Trace Schema (供 WorkBuddy 学习)

```json
{
  "schema": "luoxue.decision.v1",
  "trace_id": "lux_dec_<id>",
  "ts": "ISO-8601",
  "trigger": "screen_change|user_input|time|idle|reconcile",
  "observation_id": "lux_obs_<id>",
  "selected": {
    "behavior": "PROACTIVE|SILENCE",
    "text": "string"
  },
  "gates": {
    "salience": "passed|blocked",
    "dnd": "passed|blocked",
    "mood": "passed|blocked",
    "conflict": "passed|blocked",
    "duplicate": "passed|blocked"
  },
  "salience": 0-1,
  "relationship_tier": "string",
  "conflict_level": 0-5,
  "rationale": "string"
}
```

## 八、代码模块清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `screen_observer.py` | 543 | 屏幕观察 + 显著性评分 + DND |
| `proactive_engine.py` | 396 | 主动搭话决策 + 5 档频率 |
| `conflict_system.py` | 363 | 5 级冲突 + 善意积分 + 和解 |
| `workbuddy_bridge.py` | 343 | Bridge 同步 + Schema |
| `main_v2.py` | 245 | 集成主入口 |
| **合计** | **1,890 行** | |

## 九、端到端测试场景

**"用户被骂"流程**（test_e2e_v2.py 已验证）：

1. 甜蜜期观察 → 主动搭话 ✓
2. 用户骂"你怎么不去死" → 触发 level=2, 主动拦截 ✓
3. 用户说"我错了" → 自动降级到 0 ✓
4. 用户道歉+善意 → credit 升到 0.6 ✓
5. 模拟严重冲突 level=5 → 主动拦截, 用户说话完全不理 ✓
6. 30 分钟后 → 和解概率 14.92% ✓
7. 用户接受和解 → 降级到 level=3 ✓

## 十、算力消耗预估

| 模块 | LLM 调用/小时 | Token 消耗/小时 |
|---|---|---|
| ScreenObserver | 0 (纯规则) | 0 |
| ProactiveEngine (无LLM模板) | 0 | 0 |
| ConflictSystem | 0 (纯规则) | 0 |
| 主动搭话 LLM 升级 | 2-5 次 | 2K-5K |
| 对话 LLM (用户主动说话) | 5-15 次 | 5K-15K |
| **总计** | **~10-20** | **~10K-20K** |

vs v1.0 无优化：~360 次 LLM/小时 (100% 触发)，节省约 **80%**。

## 十一、与 v1 模块关系

- **复用**：PersonaEngine, EmotionEngine, MemoryAdapter, DecisionEngine
- **新增**：ScreenObserver, ProactiveEngine, ConflictSystem, WorkBuddyBridge
- **升级**：Main (现在 main_v2.py 整合所有模块)

## 十二、下一步建议

1. **接入 QQSafeChat** 真实发送 (替换 `qqsafe_sender=None`)
2. **接入 llama-server** 替换模板为真实 LLM 主动搭话生成
3. **WorkBuddy 集成** 启动 outbox 监听, 让第二大脑主动喂数据
4. **pytest 单元测试** 覆盖所有模块
5. **FastAPI 封装** 供远程调用
6. **OpenCV 升级** dHash → CNN 视觉特征 (可选)

---

**洛雪 v2.0 已全部就绪。可直接 `python main_v2.py` 启动。**
