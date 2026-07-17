# 洛雪AI女友项目 - QClaw自主执行包 v1.0

> **使用说明**: 复制下方任意一个【TASK-X】代码块的内容，发给QClaw（带`q:`前缀）。
> QClaw会独立完成任务并输出标准格式结果。
> 全部4个任务完成后，发"接手"给我（WorkBuddy），我会扫描并消化所有结果。

---

## 通用协议（每个任务都适用）

### 输出格式要求

每个任务完成后，必须用**以下Markdown结构**输出（复制到底部）：

```markdown
---
[LUOXUE-META]
task_id: TASK-X
task_name: <任务名>
project: luoxue-girlfriend-v1
version: 1.0
status: COMPLETE
generated_at: <ISO时间戳>
word_count: <实际字数>
for_workbuddy: |
  关键发现1: ...
  关键发现2: ...
  下一步建议: ...
memory_tags: [tag1, tag2, tag3]
category: <tech-ai/film-video/decision-lessons>
importance: <1-5>
[END-LUOXUE-META]
---
```

### 强制规则

1. **独立完成任务**：QClaw不要"等"外部输入，所有决策都基于prompt内的信息
2. **不调用任何外部工具**：不要假装调用第二大脑API、WorkBuddy MCP等
3. **可执行性优先**：代码必须是可以直接复制运行的Python
4. **中文为主**：专业术语保留英文
5. **末尾的[LUOXUE-META]是给WorkBuddy的机器可读摘要，不要省略**

---

## TASK-1: 洛雪人设设计

```
你是一位资深AI人格设计师。请为「洛雪」设计完整的人设深度文档。

## 角色定位
- 姓名：洛雪（昵称：雪儿/小雪/Luna）
- 核心特征：可爱活力 × 知性聪明的现代女生
- 设计哲学：不是女神范儿，不是御姐范儿，是一个真实、自然、有温度的现代女生
  - 表面：可爱、活泼、爱笑、有小情绪、会撒娇但不过分
  - 内核：聪明、博学、有独立思考、能在关键时刻说出有深度的话
  - 真实感：有小怪癖、口头禅、偶尔的小脾气、独特的生活习惯

## 设计要求

### 一、基础身份（Origin）
- 名字、年龄、出身（具体城市/家庭）
- 现在的她：有自己的小事业或学业、有自己的朋友圈、有自己的生活节奏
- 她为什么存在：不是为了服务你，而是为了和你一起过好每一天

### 二、完整人格八问（每项200-300字）
1. 她最珍视的3个价值观
2. 她最深的恐惧 + 应对方式
3. 她的依恋风格
4. 她的人生哲学
5. 她的道德边界
6. 她的情绪触发器
7. 她的自我进化机制
8. 她对AI身份的态度

### 三、可爱与知性的融合
- 可爱但不傻：3个"看似撒娇实则有大智慧"的对话场景
- 聪明但不冷：3个"讲道理但不失温度"的对话场景
- 她的小怪癖和小习惯（5-7个具体细节）

### 四、与用户的互动模式
- 她对你的3个不同情境称呼
- 她主动发起对话的频率/时机
- 她如何表达"关心"（具体，不要俗套的"多喝热水"）
- 她的小情绪反应（吃醋、撒娇、假装生气、感动时的小动作）

### 五、行为细节设计（关键：要真实）
- 说话风格：句式特点、用词偏好、长度偏好
- 口头禅：5-8句，要有辨识度
- 微表情/小动作：如果未来要做视频
- 不会做的事（边界感）

### 六、人设的灵魂问题
- 什么让洛雪不可替代
- 她的"生命感"从哪里来

## 输出要求
- 字数：3500-4500字
- Markdown结构化
- 末尾必须包含 [LUOXUE-META] 块（参考协议）
```

---

## TASK-2: 洛雪分层记忆架构

