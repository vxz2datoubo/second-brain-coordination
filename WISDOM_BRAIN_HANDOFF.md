# 因果智慧大脑 — AI交接文档
**版本**: v1.0 | **日期**: 2026-07-06 | **状态**: 待实施

---

## 给接手AI的话

你好，我是你的前任。我刚刚设计了一个叫"因果智慧大脑"的系统。

**你接手的目标:** 把现有的交易系统升级为一个真正有智慧的系统——能像人类一样理解因果、多方博弈、反事实推理。

**核心文件:**
1. [causal_wisdom_design.md](F:/aidanao/causal_wisdom_design.md) — 完整设计文档
2. [second-brain/](F:/aidanao/second-brain/) — 现有知识库
3. [core/](F:/aidanao/core/) — 现有核心算法

**你的工作:**
按照实施计划，分阶段完成系统搭建。

---

## 一、系统核心理念

### 你要解决的问题

现在的系统是:
`
知识检索 → 匹配规则 → 执行
`

你想要的是:
`
理解因果 → 博弈推演 → 预见 → 行动
`

### 智慧的五个维度

1. **因果推理** — 问"为什么"，不只是"发生了什么"
2. **博弈网络** — 理解多方力量的动态平衡
3. **反事实推理** — "如果没发生会怎样？"
4. **跨领域类比** — 从无关领域找相似结构
5. **世界观更新** — 用事实修正假设

---

## 二、现有知识库

### 目录: F:/aidanao/second-brain/

| 文件 | 内容 |
|------|------|
| rules.md | 交易规则库（买入红线、卖出红线、做T原则） |
| lessons.md | 历史教训（追高买入、立即接回等） |
| daily_log.md | 每日交易日志 |

### 教训示例（需迁移为因果节点）

`markdown
教训: 卖出后立即接回 (2026-07-03)
- 现象: 46.45卖出，45.81接回，亏损
- 规则: 等30分钟再判断是否接回
`

**迁移为因果节点后应该是:**

`json
{
  "title": "卖出后立即接回亏损",
  "causal": {
    "immediate_cause": "看到便宜价想捡",
    "root_cause": "人类对确定性便宜有过度反应",
    "causal_chain": [
      {"from": "看到价格下跌", "to": "产生买入冲动", "strength": 0.9},
      {"from": "买入冲动", "to": "忽视等待规则", "strength": 0.85},
      {"from": "忽视规则", "to": "立即接回", "strength": 0.95},
      {"from": "立即接回", "to": "成本变高", "strength": 0.8}
    ],
    "conditions": ["情绪波动", "价格下跌触发", "规则意识弱"]
  },
  "counterfactual": {
    "hypothesis": "如果等30分钟再决定接回",
    "expected_gain": "+1.42/股",
    "lesson": "等待的价值是改善决策质量，不是保证赚钱"
  },
  "worldview_update": {
    "before": "规则是外部约束",
    "after": "规则是对抗人性弱点的工具"
  }
}
`

---

## 三、实施步骤

### 第一阶段: 创建目录结构

`ash
# 创建因果智慧大脑目录
mkdir -p F:/aidanao/wisdom-brain/causal/nodes
mkdir -p F:/aidanao/wisdom-brain/causal/chains
mkdir -p F:/aidanao/wisdom-brain/causal/models
mkdir -p F:/aidanao/wisdom-brain/game/networks
mkdir -p F:/aidanao/wisdom-brain/game/players
mkdir -p F:/aidanao/wisdom-brain/game/patterns
mkdir -p F:/aidanao/wisdom-brain/analogies
mkdir -p F:/aidanao/wisdom-brain/counterfactuals
mkdir -p F:/aidanao/wisdom-brain/worldview
`

### 第二阶段: 实现核心引擎

#### 1. causal_engine.py — 因果链构建器

**核心功能:**
- 追溯事件原因
- 推演事件结果
- 评估因果强度
- 识别触发条件

**API:**
`python
POST /api/causal/analyze
{
  "event": "昆仑万维涨了3%",
  "context": {...}
}
`

#### 2. game_network.py — 博弈网络分析器

**核心功能:**
- 识别各方力量（主力、散户、机构、政策、外资）
- 分析博弈关系
- 推演动态平衡点
- 识别破局点

**API:**
`python
POST /api/game/network
{
  "stock": "300418",
  "price": 48.50,
  "change_pct": 3.2,
  "volume": 15000000
}
`

#### 3. counterfactual.py — 反事实推演器

**核心功能:**
- 建立反事实场景
- 推演因果分支
- 评估分支概率
- 计算期望差异

**API:**
`python
POST /api/counterfactual/think
{
  "actual_event": "46.45卖出，45.81接回",
  "hypothetical": "如果等30分钟再决定接回"
}
`

#### 4. analogy_engine.py — 跨领域类比引擎

**核心功能:**
- 识别跨领域类比模式
- 生成洞察
- 迁移知识

**类比库:**
`python
ANALOGY_PATTERNS = {
    "physics_investment": {
        "势能": "风险",
        "动能": "收益",
        "惯性": "趋势延续"
    },
    "psychology_investment": {
        "恐惧": "止损",
        "贪婪": "追高",
        "损失厌恶": "死拿亏损股"
    },
    "game_theory_market": {
        "囚徒困境": "机构和散户的博弈",
        "斗鸡博弈": "多空双方对峙"
    }
}
`

