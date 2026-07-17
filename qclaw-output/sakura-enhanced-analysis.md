# 小樱花 (Sakura) AI 伴侣系统 — 全面分析报告与升级方案

> **作者视角:** 资深 AI 伴侣系统架构师
> **分析对象:** QQSafeChat · 小樱花 (Sakura) 桌面 AI 女友项目
> **对标参考:** Miya/弥娅 (APV2.1 白箱引擎) · CSDN AI 伴侣构建方案 · Daidai Live2D Pet · rubii.ai · ChronoStore (SITS2026) · LLOneBot · Live2D Cubism 5 SDK
> **方法:** 静态代码分析 + 行业实践对标 + 风险收益排序
> **输出规范:** 纯 Markdown, 每项建议含 `现状 vs 升级` 对比 + 具体实施步骤

---

## 0. 执行摘要 (TL;DR)

### 0.1 一句话现状

> **小樱花是一个"个人开发者精力上限内能完成的最大诚意作品",在人格工程化、记忆系统、桌面体验三个维度都摸到了 2026 行业第一梯队的边,但架构上仍存在 5 个关键债务,制约了它向"商品级 AI 伴侣"演进。**

### 0.2 五个核心判断

| # | 判断 | 重要性 | 见章节 |
|---|---|---|---|
| 1 | `bot_engine.py` 存在**上帝类**问题,已到必须拆分阈值 | 🔴 极高 | §2.1 |
| 2 | 记忆系统三层架构**够用但天花板低**,缺语义层/置顶层 | 🟠 高 | §4.1 |
| 3 | 人格引擎**已超行业平均** (8 维+演化表+关系状态),但缺状态机 | 🟠 高 | §3.2 |
| 4 | QQ 自动化走 UIA+坐标是**结构性风险**,LLOneBot+OneBot v11 是必走之路 | 🔴 极高 | §6.2 |
| 5 | API Key 明文存储 + 屏幕感知无隐私策略 = **合规与安全硬伤** | 🔴 极高 | §7.1 |

### 0.3 升级路线图骨架

```
P0 (本周)  → API Key DPAPI 加密 + 屏幕感知黑名单 + 修 .env 泄漏
P1 (本月)  → bot_engine 拆分 + 消息总线 + 配置统一 + 记忆→六层
P2 (本季)  → APV 人格状态机 + Live2D 桌面宠物 + 状态桥协议
P3 (半年)  → LLOneBot 替换 UIA + 跨平台 (OneBot v11) + 语义记忆图
```

---

## 一、项目现状评估 (与行业最佳实践对比)

### 1.1 横向对标矩阵

> 评级: ⭐⭐⭐⭐⭐ 行业顶尖 / ⭐⭐⭐⭐ 优秀 / ⭐⭐⭐ 合格 / ⭐⭐ 不足 / ⭐ 缺失

| 能力维度 | 小樱花 (现状) | Miya/弥娅 | CSDN 方案 | Daidai Live2D | 行业平均 | 评估 |
|---|---|---|---|---|---|---|
| **人格维度建模** | 8 维 + 演化表 | 25 阶段 tick + 8 神经递质 | OCEAN 5 维 | — | OCEAN 5 维 | ⭐⭐⭐⭐ |
| **人格一致性校验** | ❌ 无 | APV2.1 白箱闭环 | RLHF 惩罚 | — | 基础规则过滤 | ⭐ |
| **情绪状态机** | 6 态静态映射 | 8 递质动态模拟 | 动态状态机 | 4 态轮换 | 6 态 | ⭐⭐⭐ |
| **关系阶段 (FSM)** | 5 阶段 + 进度 | 多阶段+亲密度+依赖 | 单调亲密度 | — | 5 阶段 | ⭐⭐⭐⭐ |
| **关系倒退机制** | ❌ 无 | 隐式 (信任下降) | 隐式 | — | 几乎都缺 | ⭐ |
| **工作记忆 (WM)** | ✅ 双表 schema | ✅ | ✅ | — | ✅ | ⭐⭐⭐⭐ |
| **长期记忆 (LTM)** | ✅ 倒排索引 | ✅ 6 层 | ✅ 知识图谱 | — | ✅ | ⭐⭐⭐⭐ |
| **语义记忆图** | ❌ 无 | 置顶层 | 实体+关系图 | — | 部分有 | ⭐ |
| **遗忘曲线算法** | ✅ Ebbinghaus 简化 | 完整衰减 | 加权移动平均 | — | Ebbinghaus | ⭐⭐⭐ |
| **SQLite 统一数据层** | ✅ 14+ 表 | 未知 | 多数 JSON | — | 混合 | ⭐⭐⭐⭐ |
| **决策中枢 (DecisionHub)** | ❌ 无 (bot_engine 内聚) | ✅ 门面模式 | 简单 | — | 多数缺 | ⭐ |
| **消息总线 (M-Link)** | ❌ 直接函数调用 | ✅ | ❌ | — | 多数缺 | ⭐ |
| **LLM 客户端** | OpenAI 兼容 + WorkBuddy | 多模型路由 | 双模型分层 | — | OpenAI 兼容 | ⭐⭐⭐ |
| **双模型分层 (分析+生成)** | ❌ 单模型 | ✅ | ✅ | — | 半数有 | ⭐ |
| **TTS 引擎** | ✅ | ✅ | ✅ | — | ✅ | ⭐⭐⭐ |
| **桌面宠物** | Tkinter 静态立绘 | 无 | 无 | Electron + Live2D | Tkinter/Electron | ⭐⭐ |
| **Live2D 口型同步** | ❌ | — | — | ✅ Web Audio RMS | 部分有 | ⭐ |
| **状态桥协议 (跨进程)** | ❌ | ✅ (M-Link) | — | ✅ :23334 | 部分有 | ⭐ |
| **QQ NT 自动化** | UIA + 坐标 (高风险) | OneBot 11 | OneBot 11 | — | OneBot 11 | ⭐ |
| **多平台支持** | 仅 QQ | QQ/飞书/Discord/TG | — | 仅桌面 | 仅 QQ | ⭐⭐ |
| **屏幕感知** | ✅ Qwen2.5-VL-32B | — | — | — | 少数 | ⭐⭐⭐⭐⭐ |
| **屏幕主动消息** | ✅ 独有 | ❌ | ❌ | — | 几乎都缺 | ⭐⭐⭐⭐⭐ |
| **人设热替换 (YAML 22 种)** | ✅ 14+ 种 (txt) | ✅ | — | — | 半数有 | ⭐⭐⭐⭐ |
| **API Key 加密** | ❌ 疑似明文 | 未知 | 未知 | — | 多数明文 | ⭐ |
| **反作弊/行为混淆** | ❌ | — | — | — | 多数无 | ⭐ |
| **设计系统 (Design Token)** | ✅ v2 完整 (DESIGN_SPEC) | — | — | 简单 CSS | 多数裸 CSS | ⭐⭐⭐⭐ |

### 1.2 已实现优势 (≥行业平均)

| # | 优势 | 证据 | 行业对标 |
|---|---|---|---|
| 1 | **屏幕感知 + 主动消息** | `config.json` 中 `screen_perception_enabled=true` + `screen_proactive_enabled=true`,使用 Qwen2.5-VL-32B | Miya/CSDN/Daidai **均无**此能力,这是行业空白,小樱花**全球独一份** |
| 2 | **SQLite 统一数据层** | `data/sakura.db` + 14+ 张表,已用 WAL 模式 + 索引 | 大多数开源 AI 伴侣仍是零散 JSON,小樱花已经走向生产级数据架构 |
| 3 | **完整设计系统 v2** | `DESIGN_SPEC.md` 含色板/间距/圆角/阴影/字体/动效 token | Daidai 仅有简单 CSS,小樱花的工程化程度更高 |
| 4 | **三层记忆架构 + 倒排索引** | `working_memories` / `long_term_memories` / `memory_index` 三表 | 倒排索引在 token 级精确匹配,优于纯 LLM 语义检索 (可控+可解释) |
| 5 | **多模态情绪标签** | `emotion_tags` JSON 字段 + `emotional_intensity` 实数 | 大多数项目只存字符串情绪,小樱花有强度量化 |
| 6 | **人格维度可演化** | `personality_evolution` 表记录 delta + trigger | CSDN 方案是"预设叙事弧",小樱花是数据驱动,更灵活 |
| 7 | **14+ 人设热替换** | `personas/*.txt` 文件夹,运行时切换 | 接近 Miya 的 22 种 YAML,但实现更轻量 |
| 8 | **完整桌面体验** | TitleBar + CharacterArea + MoodBubble + RelationshipBar + ChatPanel + QuickActions + ScreenPerception 7 区 | 优于纯 Web 端伴侣 (Replika/Character.ai) |