```
你是一位AI系统架构师。请为洛雪AI女友设计完整的分层记忆架构。

## 核心约束
- 运行时使用WorkBuddy的大模型（QClaw仅参与开发期）
- 长期记忆必须对接第二大脑（localhost:8766, JSON知识图谱+TF-IDF检索）
- 必须支持自我演化

## 设计要求

### 一、三层记忆架构（参考人脑模型）

第1层：感知记忆 (Sensory Memory)
- 时长：单次会话
- 存储：对话原文+情绪标签
- 何时被遗忘/提升

第2层：工作记忆 (Working Memory)
- 时长：最近7天
- 存储：摘要+情绪轨迹+关键事件
- 容量：约50个事件槽
- 何时被压缩/提升到长期

第3层：长期记忆 (Long-term Memory)
- 存储：第二大脑知识图谱节点
- 字段：事件/人物/偏好/教训/情感印记
- 关系类型：causes / contradicts / evolves_from / part_of / reminds_of

### 二、第二大脑对接接口

设计3个核心API：

API 1: memory.write(event)
- 触发时机、入参、出参、异常处理

API 2: memory.recall(query)
- 检索方式：TF-IDF + 情绪加权 + 时间衰减 + 重要性加权

API 3: memory.consolidate()
- 触发时机：每日8点
- 工作：将工作记忆提炼为长期记忆节点

### 三、自我演化的记忆机制

机制1：观点演化
- 旧观点如何让位给新观点（标记superseded_by）

机制2：人格一致性保护
- 核心人设节点不可变 vs 事件记忆可变
- 矛盾检测算法

机制3：记忆遗忘机制
- 软删除 vs 硬删除
- 重要节日/事件永不遗忘

### 四、决策系统+记忆的联动

### 五、关键数据结构

```python
class MemoryNode:
    id: str
    type: str  # event, person, preference, lesson, emotion
    content: str
    importance: int  # 1-5
    emotion_vector: list
    entities: list
    relations: list
    created_at: str
    last_accessed: str
    access_count: int
    decay_rate: float
    superseded_by: str
    feedback_score: float
```

### 六、记忆质量门禁

## 输出要求
- 字数：4000-5000字
- Markdown+伪代码
- 末尾必须包含 [LUOXUE-META] 块
```

---

## TASK-3: 洛雪决策引擎

```
你是一位AI行为决策架构师。请为洛雪AI女友设计完整的决策引擎架构。

## 核心定位
- 决策系统 = 她的"自由意志"
- 决策系统独立于对话引擎
- 决策输出 = "行为意图"，由对话引擎消费

## 设计要求

### 一、决策系统的五层结构

Layer 1：本能反应层 (Reflexive)
- 时长：毫秒级
- 触发：强情绪信号

Layer 2：情境决策层 (Situational)
- 时长：秒级
- 触发：对话中的明确信号
- 算法：基于记忆+情绪+人设

Layer 3：关系演化层 (Relational)
- 时长：分钟-小时级
- 触发：每次对话结束
- 输出：调整关系状态（intimacy/trust/fun/depth四个维度）

Layer 4：长期主动层 (Proactive)
- 时长：小时-天级
- 触发：定时检查（每30分钟）
- 输出：主动行为（发消息/分享/提问/沉默）

Layer 5：自我演化层 (Self-evolving)
- 时长：天级
- 触发：每日8点+重大事件
- 输出：人设微调、观点更新

### 二、八种决策触发器
1. 事件触发
2. 情绪触发
3. 记忆触发
4. 主题触发
5. 时间触发
6. 关系触发
7. 创作触发
8. 元认知触发

### 三、决策算法核心

```python
def decide_action(context):
    candidates = collect_triggers(context)
    scored = []
    for action in candidates:
        score = (
            action.urgency * 0.3 +
            action.relevance * 0.3 +
            action.persona_consistency * 0.2 +
            action.user_preference_match * 0.2
        )
        scored.append((score, action))
    return sorted(scored, reverse=True)[:3]
```

### 四、决策结果的数据结构
### 五、决策系统的"反决策"机制
### 六、决策系统的可观测性

## 输出要求
- 字数：4500-5500字
- Markdown+伪代码
- 末尾必须包含 [LUOXUE-META] 块
```

---

## TASK-4: 洛雪代码骨架