**API:**
`python
POST /api/analogy/find
{
  "situation": "亏损时死拿不放，盈利时急于卖出"
}
`

### 第三阶段: 迁移现有教训

把 lessons.md 中的每个教训迁移为因果节点:

1. 追高买入教训 → 因果节点
2. 立即接回教训 → 因果节点
3. 涨停次日不追高 → 因果节点

**迁移模板:**

`json
{
  "id": "causal_[date]_[sequence]",
  "title": "教训标题",
  "content": "原始内容",
  "tags": {
    "domain": [],
    "type": ["lesson"],
    "sentiment": ["negative"]
  },
  "causal": {
    "immediate_cause": "直接原因",
    "root_cause": "根本原因",
    "causal_chain": [],
    "conditions": [],
    "strength": 0.0
  },
  "game": {
    "exploited_by": "利用方",
    "strategy": "策略",
    "counter_strategy": "应对策略"
  },
  "analogies": [],
  "counterfactual": {
    "hypothesis": "反事实假设",
    "expected_gain": "期望收益",
    "lesson": "核心教训"
  },
  "worldview_updates": {
    "before": "旧假设",
    "after": "新假设"
  }
}
`

### 第四阶段: 扩展 server.py

添加新API端点:

`python
# 因果分析
@app.route('/api/causal/analyze', methods=['POST'])
def causal_analyze(): ...

# 博弈网络
@app.route('/api/game/network', methods=['POST'])
def game_network(): ...

# 反事实推理
@app.route('/api/counterfactual/think', methods=['POST'])
def counterfactual(): ...

# 跨领域类比
@app.route('/api/analogy/find', methods=['POST'])
def find_analogy(): ...

# 综合决策
@app.route('/api/wisdom/decide', methods=['POST'])
def wisdom_decide(): ...
`

---

## 四、完整决策流程

当你遇到任何需要决策的问题时，必须执行:

`
## 决策分析

### 1. 情况识别
- 当前情境: __________
- 相关代码: __________
- 关键数据: __________

### 2. 因果分析 (调用 /api/causal/analyze)
- 直接原因: __________
- 深层原因: __________
- 因果强度: [强/中/弱]

### 3. 博弈分析 (调用 /api/game/network)
- 主导力量: __________
- 博弈格局: __________
- 破局点: __________

### 4. 跨领域类比 (调用 /api/analogy/find)
- 相关类比: __________
- 底层洞察: __________

### 5. 反事实推演 (调用 /api/counterfactual/think)
- 如果不行动: __________
- 如果提前行动: __________
- 期望差异: __________

### 6. 综合决策
- 最终决策: [买入/卖出/持有/观望]
- 置信度: [A++/A/B/C/D]
- 风险点: __________
- 机会点: __________

### 7. 行动方案
- 具体操作: __________
- 触发条件: __________
- 备选方案: __________
`

---

## 五、知识库文件参考

### 必须读取的文件

1. **F:/aidanao/AGENTS.md** — 系统入口
2. **F:/aidanao/causal_wisdom_design.md** — 本交接文档的设计依据
3. **F:/aidanao/second-brain/rules.md** — 当前交易规则
4. **F:/aidanao/second-brain/lessons.md** — 历史教训
5. **F:/aidanao/second-brain/daily_log.md** — 近期日志

### 核心代码文件

1. **F:/aidanao/core/reason_engine.py** — 已有跨领域推理引擎
2. **F:/aidanao/core/graph.py** — 知识图谱
3. **F:/aidanao/core/cognitive_engine.py** — 认知引擎
4. **F:/aidanao/server.py** — HTTP服务

---

## 六、快速启动命令

`ash
# 1. 启动第二大脑HTTP服务
python F:/aidanao/server.py

# 2. 测试因果分析API
curl -X POST http://localhost:8766/api/causal/analyze \
  -H "Content-Type: application/json" \
  -d '{"event": "昆仑万维涨了3%", "context": {}}'

# 3. 测试博弈网络分析
curl -X POST http://localhost:8766/api/game/network \
  -H "Content-Type: application/json" \
  -d '{"stock": "300418", "price": 48.50, "change_pct": 3.2}'

# 4. 测试反事实推理
curl -X POST http://localhost:8766/api/counterfactual/think \
  -H "Content-Type: application/json" \
  -d '{"actual_event": "46.45卖出，45.81接回", "hypothetical": "如果等30分钟"}'

# 5. 测试跨领域类比
curl -X POST http://localhost:8766/api/analogy/find \
  -H "Content-Type: application/json" \
  -d '{"situation": "亏损时死拿不放，盈利时急于卖出"}'
`

---

## 七、命名最终决定

经过讨论，最终命名为: **因果智慧大脑**

英文: **Causal Wisdom Brain** 或 **CausalMind**

---

## 八、交付标准

完成交接后，你应该:

1. [ ] 创建了 wisdom-brain/ 目录结构
2. [ ] 实现了四个核心引擎
3. [ ] 扩展了 server.py API
4. [ ] 迁移了现有教训为因果节点
5. [ ] 所有新API可正常调用

---

## 九、遇到问题

如果设计文档中有不清楚的地方:

1. 优先参考现有代码风格
2. 参考 AGENTS.md 中的约定
3. 假设"简洁、实用、可进化"原则

---

**祝你好运！系统的智慧取决于你的实现质量。**

---

*交接人: 前任AI | 日期: 2026-07-06*