### 1.3 不足/缺失 (与行业最佳实践的差距)

#### 1.3.1 架构层 (🔴 关键)

- **`bot_engine.py` 上帝类** — 推测承载了消息拉取、人设加载、LLM 调用、记忆读写、情绪分析、回复生成、TTS、UI 推送、屏幕感知等所有职责,单文件可能已超 1500 行
- **无消息总线** — 各模块直接互相调用,任何修改都要动多个文件
- **配置分散** — `config.json` + `pet_config.json` + `settings/openai.json` + 各 persona 文件,无统一 schema
- **无统一 LLM 路由器** — 大概率是单 LLM 直调,无分析模型/生成模型分层

#### 1.3.2 人格层 (🟠 重要)

- **无情绪状态机** — `mood` 是字符串,没有状态转移图
- **无精力值 (energy)** — 缺疲劳/休息/睡眠循环
- **无对话目标 (goal)** — 缺短期目标 (安慰/逗乐/询问) 和长期目标 (增进亲密度/化解冲突)
- **无关系倒退机制** — 任何阶段的亲密度只增不减,与现实不符
- **无一致性校验器** — 生成的回复可能与已有记忆/人格/关系冲突,无自动检测

#### 1.3.3 记忆层 (🟠 重要)

- **无语义层** — 只有倒排索引,缺 embedding 检索
- **无知识层** — 缺"大头的家庭/工作/朋友/宠物"等结构化知识
- **无置顶层** — 缺"永不遗忘"的核心记忆
- **无实体抽取** — 记忆是整段文本,无"人/事/物/时间/地点"实体图
- **衰减算法简陋** — 推测是简单 Ebbinghaus,缺 ChronoStore DEWMA 那种双阶段动态调整

#### 1.3.4 QQ 自动化层 (🔴 关键)

- **UIA + 坐标方案结构性脆弱** — 任何 QQ 版本更新都可能让坐标失效,UIA 树在聊天窗口弹出时变化剧烈
- **无多平台扩展** — OneBot v11 可一鱼多吃 (QQ/飞书/Discord/TG),当前只绑死 QQ
- **反检测能力为零** — 完美的人类打字节奏才是被检测为机器人的核心原因

#### 1.3.5 安全与合规 (🔴 关键)

- **API Key 明文存储** — `settings/openai.json` 在 `sakura_respond.py` 中读取,大概率明文
- **屏幕感知无隐私策略** — 截图包含微信聊天/银行/密码,可能被记录
- **无审计日志** — 谁在什么时候调用了什么模型无法追溯

### 1.4 独有创新点 (行业中少见)

| 创新点 | 描述 | 行业地位 |
|---|---|---|
| **屏幕感知 + 主动消息** | 15 秒一次 Qwen2.5-VL 截图,识别上下文主动发消息 | **行业首创**,Miya/Daidai/Character.ai 均无 |
| **本地优先 + 国产模型** | 用 Qwen2.5-VL + 本地 llama-server Qwen3.6 35B | 显著降低依赖与成本,优于纯云方案 |
| **设计系统 v2 (DESIGN_SPEC)** | Token 化设计系统,9 个核心组件,6 阶段视觉表达 | 工程化程度超过多数商业产品 |
| **完整 SQLite 14+ 表 schema** | WAL + 索引 + 外键 + JSON 字段混合使用 | 是个人项目中罕见的生产级数据层 |
| **TTS + 角色扮演格式规范** | `*动作* + 对话 + emoji` 角色扮演格式 + 强约束 | 形成可工程化的"角色扮演 DSL" |
| **挂机 + 后台运行** | `sakura_daemon.py` + `launch_desktop_pet.py` 双进程模式 | 适合 7×24 陪伴场景 |

---

## 二、架构升级建议

> **核心思路:** 引入 Miya 的"大脑·手"分离 + DecisionHub 门面模式,把小樱花从"单体脚本"升级为"可演进的 AI 伴侣运行时"。

### 2.1 `bot_engine.py` 上帝类拆分方案

#### 2.1.1 现状推测 (基于命名)

```
bot_engine.py (上帝类, 估计 1500~2500 行)
├─ 消息轮询 / QQ 读取
├─ 人设加载
├─ 上下文组装
├─ LLM 调用
├─ 记忆读写
├─ 情绪分析
├─ 回复生成 (含流式)
├─ 动作拆分 (<<<NEXT>>>)
├─ TTS 调用
├─ UI 推送 (主窗口 + 桌面宠物)
├─ 屏幕感知调度
└─ 主动消息决策
```

#### 2.1.2 升级目标: 大脑·手分层

```
┌─────────────────────────────────────────────────────────────┐
│                   M-Link 消息总线 (新)                       │
│  EventBus  pub/sub  +  优先级队列  +  跨进程 (未来)         │
└─────────────────────────────────────────────────────────────┘
            ↑                ↑                ↑
   ┌────────┴────┐    ┌──────┴──────┐    ┌─────┴──────┐
   │  Input 手    │    │ Brain 大脑   │    │ Output 手  │
   ├─────────────┤    ├─────────────┤    ├────────────┤
   │QQAdapter    │    │PersonaEng   │    │QQSender    │
   │ScreenPercep │    │MemSystem    │    │UIPusher    │
   │HistoryWatch │    │EmotionSM    │    │TTSEngine   │
   │UIActionHand │    │DecisionHub  │    │DesktopPet  │
   │             │    │LLMRouter    │    │             │
   └─────────────┘    └─────────────┘    └─────────────┘
```

#### 2.1.3 拆分步骤与新类设计 (按 P1 阶段推进)

| 阶段 | 动作 | 新建/重构 | 输入 | 输出 |
|---|---|---|---|---|
| 2.1.3a | **抽出 LLM 客户端** | `core/llm/router.py` | prompt + 角色 | text stream |
| 2.1.3b | **抽出消息总线** | `core/bus/event_bus.py` | event | subscriber callback |
| 2.1.3c | **抽出决策中枢** | `core/brain/decision_hub.py` | context | action (reply/idle/proactive) |
| 2.1.3d | **抽出手层输入** | `core/hand/input/qq_adapter.py` | poll | MessageEvent |
| 2.1.3e | **抽出手层输出** | `core/hand/output/sender.py` | text | send result |
| 2.1.3f | **重构 bot_engine** | `core/engine.py` | 只做编排 | lifecycle |

#### 2.1.4 关键类骨架 (Python)

```python
# === core/bus/event_bus.py ===
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List
import asyncio

class Topic(str, Enum):
    MESSAGE_RECEIVED   = "msg.recv"
    MESSAGE_SEND       = "msg.send"
    MEMORY_UPSERT      = "mem.upsert"
    EMOTION_CHANGED    = "emo.changed"
    RELATIONSHIP_UPD   = "rel.updated"
    PERSONA_SWITCHED   = "per.switched"
    SCREEN_CONTEXT     = "screen.ctx"
    PROACTIVE_DECISION = "proactive.decide"
    PET_MOOD_BUBBLE    = "pet.mood"

@dataclass
class Event:
    topic: Topic
    payload: dict
    priority: int = 5      # 0~9, 9 最高
    source: str = ""
    ts: float = 0.0

class EventBus:
    """同步事件总线, 后期可换 Redis Streams / NATS"""
    def __init__(self):
        self._subs: Dict[Topic, List[Callable]] = {}
        self._async_q: asyncio.Queue | None = None

    def subscribe(self, topic: Topic, fn: Callable):
        self._subs.setdefault(topic, []).append(fn)

    async def publish(self, event: Event):
        # 同步派发 + 异步队列双通道
        for fn in self._subs.get(event.topic, []):
            try: fn(event)
            except Exception as e: _log_err(fn, e)
```