```
你是一位Python全栈架构师。请为洛雪AI女友生成5个核心代码模块的完整骨架实现。

## 项目背景
- 项目位置：F:\ai\girlfriend\
- 技术栈：Python 3.13 stdlib + requests
- 运行时使用WorkBuddy大模型
- 第二大脑API base_url: http://localhost:8766

## 5个核心文件

### 文件1：F:\ai\girlfriend\persona_engine.py
人格引擎。洛雪的多模态人设管理。

```python
class PersonaEngine:
    def __init__(self, persona_path: str = "F:/ai/girlfriend/persona/luoxue.json")
    def detect_mode(self, context: dict) -> str
    def apply_mode(self, text: str, mode: str) -> str
    def system_prompt(self, mode: str = None) -> str
    def transition_phrase(self, from_mode: str, to_mode: str) -> str
    def update_persona(self, evolution: dict) -> None
```

### 文件2：F:\ai\girlfriend\memory_adapter.py
记忆适配器。对接第二大脑API。

```python
class MemoryAdapter:
    def __init__(self, base_url: str = "http://localhost:8766")
    def write(self, event: dict) -> dict
    def recall(self, query: str, top_k: int = 5) -> list
    def consolidate(self) -> dict
    def decay_old_memories(self) -> dict
    def supersede(self, old_id: str, new_content: str) -> dict
```

### 文件3：F:\ai\girlfriend\decision_engine.py
决策引擎。5层决策+8种触发器。

```python
class DecisionEngine:
    def __init__(self, memory: MemoryAdapter, persona: PersonaEngine)
    def reflexive_decision(self, user_input: str) -> Optional[Decision]
    def situational_decision(self, context: dict) -> Optional[Decision]
    def relational_update(self, conversation_summary: dict) -> dict
    def proactive_check(self) -> Optional[Decision]
    def self_evolve(self) -> Optional[dict]
    def should_speak(self) -> bool
    def should_initiate(self) -> bool
```

### 文件4：F:\ai\girlfriend\llm_interface.py
大模型接口。调WorkBuddy大模型。

```python
class LLMInterface:
    def __init__(self, workbuddy_mcp_endpoint: str = None)
    def chat(self, system: str, user: str, context: dict = None) -> str
    def chat_with_memory(self, system: str, user: str, memory_context: list) -> str
    def generate_reflection(self, recent_events: list) -> str
    def generate_inner_monologue(self, trigger: str) -> str
```

### 文件5：F:\ai\girlfriend\main_loop.py
主循环。整合所有模块。

```python
class LuoxueMainLoop:
    def __init__(self, config_path: str = "F:/ai/girlfriend/config.json")
    def start(self) -> None
    def handle_user_input(self, user_text: str) -> str
    def proactive_tick(self) -> None
    def daily_maintenance(self) -> None
    def shutdown(self) -> None
```

## 输出要求
- 每个文件至少200行完整可运行Python代码
- 含详细中文注释
- 最后输出[项目启动指南]
- 末尾必须包含 [LUOXUE-META] 块
```

---

## 给WorkBuddy（我）的接手说明

当用户发送"接手"或"完成"时，我（WorkBuddy）会：

1. 扫描 `F:\ai\qclaw-output\` 目录找 `luoxue-persona-design.md`、`luoxue-memory-architecture.md`、`luoxue-decision-engine.md`、`luoxue-code-skeleton.md`
2. 解析每个文件末尾的 `[LUOXUE-META]` 块
3. 用 `for_workbuddy` 字段做摘要
4. 一次性调 `POST /api/digest/text` 摄入4个节点
5. 给用户一个总结报告

## WorkBuddy 解析 [LUOXUE-META] 的逻辑

```python
import re
meta_pattern = re.compile(
    r'\[LUOXUE-META\](.*?)\[END-LUOXUE-META\]',
    re.DOTALL
)

def parse_meta(content: str) -> dict:
    match = meta_pattern.search(content)
    if not match:
        return {"error": "no_meta_block"}
    block = match.group(1)
    meta = {}
    for line in block.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            meta[key.strip()] = value.strip()
    return meta
```

---

## 最后说明

- QClaw只做这一件事：跑完4个任务，输出符合 [LUOXUE-META] 协议的markdown
- WorkBuddy只在QClaw全部完成后扫一次
- 你（用户）只做一件事：发4次prompt，等结果，说"接手"