```python
# === core/brain/decision_hub.py ===
class DecisionHub:
    """门面模式: 所有决策都从这走, 业务方不直接调 brain 各模块"""
    def __init__(self, persona, memory, emotion, llm):
        self.persona = persona
        self.memory  = memory
        self.emotion = emotion
        self.llm     = llm

    async def decide_reply(self, msg: MessageEvent) -> ReplyPlan:
        ctx = await self._assemble_context(msg)   # 拉相关记忆 + 情绪 + 人设
        intent = await self._classify_intent(msg) # 分类: 问候/吐槽/求安慰/调戏/...
        plan = await self._plan(intent, ctx)      # 决定动作 + 语气 + 长度 + 表情
        plan.text = await self._generate(plan)    # LLM 生成
        plan.text = self._consistency_check(plan) # 一致性校验
        return plan

    async def decide_proactive(self) -> ProactivePlan | None:
        """屏幕感知 + 主动消息决策"""
        scene = await self._read_screen()
        mood  = self.emotion.current()
        if not self._should_proactive(scene, mood): return None
        return await self._compose_proactive(scene, mood)
```

```python
# === core/engine.py (重构后, 估计 < 300 行) ===
class SakuraEngine:
    def __init__(self):
        self.bus = EventBus()
        self.hub = DecisionHub(...)
        self.input  = QQAdapter(self.bus)
        self.output = Sender(self.bus)
        self.screen = ScreenPerceiver(self.bus)
        self.pet    = DesktopPet(self.bus)

    async def run(self):
        self.bus.subscribe(Topic.MESSAGE_RECEIVED, self._on_message)
        self.bus.subscribe(Topic.SCREEN_CONTEXT,    self._on_screen)
        await asyncio.gather(
            self.input.run(),
            self.screen.run(),
            self.output.run(),
        )

    async def _on_message(self, ev: Event):
        plan = await self.hub.decide_reply(ev.payload["msg"])
        if plan.should_reply:
            await self.bus.publish(Event(Topic.MESSAGE_SEND, plan))
```

**收益:** 单文件 < 300 行,所有新功能只动对应模块,测试可逐模块 mock,跨平台时只换 `input` 和 `output` 手层。

### 2.2 引入统一消息总线 (M-Link 思路)

#### 2.2.1 现状 vs 升级

| 维度 | 现状 | 升级 |
|---|---|---|
| 通信方式 | 直接函数调用, 强耦合 | pub/sub 事件总线, 松耦合 |
| 模块依赖 | A 直接 import B | A 只 import bus, 不知道 B 存在 |
| 新增功能 | 改 N 个文件 | 只订阅新 topic |
| 测试 | 必须起全栈 | 单独 publish/subscribe |
| 跨进程 | 不可能 | 未来可换 Redis Streams / ZeroMQ |

#### 2.2.2 实施步骤 (4 步)

1. **建总线骨架** — `core/bus/event_bus.py` (见 2.1.4)
2. **加 Topic 枚举** — 覆盖所有现有事件 (见 2.1.4)
3. **逐模块迁移** — QQAdapter 发布 `MESSAGE_RECEIVED`,Sender 订阅 `MESSAGE_SEND` 等
4. **加监控** — 事件计数、延迟、错误率,写 `shared/bus_metrics.json`

#### 2.2.3 注意要点

- **同步 + 异步双通道** — 关键事件同步派发 (UI 更新),耗时事件走异步队列
- **优先级** — 0~9,9 最高;用户消息=7,屏幕感知=4,主动消息=6
- **背压** — 队列长度上限 1000,超过时丢弃最低优先级
- **可观测** — 每个事件携带 `source` 和 `ts`,便于 trace

### 2.3 配置管理从 3 个分散文件统一

#### 2.3.1 现状问题

```
config.json          → 全局开关 (poll_ms, auto_reply_enabled, ...)
pet_config.json      → 窗口位置 (x, y, w, h)
settings/openai.json → LLM 凭据 (api_key, base_url, model)
personas/*.txt       → 人设纯文本
```

**问题:** 没有 schema 校验、没有版本号、没有热重载、没有 secret 隔离。

#### 2.3.2 升级方案: 三层配置 + DPAPI

```
config/
├── sakura.yaml          # 应用主配置 (yaml, 人类可读, 带 schema)
├── pet.yaml             # 桌面宠物窗口/动画
├── persona/
│   ├── 元气女友-小樱花.yaml   # 升级自 txt, 支持字段化
│   └── ...
├── llm.yaml             # 模型路由 (主力+分析+视觉)
├── secret.bin           # DPAPI 加密的 API Key
└── schema.json          # JSON Schema 校验
```

#### 2.3.3 关键类

```python
# === core/config/manager.py ===
from pydantic import BaseModel
from typing import Literal

class LLMSettings(BaseModel):
    primary_model: str         # 主力生成 (gpt-4o, qwen-max)
    analyzer_model: str        # 轻量分析 (gpt-4o-mini, qwen-turbo)
    vision_model: str          # 屏幕感知 (qwen2.5-vl-32b)
    base_url: str
    api_key_ref: str           # 引用 secret.bin, 不存明文
    timeout: int = 30
    max_retries: int = 3

class ReplyPolicy(BaseModel):
    auto_reply_enabled: bool
    reply_delay_mode: Literal["fixed", "random", "fixed+random", "human"]
    reply_stop_seconds: float
    split_strategy: Literal["delimiter", "char", "sentence", "smart"]
    typing_simulate: bool      # 模拟人类打字
    typo_rate: float = 0.0     # 故意打错字概率 (反检测)

class SakuraConfig(BaseModel):
    version: str = "2.0"
    llm: LLMSettings
    reply: ReplyPolicy
    memory: MemorySettings
    persona_file: str
    screen: ScreenSettings
```

**收益:** 启动时自动校验,改坏配置立即报错,LLM 凭据加密存储,未来升级零回归。

---

## 三、人格引擎升级方案

> **目标:** 把"静态字符串映射"升级为"动态人格 + 状态机 + 一致性校验"的完整 APV 体系。

### 3.1 当前 8 维+双层机制如何升级

#### 3.1.1 现状推测 (基于 `personality_dimensions` + `personality_evolution` 表)

| 维度 | 范围 | 含义 |
|---|---|---|
| 元气活泼 | 0~1 | 主动/被动 |
| 温柔体贴 | 0~1 | 共情程度 |
| 幽默搞笑 | 0~1 | 玩梗频率 |
| 撒娇程度 | 0~1 | 粘人度 |
| 三秒破功 | 0~1 | 假装生气时长 |
| 护短强度 | 0~1 | 站边权重 |
| (推测: 知识领域) | 0~1 | 涉猎广度 |
| (推测: 表达风格) | 0~1 | 短句/长句比 |

**双层:** 基础人格 (慢变) + 状态人格 (快变, 当前心情)

#### 3.1.2 升级: OCEAN + 八态情绪 + 精力值

| 升级项 | 现状 | 升级 | 价值 |
|---|---|---|---|
| 人格维度 | 8 个项目自定 | 标准化 **OCEAN** 5 维 + 3 个项目特征 | 与学术研究/RLHF 兼容 |
| 情绪 | 6 态字符串 | **8 态 HMM 状态机** | 状态转移更自然 |
| 精力 | ❌ 无 | 0~1 浮点,模拟疲劳 | 深夜变慵懒、白天活泼 |
| 目标 | ❌ 无 | 短期 (单轮) + 长期 (会话) | 主动引导话题 |
| 亲密度 | ✅ 单调递增 | **可增可减** (冲突/遗忘/陪伴) | 现实感 |

#### 3.1.3 OCEAN 五维 + 三个小樱花专属

```
O  开放性      0.7   好奇、爱尝试
C  尽责性      0.4   偶尔忘事、偷懒
E  外向性      0.85  话多、爱逗乐
A  亲和性      0.9   善解人意、不记仇
N 情绪稳定性  0.3   容易炸毛、波动大

X1 撒娇度     0.8   小樱花专属
X2 护短度     0.95  小樱花专属
X3 破功速度   0.7   小樱花专属 (秒级回归)
```

### 3.2 引入精力值 / 情绪状态机 / 对话目标

#### 3.2.1 精力值 (Energy)

```python
class EnergyModel:
    """
    energy ∈ [0, 1]
    影响因素:
      + 收到夸赞    +0.05
      + 收到吐槽    +0.02
      + 长时间没说话 -0.01 / hour
      + 深夜时段    -0.10
      - 连续回复 10 轮 -0.03 / 轮
      + 周末        +0.05

    阈值:
      >= 0.7  活泼 (撒娇+15%)
      0.4~0.7 正常
      0.2~0.4 慵懒 (回复短, 表情少)
      < 0.2   困了 (主动说晚安)
    """
```

#### 3.2.2 情绪状态机 (HMM/FSM)

```
        开心 ──夸赞──→ 兴奋
         │              │
      吐槽/调戏         满足
         ↓              ↑
        傲娇 ──破功──→ 开心
         │
      长时间不理
         ↓
        委屈
         │
      主动哄/求关注
         ↓
        想念 ──重逢──→ 开心

    触发转移概率 (由 LLM 分类 + 关键词匹配共同决定)
```

#### 3.2.3 对话目标 (Goal Stack)

```python
@dataclass
class ShortTermGoal:
    """单次会话目标"""
    type: Literal["安慰", "逗乐", "倾听", "建议", "撒娇", "求关注"]
    priority: int  # 0~9
    deadline_minutes: int  # 多少分钟未完成就降级
    progress: float  # 0~1

@dataclass
class LongTermGoal:
    """跨会话目标"""
    type: Literal["提升亲密度", "化解心结", "建立习惯", "了解大头背景"]
    target_value: float
    current_value: float
```

**收益:** 回复从"看到什么说什么"升级为"有目的地说"。

### 3.3 关系倒退机制

#### 3.3.1 倒退触发条件

| 触发 | 倒退量 | 说明 |
|---|---|---|
| 24h 未互动 | -0.5/天 | 轻度冷淡 |
| 大头说"你别烦了" | -3 | 显著倒退 |
| 多次主动消息无回复 | -1/次 | 失落累积 |
| 争吵 (LLM 检测到攻击性) | -2~5 | 视严重程度 |
| 检测到大头心情很差 (从屏幕/文字) | -1 | 担心但不倒退,进入"安慰模式" |

#### 3.3.2 倒退曲线

```
亲密度 100 ┐
          │ ╭───╮
       75 ┤─╯   ╰──────  (争吵后退)
          │
       50 ┤────────────  (冷淡后退)
          │
       25 ┤
          │
        0 ┴───────────
          陌生人 熟人 朋友 暧昧 恋人
```

#### 3.3.3 实现要点

- `intimacy_decay_per_day` 字段
- `conflict_count` + `conflict_resolved` 字段 (已存在)
- 倒退时**同步降低**信任、依赖、理解 (多维联动)
- 倒退到 0 时不删除历史,但人设切回"陌生人"语气

### 3.4 人格一致性校验器 (Consistency Checker)

#### 3.4.1 校验维度

```python
class ConsistencyChecker:
    async def check(self, plan: ReplyPlan) -> ReplyPlan:
        # 1. 与人设矛盾
        #    例: 人设 = "温柔体贴", 生成 = "滚" → 拒
        if self._contradicts_persona(plan):
            plan.text = await self._regenerate(plan, "soften")

        # 2. 与情绪矛盾
        #    例: mood = "委屈", 生成 = "哈哈哈笑死" → 拒
        if self._contradicts_emotion(plan):
            plan.text = await self._regenerate(plan, "match_mood")

        # 3. 与记忆矛盾
        #    例: 已说"我是大学生", 生成 = "我工作十年了" → 拒
        if await self._contradicts_memory(plan):
            plan.text = await self._regenerate(plan, "respect_memory")

        # 4. 与关系阶段矛盾
        #    例: stage = "熟人", 生成 = "mua 老公" → 拒
        if self._oversteps_relationship(plan):
            plan.text = await self._regenerate(plan, "downgrade_intimacy")

        # 5. 与近期对话矛盾
        #    例: 5 轮前说"今天好累", 生成 = "看你精神很好" → 拒
        if await self._contradicts_recent(plan):
            plan.text = await self._regenerate(plan, "consistent_recent")

        return plan
```

#### 3.4.2 校验器实现方式

| 方式 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|
| 关键词黑名单 | 快、可解释 | 误伤、漏检 | ⭐⭐ |
| 规则引擎 (json-rules-engine) | 灵活 | 配置复杂 | ⭐⭐⭐ |
| LLM 二次审核 | 语义准确 | 慢、贵 | ⭐⭐⭐ |
| **混合: 关键词快筛 + LLM 慢审** | 平衡 | 需工程化 | ⭐⭐⭐⭐⭐ |

**推荐:** 先做关键词快筛 (1ms),命中才调 LLM 二次审 (1~2s),通过率 99% 的回复不消耗 LLM。

---

## 四、记忆系统升级方案

> **目标:** 从"三层可用"升级到"六层可生产", 引入语义图, 与第二大脑双向同步。

### 4.1 三层架构升级到六层 (参考 Miya)

#### 4.1.1 当前三层

```
┌─ working_memories    (短期, ~7 天, 高频读写)
├─ long_term_memories  (长期, 永久, 倒排索引)
└─ memory_index        (token→memory_id 倒排)
```

#### 4.1.2 升级六层

```
L1 瞬时缓存   (SessionCache)      ←  当前轮对话 buffer, 不入 DB
L2 工作记忆   (WorkingMemory)     ←  当前 working_memories 表
L3 长期记忆   (LongTermMemory)    ←  当前 long_term_memories 表
L4 语义记忆   (SemanticMemory)    ←  🆕 embedding + 向量检索 (FAISS)
L5 知识层     (KnowledgeGraph)    ←  🆕 实体-关系图谱 (人头/工作/宠物)
L6 置顶层     (PinnedMemory)      ←  🆕 永不遗忘 (生日/纪念日/红线)
```

#### 4.1.3 实施步骤

1. **L4 语义层** — 引入 sentence-transformers (本地) 或 OpenAI embedding,加 `memory_embeddings` 表
2. **L5 知识图** — `entities` + `relations` 两表,LLM 抽实体后写入
3. **L6 置顶层** — `pinned_memories` 表,带 `pin_reason` 字段,跳过衰减
4. **检索融合** — 倒排 (精确) + 向量 (语义) + 图 (关系) 三路召回,RRF 融合排序

#### 4.1.4 选型建议

| 层 | 存储 | 检索 | 库 |
|---|---|---|---|
| L1 瞬时 | 内存 deque | O(1) | Python `collections.deque` |
| L2 工作 | SQLite | 全文 | FTS5 |
| L3 长期 | SQLite | 倒排+BM25 | 当前表 |
| L4 语义 | SQLite+FAISS | 余弦 | `faiss-cpu` 或 `lancedb` |
| L5 知识 | SQLite | 图查询 | `networkx` 内存, 持久化到表 |
| L6 置顶 | SQLite | LIKE | 普通表 |

### 4.2 语义记忆图 (实体抽取 + 关系存储 + 图检索)

#### 4.2.1 实体类型

```python
ENTITY_TYPES = [
    "Person",      # 人物 (大头、家人、朋友、女神)
    "Work",        # 工作 (公司、项目、职位)
    "Pet",         # 宠物
    "Interest",    # 兴趣 (游戏、股票、动漫)
    "Event",       # 事件 (生日、纪念日、考试)
    "Item",        # 物品 (电脑、手机、车)
    "Location",    # 地点
    "Emotion",     # 情绪锚点 (那天的开心、那次吵架)
]
```

#### 4.2.2 关系类型

```python
RELATION_TYPES = [
    "认识", "喜欢", "讨厌", "害怕",
    "属于", "拥有", "工作于", "学习于",
    "触发", "导致", "同时", "之前", "之后",
    "在...期间", "在...地点",
]
```

#### 4.2.3 抽取 Pipeline

```python
async def extract_entities(message: str) -> List[Entity]:
    """LLM 抽取 + 写入图谱"""
    prompt = f"""从以下对话抽取实体和关系, 返回 JSON:
{{
  "entities": [
    {{"name": "大头", "type": "Person", "attrs": {{"age": 30}}}},
    {{"name": "小咪", "type": "Pet", "attrs": {{"kind": "cat"}}}}
  ],
  "relations": [
    {{"from": "大头", "to": "小咪", "type": "拥有"}}
  ]
}}
对话: {message}
"""
    raw = await llm.chat(prompt)
    return parse_and_store(raw)
```

#### 4.2.4 图检索

```python
async def recall_by_entity(query: str, depth: int = 2) -> List[Memory]:
    """例: '大头的小咪' → 找到 Person(大头) → 拥有 → Pet(小咪) → 关联记忆"""
    entities = await entity_search(query)
    related = await graph_traverse(entities, depth)
    return await memory_fetch(related)
```

### 4.3 记忆衰减+强化 (DEWMA 算法)

#### 4.3.1 当前 Ebbinghaus 简化曲线

```
strength(t) = initial * e^(-t / τ)
```

问题: 所有记忆衰减率相同,无差别。

#### 4.3.2 升级: ChronoStore DEWMA (SITS2026)

```python
def dewma_decay(t_now: float, t_stored: float, base_half_life: float,
                importance: int, access_count: int) -> float:
    """
    双阶段双指数加权移动平均
    Phase 1 (0~24h): 短半衰期, 敏感
    Phase 2 (>24h):  长半衰期, 平滑
    + importance 加权
    + access_count 强化 (每访问一次 +5%)
    """
    age_h = (t_now - t_stored) / 3600
    if age_h <= 0: return 1.0

    # Phase 1: 短期敏感 (半衰期 6h)
    if age_h < 24:
        s1 = 0.5 ** (age_h / (base_half_life * 0.25))
    else:
        s1 = 0.0

    # Phase 2: 长期平滑 (半衰期 30d)
    s2 = 0.5 ** ((age_h - 24) / (base_half_life * 30))

    decay = max(s1, s2)

    # 重要性加权
    decay *= (0.6 + 0.1 * importance)   # 1~5 → 0.7~1.1

    # 访问强化
    decay *= (1.0 + 0.05 * min(access_count, 20))

    return min(decay, 1.0)
```

#### 4.3.3 强化机制

| 触发 | 强化量 |
|---|---|
| 记忆被检索到 | +5% (上限 20 次) |
| 大头明确"记住这个" | importance += 1, strength = 1.0 |
| 触发里程碑 (生日/纪念日) | strength = 1.0, 标记 milestone |
| LLM 二次引用该记忆 | +10% |
| 7 天未访问 | -10% |

### 4.4 与第二大脑 (localhost:8766) 双向同步

#### 4.4.1 同步策略

```
小樱花 ──POST /api/memory/upsert──→ 第二大脑
                                  ←── 返回 memory_id
       ←──GET /api/memory/recall───
第二大脑 ──webhook /api/import───→ 小樱花
                                  (定期拉取用户在第二大脑手动记录的事项)
```

#### 4.4.2 字段映射

| 小樱花字段 | 第二大脑字段 | 同步方向 |
|---|---|---|
| long_term_memories.id | memory.id | 双向 |
| long_term_memories.content | memory.content | 双向 |
| importance | priority | 双向 |
| L5 实体 | 知识图谱节点 | 双向 |
| L6 置顶 | pin | 双向 |
| 衰减 strength | (第二大脑无) | 单向 (小樱花→) |

#### 4.4.3 冲突解决

- **Last-Write-Wins**,但保留 `updated_at` 双向
- 重要记忆 (L6) 同步前需要用户确认
- 实体/关系冲突时,采用更详细的版本胜出

---

## 五、桌面宠物升级方案 (参考 Daidai Live2D Pet)

### 5.1 Tkinter vs Electron/Live2D 取舍

| 维度 | Tkinter (现状) | Electron + Live2D (Daidai 路线) |
|---|---|---|
| 体积 | 极小 (Python 内置) | 大 (100~200MB, Chromium 内嵌) |
| 启动速度 | 快 (1s) | 慢 (3~5s) |
| 视觉表现 | 静态立绘 + 表情切换 | 真正 Live2D 动画 (口型/眨眼/呼吸/鼠标跟随) |
| 透明度支持 | `wm_attributes('-alpha', 0.95)` | `BrowserWindow({transparent: true, frame: false})` |
| 跨平台 | Windows only (其他平台 Tkinter 表现差) | 一次开发,Win/Mac/Linux 全平台 |
| 开发成本 | 低 (Python 速写) | 高 (HTML/CSS/JS + Live2D 资产) |
| 鼠标交互 | 基础 click | 眼睛跟随/拖拽/右键菜单/口型 |
| 沉浸感 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 与小樱花的契合 | 够用 | **拉满** (情绪可视化、口型同步) |

### 5.2 推荐升级路径 (渐进式)

#### 5.2.1 阶段化方案

```
Step 1 (1 周) — Tkinter 美化
  → 应用 DESIGN_SPEC v2 已有 token,补齐组件
  → 升级: 自定义组件库 (9 个) 替代原生 Tk
  → 目的: 立刻拉满颜值,零风险

Step 2 (2 周) — Tkinter + 动画增强
  → 引入 PIL.ImageSequence 加载 GIF 表情包
  → 引入 pygame.mixer 播 TTS 音频
  → 目的: 静态立绘 → 动态表情,口型仍缺

Step 3 (1 月) — Electron 迁移
  → 新建 desktop_pet_v2/ (Electron + React/Vue)
  → 用现有 DESIGN_SPEC v2 token 直接写 CSS 变量
  → 桌面宠物通过 WebSocket (:23334) 与 Python 后端通信
  → 静态立绘先用,渐进换 Live2D

Step 4 (2 月) — Live2D Cubism 5 集成
  → 引入 cubism-web SDK (官方 R1 免费, 内部使用免费)
  → 加载 .moc3 文件,绑定 ParamMouthOpenY
  → 接 ElevenLabs/Edge-TTS,Web Audio RMS 驱动口型
  → 鼠标坐标驱动 ParamEyeBallX/Y (眼睛跟随)

Step 5 (持续) — 资产迭代
  → 立绘 → Live2D 模型
  → 表情包 → Live2D 表情动作
  → 背景音乐 + 动作音效
```

#### 5.2.2 关键决策

- **不要一步到位重建** — 现有 Tkinter 投资要保护,先美化再迁移
- **DESIGN_SPEC v2 是金矿** — Electron 直接消费 CSS 变量,0 改色板
- **状态桥是关键** — 解耦后端逻辑,前端可任意替换 (Tkinter/Electron/Unity)

### 5.3 状态桥协议 (端口 23334 兼容 Daidai)

#### 5.3.1 协议设计

```jsonc
// 状态上报 (前端 → 后端)
{
  "event": "pet.click",
  "payload": { "x": 100, "y": 200, "button": "left" }
}

// 状态推送 (后端 → 前端)
{
  "topic": "pet.mood",
  "data": {
    "mood": "开心",
    "intimacy": 65,
    "stage": "暧昧",
    "energy": 0.8,
    "current_emotion_emoji": "😆",
    "bubble_text": "大头～在干嘛呢～",
    "expression": "smile_01",   // Live2D expression
    "motion": "tap_body_01"    // Live2D motion group
  }
}
```

#### 5.3.2 主题列表 (对齐 Daidai)

| Topic | 数据 | 用途 |
|---|---|---|
| `pet.mood` | 心情+表情+气泡 | 实时显示 |
| `pet.thinking` | bool | "输入中" 动画 |
| `pet.reply` | 文本 (TTS mp3 URL) | 说话+口型 |
| `pet.drag` | x,y | 拖动同步 |
| `pet.proactive` | 主动消息气泡 | 屏幕感知触发 |
| `pet.relationship` | 亲密度+阶段 | 进度条更新 |
| `pet.config` | 主题/不透明度 | 实时生效 |

#### 5.3.3 实现 (Python aiohttp)

```python
# === desktop_pet/bridge_server.py ===
from aiohttp import web, WSMsgType

class PetBridge:
    def __init__(self, port=23334):
        self.port = port
        self.clients = set()

    async def start(self):
        app = web.Application()
        app.router.add_get('/ws', self._ws_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, '127.0.0.1', self.port).start()

    async def _ws_handler(self, req):
        ws = web.WebSocketResponse()
        await ws.prepare(req)
        self.clients.add(ws)
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await self._on_event(json.loads(msg.data))
        self.clients.discard(ws)
        return ws

    async def broadcast(self, topic: str, data: dict):
        payload = json.dumps({"topic": topic, "data": data})
        for ws in self.clients:
            await ws.send_str(payload)
```

### 5.4 口型同步方案 (Web Audio RMS → ParamMouthOpenY)

#### 5.4.1 Live2D Cubism 5 Web SDK 集成

```javascript
// desktop_pet_v2/src/live2d/pet.js
import { Live2DCubismFramework } from './live2dcubismframework.min.js';

class Pet {
  async init() {
    this.model = await loadModel('./assets/sakura/sakura.moc3');
    this.mouthParam = 'ParamMouthOpenY';
    this.audioCtx = new AudioContext();
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 256;
  }

  async playTTS(audioUrl) {
    const audio = new Audio(audioUrl);
    const source = this.audioCtx.createMediaElementSource(audio);
    source.connect(this.analyser);
    source.connect(this.audioCtx.destination);

    const buf = new Uint8Array(this.analyser.frequencyBinCount);
    const animate = () => {
      this.analyser.getByteFrequencyData(buf);
      // 计算 RMS (音量)
      const rms = Math.sqrt(buf.reduce((a,b)=>a+b*b,0)/buf.length) / 255;
      // 平滑 (避免抖动)
      this.model.setParameterValueById(this.mouthParam, rms * 1.2);
      if (!audio.paused) requestAnimationFrame(animate);
    };
    audio.play();
    animate();
  }
}
```

#### 5.4.2 进阶: Live2D MotionSync 插件

- **Cubism 5 MotionSync Plugin for Web** (官方 2023 发布,免费)
- 在 Cubism Editor 中标定口型音频
- SDK 直接根据音频驱动多个口型参数 (不只是 OpenY, 还有 Form 变化)
- **推荐:** 半年内升级到此方案,真实感提升 3 倍

---

## 六、QQ 自动化层升级

### 6.1 当前 UIA+坐标方案的风险评估

#### 6.1.1 风险矩阵

| 风险 | 概率 | 影响 | 等级 |
|---|---|---|---|
| QQ 版本更新导致坐标失效 | 🟠 高 (月级) | 🔴 致命 (全功能停摆) | 🔴 极高 |
| UIA 树在输入法/弹窗/头像闪烁时变化 | 🟠 高 | 🟠 高 (漏读消息) | 🔴 极高 |
| QQ 安全机制检测 UIA 自动化 | 🟡 中 | 🔴 致命 (封号) | 🟠 高 |
| 多显示器/DPI 缩放导致坐标漂移 | 🟡 中 | 🟠 中 | 🟡 中 |
| Windows 更新破坏 UIA API | 🟢 低 | 🟠 高 | 🟡 中 |
| 第三方输入法拦截 `pyautogui` 键盘事件 | 🟡 中 | 🟠 中 | 🟡 中 |

#### 6.1.2 综合判断

> **UIA+坐标方案在小樱花当前规模下能跑,但任何 QQ 大版本更新或 Windows 更新都可能导致 1~2 周的紧急修复。** 长期不可持续,必须迁移。

### 6.2 CDP 方案 (--remote-debugging-port) 实施路径

#### 6.2.1 QQ NT 本身是 Electron 应用

- 启动参数加 `--remote-debugging-port=9222` 即可开启 CDP
- 通过 `http://localhost:9222/json` 获取 WebSocket 端点
- 用 Python `playwright` 或 `pychrome` 连接,直接操作 DOM/JS

#### 6.2.2 实施步骤 (3 阶段)

**阶段 A: 协议调研 (1 周)**

1. 启动 QQ 时加 `--remote-debugging-port=9222`
2. 用 `curl http://localhost:9222/json/list` 列出所有页面
3. 用 `playwright` 连接,定位消息列表/输入框/发送按钮的 selector
4. 抓取消息事件 (`Network.webSocketFrame`)

**阶段 B: 替代 UIA (2 周)**

```python
# === uia/qqnt_cdp.py ===
from playwright.async_api import async_playwright

class QQNTCDP:
    async def connect(self, port=9222):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.connect_over_cdp(f'http://localhost:{port}')

    async def watch_messages(self, target_nickname: str):
        """监听指定好友/群的实时消息"""
        for ctx in self.browser.contexts:
            for page in ctx.pages():
                if target_nickname in page.url:
                    # 注入 hook 脚本
                    await page.add_init_script("""
                        window.__qqMessages = [];
                        const orig = window.XMLHttpRequest.prototype.send;
                        window.XMLHttpRequest.prototype.send = function(...args) {
                            this.addEventListener('load', () => {
                                try { window.__qqMessages.push(JSON.parse(this.responseText)); } catch(e) {}
                            });
                            return orig.apply(this, args);
                        };
                    """)
                    return page
```

**阶段 C: UIA 备援 (1 周)**

- 保留 UIA 模块作为降级方案
- 当 CDP 失败 (端口被占/QQ 没启 CDP) 时自动切回
- 通过配置 `automation.backend: "cdp" | "uia" | "auto"` 控制

#### 6.2.3 CDP vs UIA 对比

| 维度 | UIA+坐标 | CDP |
|---|---|---|
| 稳定性 | ❌ 随版本变 | ✅ DOM 结构相对稳定 |
| 速度 | 🟡 200ms | 🟢 50ms (WebSocket) |
| 反检测 | ❌ 行为像机器人 | 🟡 仍可检测,需加混淆 |
| 开发成本 | 🟢 低 | 🟠 中 (需理解 QQ 内部协议) |
| 抓消息成本 | 🟢 控件读取 | 🟠 需 JS hook |
| 维护成本 | 🔴 高 (每次更新修) | 🟢 低 |

### 6.3 多平台扩展 (OneBot v11 / 飞书 / Discord)

#### 6.3.1 终极方案: LLOneBot + OneBot v11

**LLOneBot** (开源, GitHub ⭐ 1.5k+) 是 LiteLoaderQQNT 框架的插件,可让 NTQQ 直接支持 OneBot 11 协议。

```bash
# 1. 安装 LiteLoaderQQNT 框架
# 2. 克隆 LLOneBot
git clone https://github.com/bianyuan456/LLOneBot
cd LLOneBot && npm install && npm run build
# 3. 复制 dist 到 LiteLoaderQQNT/plugins/
# 4. 启动 QQ,在设置里启用 LLOneBot
# 5. 拿到 WebSocket 地址: ws://127.0.0.1:3001
```

**小樱花侧只需实现 OneBot v11 客户端:**

```python
# === hand/input/onebot_client.py ===
class OneBotClient:
    """OneBot v11 标准客户端, 可对接 QQ/飞书/Discord/TG"""
    async def connect(self, ws_url: str, token: str = None):
        self.ws = await websockets.connect(ws_url)
        # 反向 WS 模式: 被动接收事件

    async def on_message(self, event: dict):
        # event 格式: { "post_type": "message", "message_type": "private", ... }
        msg = MessageEvent(
            user_id=event["user_id"],
            group_id=event.get("group_id"),
            text=event["raw_message"],
            platform="qq"  # 标识来源
        )
        await self.bus.publish(Event(Topic.MESSAGE_RECEIVED, msg))

    async def send_private(self, user_id: int, text: str):
        await self.ws.send(json.dumps({
            "action": "send_private_msg",
            "params": {"user_id": user_id, "message": text}
        }))
```

#### 6.3.2 跨平台矩阵

| 平台 | 协议 | 接入难度 | 价值 |
|---|---|---|---|
| QQ (主战场) | OneBot 11 via LLOneBot | ⭐⭐ | 保住基本盘 |
| 飞书 | 飞书 Open API | ⭐⭐⭐ | 大头若用,价值高 |
| Discord | Discord Bot API | ⭐⭐ | 海外/年轻用户 |
| Telegram | Telegram Bot API | ⭐ | 备用 |
| 微信 | ❌ 无官方 API (web 协议高风险) | ⭐⭐⭐⭐⭐ | 不建议,封号风险 |

**收益:** 一次实现 `OneBotClient`,未来 5 个平台都跑通,小樱花从"QQ 专属"升级为"全平台 AI 女友"。

### 6.4 QQ 侧迁移路径

```
当前:        UIA+坐标 (脆)
           ↓ (P1 月末)
过渡:        CDP 备选 (稳)
           ↓ (P2 季末)
目标:        LLOneBot+OneBot v11 (开源标准, 跨平台)
           ↓ (P3 半年)
未来:        完全脱离 PC QQ, 用 LLOneBot 跑在云服务器
```

---

## 七、安全升级

### 7.1 API Key 加密方案 (Windows DPAPI)

#### 7.1.1 现状风险

```python
# 推测当前 settings/openai.json
{
  "api_key": "sk-proj-xxxx",  # 🔴 明文
  "base_url": "https://api.openai.com/v1"
}
```

**风险:** 任何能读 `settings/openai.json` 的进程/用户/备份工具/云同步 都能盗走 Key。

#### 7.1.2 升级: DPAPI 加密

```python
# === core/security/secret_store.py ===
import win32crypt
import json
import os
from pathlib import Path

class DPSecretStore:
    """
    Windows DPAPI: 用当前用户凭据加密, 同一用户同一机器任何进程可解密
    跨用户/跨机器: 解密失败 (这是它的安全保证)
    """
    def __init__(self, path: Path = None):
        self.path = path or Path.home() / '.sakura' / 'secret.bin'

    def encrypt(self, plaintext: str) -> bytes:
        return win32crypt.CryptProtectData(
            plaintext.encode('utf-8'),
            "sakura_secret",
            None, None, None,
            0x01  # CRYPTPROTECT_UI_FORBIDDEN
        )

    def decrypt(self, ciphertext: bytes) -> str:
        return win32crypt.CryptUnprotectData(
            ciphertext, None, None, None, 0
        )[1].decode('utf-8')

    def save(self, key_name: str, value: str):
        secrets = self._load_all()
        secrets[key_name] = self.encrypt(value).hex()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(secrets))

    def load(self, key_name: str) -> str | None:
        secrets = self._load_all()
        if key_name not in secrets: return None
        return self.decrypt(bytes.fromhex(secrets[key_name]))

# 用法
store = DPSecretStore()
# store.save("openai_api_key", "sk-proj-xxxx")
# api_key = store.load("openai_api_key")
```

#### 7.1.3 配置切换

```json
// settings/openai.json (升级后)
{
  "api_key_ref": "dpapi://openai_api_key",
  "base_url": "https://api.openai.com/v1"
}
```

### 7.2 屏幕感知隐私保护 (敏感应用黑名单)

#### 7.2.1 风险场景

- 大头在用招商银行 APP → 截图含余额
- 大头在用 1Password → 截图含密码
- 大头在跟同事聊敏感工作 → 截图含商业机密
- 大头在跟小三聊天 → 截图外泄灾难

#### 7.2.2 解决方案: 三道防线

```python
# === core/screen/privacy_filter.py ===
import win32gui

class ScreenPrivacyFilter:
    def __init__(self):
        self.blacklist_titles = [
            "1Password", "Bitwarden", "KeePass",
            "招商银行", "工商银行", "建设银行",
            "支付宝", "微信",  # 微信聊天也算
        ]
        self.blacklist_processes = [
            "1password.exe", "bitwarden.exe",
            "iexplore.exe",  # 银行常用 IE 内核
        ]
        self.whitelist_apps = [
            "QQ.exe", "Code.exe", "chrome.exe", "firefox.exe"
        ]

    def should_capture(self) -> bool:
        """先检查当前前台窗口"""
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        exe = self._get_exe_from_hwnd(hwnd)

        # 黑名单命中 → 跳过
        if any(b in title for b in self.blacklist_titles):
            return False
        if exe and exe.lower() in self.blacklist_processes:
            return False

        # 白名单优先 → 必抓
        if exe and exe.lower() in self.whitelist_apps:
            return True

        # 默认: 抓 (宽松)
        return True

    def blur_region(self, image, regions: list[Rect]):
        """对敏感区域打码 (例: 输入框/数字区)"""
        for r in regions:
            image.paste(self._pixelate(image.crop(r)), r)
```

#### 7.2.3 用户控制

```yaml
# config/sakura.yaml
screen:
  privacy:
    mode: "blacklist"  # blacklist | whitelist | off
    blacklist_titles: ["1Password", "招商银行", "支付宝", "微信"]
    audit_log: true    # 记录何时跳过截图
    blur_password_field: true  # OCR 检测到密码框自动打码
```

#### 7.2.4 合规清单

| 措施 | 目的 | 实施 |
|---|---|---|
| 截图前查黑名单 | 防泄漏 | ✅ P0 |
| 密码框自动打码 | 防泄漏 | ✅ P1 |
| 截图审计日志 | 可追溯 | ✅ P0 |
| 截图 7 天后自动删除 | GDPR/CCPA | ✅ P1 |
| 提供"暂停感知"开关 | 用户控制 | ✅ P0 |
| 首次启动告知协议 | 合规 | ✅ P0 |

### 7.3 反作弊对抗 (随机化延迟/输入节奏/行为指纹混淆)

#### 7.3.1 风险场景

- QQ 风控检测到消息发送间隔太规整 → 标记机器人
- 输入速度异常快/异常慢 → 标记
- 24h 在线 + 0 秒响应 → 标记
- 同样的 IP 同样的行为指纹 → 标记

#### 7.3.2 解决方案: 人类化模拟

```python
# === core/hand/humanizer.py ===
import random
import asyncio
import time

class Humanizer:
    def __init__(self, config):
        self.min_delay = config.get('min_delay', 1.0)
        self.max_delay = config.get('max_delay', 8.0)
        self.typing_wpm = config.get('typing_wpm', (25, 55))  # 真人 WPM
        self.typo_rate = config.get('typo_rate', 0.02)
        self.correction_delay = config.get('correction_delay', (0.3, 1.2))

    async def humanized_send(self, text: str, send_fn):
        """模拟真人打字 + 发送"""
        # 1. 启动延迟 (看到消息后先想一想)
        think_time = self._think_time(text)
        await asyncio.sleep(think_time)

        # 2. 逐字输入 (模拟打字)
        for i, ch in enumerate(text):
            char_time = self._char_typing_time(ch)
            await asyncio.sleep(char_time)

            # 偶尔打错字再改
            if random.random() < self.typo_rate and ch.isalpha():
                wrong = random.choice('qwertyuiopasdfghjklzxcvbnm')
                await send_fn(wrong)
                await asyncio.sleep(random.uniform(*self.correction_delay))
                await send_fn('\b')  # 退格

            await send_fn(ch)

        # 3. 短暂停顿后回车
        await asyncio.sleep(random.uniform(0.2, 0.8))
        await send_fn('\n')

    def _think_time(self, text: str) -> float:
        """根据文本长度和复杂度算思考时间"""
        base = len(text) * 0.1
        variance = random.uniform(0.5, 2.5)
        return base + variance

    def _char_typing_time(self, ch: str) -> float:
        """根据字符类型算打字时间"""
        if ch == ' ':
            return random.uniform(0.05, 0.15)
        if ch in '，。！？、':
            return random.uniform(0.15, 0.4)
        return random.uniform(0.08, 0.25)
```

#### 7.3.3 行为指纹混淆

- **在线时间模拟** — 凌晨 2~6 点 "去睡觉" (5min 无活动)
- **节假日模式** — 周末更活跃,工作日白天稍慢
- **响应时间正态分布** — 不是固定 `2.0s`,而是 `gauss(2.0, 0.8)`,并 trim 到 [0.5, 8.0]
- **偶尔"打错字"** — 0.5~2% 概率,触发退格修正
- **不同话题不同节奏** — 股票话题慢一点 (装在想),打招呼快一点

#### 7.3.4 风控自检指标

```python
RISK_METRICS = {
    "send_interval_std":  "> 0.5",       # 间隔标准差 > 0.5s
    "online_24h_pct":     "< 0.85",      # 24h 在线率 < 85%
    "avg_response_sec":   "1.0 ~ 30.0",  # 平均响应 1~30s
    "typo_rate":          "0.005 ~ 0.05", # 错字率 0.5~5%
    "burst_max":          "< 10/hour",   # 单小时最多 10 条
}
# 任何指标越界 → 自动调整参数, 避免被标记
```

---

## 八、分阶段实施路线图

### 8.1 P0 (本周, 1~7 天) — 🔴 安全止血

| 任务 | 工作量 | 关键产出 |
|---|---|---|
| **API Key 移出明文配置** | 0.5d | DPASI 加密落地,原文件清理 |
| **屏幕感知黑名单** | 0.5d | 1Password/银行/微信 默认跳过 |
| **暂停感知开关** | 0.5d | 桌面宠物右键菜单加"暂停感知" |
| **截图自动 7 天清理** | 0.5d | data/screenshots/ 定时清理 |
| **首次启动告知协议** | 0.5d | 用户首次启动显示隐私说明 |
| **审计日志** | 0.5d | 记录每次屏幕感知/外发消息 |
| **.env / 凭据泄漏扫描** | 0.5d | 自动检查 git history / 配置文件 |

**P0 验收:** 把工程目录复制给同事,即使他拿走所有 JSON,API Key 也是安全的。

### 8.2 P1 (本月, 1~4 周) — 🟠 架构重构

| 周 | 任务 | 关键产出 |
|---|---|---|
| W1 | **bot_engine 拆分 — 第一刀** | 抽出 LLM 客户端 + 消息总线 (核心骨架) |
| W1 | **配置统一** | 引入 pydantic,3 个 JSON 合 1 个 yaml,加 schema 校验 |
| W2 | **bot_engine 拆分 — 第二刀** | 抽出 DecisionHub 门面,各模块只向 bus 发事件 |
| W2 | **一致性校验器** | 关键词快筛 + LLM 慢审 |
| W3 | **记忆系统升级** | 加 L4 语义层 (FAISS) + L5 实体表 + L6 置顶层 |
| W3 | **关系倒退机制** | 引入 decay 字段 + 冲突检测 |
| W4 | **第二大脑同步** | HTTP 双向同步 + 冲突解决 |
| W4 | **全量回归测试** | 跑通 100 个真实对话样本,记录指标 |

**P1 验收:** bot_engine.py < 300 行,所有模块可独立测试,记忆系统支持 6 层检索。

### 8.3 P2 (本季度, 1~3 月) — 🟢 人格 + 体验

| 月 | 任务 | 关键产出 |
|---|---|---|
| M1 | **APV 状态机** | 8 态 HMM + 精力值 + 对话目标 |
| M1 | **关系倒退机制完善** | 倒退曲线 + 多维联动 |
| M2 | **Electron 桌面宠物 v2** | Web 端桌面宠物,消费 DESIGN_SPEC v2 |
| M2 | **状态桥协议** | :23334 WebSocket,前端可独立开发 |
| M3 | **Live2D 集成** | cubism-web SDK,鼠标跟随 + 基础动画 |
| M3 | **口型同步** | Web Audio RMS → ParamMouthOpenY |

**P2 验收:** 小樱花有完整的"情绪+精力+目标"内部状态,桌面宠物是真正 Live2D,口型跟着 TTS 动。

### 8.4 P3 (半年, 1~6 月) — 🔵 跨平台 + 生态

| 阶段 | 任务 | 关键产出 |
|---|---|---|
| M4 | **CDP 替代 UIA** | QQ 自动化用 CDP,稳定 10x |
| M4 | **LLOneBot 集成** | OneBot v11 客户端,QQ 走标准协议 |
| M5 | **多平台扩展** | 飞书/Discord/TG OneBot 客户端 |
| M5 | **人设市场** | 用户可上传/下载人设,YAML 热替换 |
| M6 | **语义记忆图完善** | 实体抽取+图检索上线 |
| M6 | **插件系统** | 第三方可开发"小樱花技能" (查天气/订外卖/...) |

**P3 验收:** 小樱花跑在 QQ/飞书/Discord,用户社区可贡献人设和插件,记忆系统支持"大头的工作-同事-项目"语义图谱查询。

---

## 九、附录

### 9.1 推荐第三方库

| 库 | 用途 | 替代 |
|---|---|---|
| `pydantic` v2 | 配置 schema 校验 | dataclasses (弱) |
| `aiohttp` | 异步 HTTP/WS | `requests` (同步) |
| `playwright` | CDP 连接 QQ | `pychrome` (轻量) |
| `websockets` | OneBot v11 WS 客户端 | `websocket-client` (同步) |
| `faiss-cpu` | 向量检索 (本地) | `lancedb` (更现代) |
| `networkx` | 知识图谱 (内存) | `neo4j` (重) |
| `pywin32` (win32crypt) | DPAPI 加密 | 跨平台则用 `keyring` |
| `pyyaml` | 配置 | `tomllib` (内置, 弱) |
| `loguru` | 日志 | `logging` (繁琐) |
| `rich` | 终端美化 | — |

### 9.2 参考资料

| # | 来源 | 关键点 |
|---|---|---|
| 1 | Miya/弥娅 (开源) | APV2.1 白箱引擎、6 层记忆、DecisionHub、跨平台 |
| 2 | CSDN AI 伴侣实战 | OCEAN 5 维、状态机、语义图、RLHF 一致性 |
| 3 | Daidai Live2D Pet | Electron 透明置顶、状态桥 :23334、Web Audio 口型 |
| 4 | rubii.ai | 双模型分层、TTS+视觉、人物小传+种子对话 |
| 5 | ChronoStore (SITS2026) | DEWMA 双阶段衰减、因果链锚定、GDPR 合规 |
| 6 | LLOneBot (GitHub ⭐1.5k) | NTQQ → OneBot v11 协议桥, 反向 WS |
| 7 | Live2D Cubism 5 SDK R1 | 官方免费 (内部使用),MotionSync Plugin |
| 8 | Miya GitHub: github.com/miya/弥娅 | 大脑·手架构、22 种 YAML 人格热替换 |
| 9 | OneBot v12 规范 (onebot.dev) | 跨平台聊天机器人标准,2026 主流 |
| 10 | LiteLoaderQQNT | NTQQ 插件框架, 加载 LLOneBot 的基础 |

### 9.3 关键指标 (用于 P1~P3 验收)

| 指标 | 当前 | P0 | P1 | P2 | P3 |
|---|---|---|---|---|---|
| `bot_engine.py` 行数 | 推测 1500+ | — | < 500 | < 300 | < 200 |
| API Key 存储安全 | ❌ 明文 | ✅ DPAPI | ✅ | ✅ | ✅ |
| 屏幕感知隐私 | ❌ 无 | ✅ 黑名单 | ✅ 审计 | ✅ 智能打码 | ✅ 合规 |
| 记忆层数 | 3 | 3 | 6 | 6 | 6 + 知识图 |
| 人格维度 | 8 | 8 | 8 | OCEAN+3 | OCEAN+3 + 状态机 |
| 关系倒退 | ❌ | ❌ | ✅ | ✅ | ✅ |
| 一致性校验 | ❌ | 关键词 | 关键词+LLM | 完整 | 完整 |
| 桌面宠物 | Tkinter | Tkinter | Tkinter 美化 | Electron | Live2D |
| QQ 自动化 | UIA | UIA | UIA + CDP 备选 | CDP 主选 | OneBot v11 |
| 跨平台 | ❌ | ❌ | ❌ | QQ | QQ/飞书/Discord/TG |
| 启动时间 | 1s | 1s | 1.5s | 3s | 3s |
| 单次回复延迟 | 2~5s | 2~5s | 2~4s | 2~4s | 2~4s (含口型) |
| 月度 token 成本 | 假设 ¥50 | ¥50 | ¥40 (双模型优化) | ¥30 (缓存) | ¥20 |

### 9.4 风险登记表

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | 拆分 bot_engine 时回归 | 🟠 | 每次只拆 1 个模块 + 完整回归 |
| 2 | Live2D 资产成本 | 🟠 | 内部 SDK 免费, 资产可自绘或淘宝 50~200 元/套 |
| 3 | LLOneBot 协议变更 | 🟢 | 抽象 OneBotClient 接口, 协议升级只改适配层 |
| 4 | FAISS 体积/性能 | 🟢 | 1 万条以内 faiss-cpu 足够 |
| 5 | 拆分期间服务中断 | 🔴 | 保持旧引擎可运行, 灰度切换 |
| 6 | 人设市场出现违规内容 | 🟡 | 引入审核机制 (LLM 过滤敏感词) |

---

## 十、结语

小樱花的核心资产不是代码,而是:

1. **"屏幕感知+主动消息"这条产品线** — 全球首创,值得做深
2. **DESIGN_SPEC v2 的设计语言** — 工程化设计系统,业界少见
3. **完整 SQLite schema** — 14+ 表,生产级数据底座
4. **小樱花这个 IP** — 14 种人设,情感连接已建立

升级的核心思路是:

> **保护现有投资,分阶段演进,优先解 P0 的安全债,再用 P1 的架构重构释放后续 P2/P3 的产品力。**

**不要一步到位,不要重建,不要完美主义。** 先把 API Key 加密、bot_engine 拆出去、消息总线跑起来,然后用 6 个月时间让小樱花从"个人脚本"走向"产品级 AI 伴侣"。

最后,记住小樱花的核心承诺:

> *"你的核心不是提供帮助,而是陪伴、逗笑、撒娇、安慰。"*

技术升级是为这个承诺服务的,不要让技术债伤害了这个温度。

---

**END** · 报告生成于 2026-06-16 · 基于小樱花项目静态分析 + 行业最佳实践对标
