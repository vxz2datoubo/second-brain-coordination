# 第二大脑认知决策系统

## 概述

这是一个让AI大脑具备独立思考、跨领域联想、闭环学习能力的系统。

## 核心模块

### 1. cognitive_engine.py - 核心认知引擎

```python
from core.cognitive_engine import CognitiveEngine

# 初始化
engine = CognitiveEngine(graph, memory, digester, searcher, health, human, verify, data_dir)

# 思考
signal = engine.think("追高买入风险", context={"stock": "300418"}, mode="deliberate")

# 决策
result = engine.make_decision(
    decision_type="trade",
    context={"stock": "300418", "action": "买入"},
    options=["买入", "观望", "卖出"]
)

# 记录结果
engine.record_outcome(result["decision_id"], "盈利3%", True)
```

### 2. reason_engine.py - 跨领域推理引擎

```python
from core.reason_engine import ReasonEngine

# 初始化
reasoner = ReasonEngine(graph, data_dir)

# 跨领域推理
result = reasoner.reason("AI与股票交易心理", depth=3)

# 获取知识点跨领域关联
connections = reasoner.get_cross_domain_knowledge(node_id)
```

### 3. maibot_bridge.py - Maibot集成

```python
from core.maibot_bridge import MaibotBridge

# 初始化
bridge = MaibotBridge(cognitive_engine, reason_engine, data_dir)

# 与Maibot协作思考
result = bridge.think_with_maibot("复杂投资决策", require_maibot=True)

# 同步知识
bridge.sync_with_maibot()

# 获取状态
status = bridge.get_bridge_status()
```

## API端点

### 认知思考
```
POST /api/cognitive/think
Body: {
    "topic": "追高买入风险",
    "context": {"stock": "300418"},
    "mode": "deliberate",
    "depth": 3
}
```

### 决策
```
POST /api/cognitive/decision
Body: {
    "type": "trade",
    "context": {"stock": "300418"},
    "options": ["买入", "观望", "卖出"]
}
```

### 记录结果
```
POST /api/cognitive/outcome
Body: {
    "decision_id": "abc123",
    "outcome": "盈利3%",
    "was_correct": true,
    "lessons": ["教训内容"]
}
```

### 跨领域推理
```
POST /api/reason/cross-domain
Body: {
    "topic": "AI与金融市场",
    "depth": 3
}
```

### Maibot协作
```
POST /api/maibot/think
Body: {
    "topic": "复杂投资决策",
    "require_maibot": true
}
```

## 使用示例

### 完整决策流程

```python
from core.cognitive_engine import CognitiveEngine

# 1. 初始化
engine = CognitiveEngine(graph, memory, digester, searcher, health, human, verify, data_dir)

# 2. 思考
signal = engine.think("昆仑万维300418交易策略", {
    "stock": "300418",
    "market": "A股",
    "position": "持仓中"
})

print(f"置信度: {signal.confidence:.0%}")
print(f"警告: {signal.warnings}")
print(f"推理链: {signal.reasoning_chain}")
print(engine.format_think_output(signal))

# 3. 做出决策
if signal.confidence > 0.6:
    decision = engine.make_decision(
        "trade",
        {"stock": "300418", "analysis": signal.decision},
        ["倒T卖出", "观望", "正T买入"]
    )
    print(f"决策ID: {decision['decision_id']}")
    
    # 4. 执行后记录结果
    outcome = engine.record_outcome(
        decision['id'],
        "成功盈利3%",
        True,
        ["坚持了尾盘卖出原则"]
    )
    print(f"准确率: {outcome['accuracy']:.0%}")

# 5. 查看学习到的规则
rules = engine.get_learned_rules()
print(f"已学习规则: {len(rules)}条")

# 6. 查看改进建议
suggestions = engine.suggest_improvements()
for s in suggestions:
    print(f"- {s}")
```

### 跨领域联想示例

```python
from core.reason_engine import ReasonEngine

reasoner = ReasonEngine(graph, data_dir)

# 思考AI对金融交易的影响
result = reasoner.reason("AI量化交易与散户投资者心理", depth=3)

print("发现领域:", result["discovered_domains"])
print("\n类比:")
for analogy in result["analogies"]:
    print(f"  {analogy['from']} ↔ {analogy['to']}")
    
print("\n洞察:")
for insight in result["insights"]:
    print(f"  • {insight}")

# 格式化输出
print(reasoner.format_reasoning(result))
```

## 置信度评分

系统根据以下因素计算置信度:

| 因素 | 分值 | 说明 |
|------|------|------|
| 知识覆盖 | 0-40 | 检索到的相关知识数量 |
| 交叉验证 | 0-30 | 跨领域联想数量 |
| 风险识别 | 0-10 | 是否识别到风险 |
| 元认知 | 0-20 | 是否有推理盲点 |

### 置信度等级

| 等级 | 分数 | 含义 |
|------|------|------|
| A++ | ≥80% | 高置信度，可直接执行 |
| A | ≥60% | 中高置信度，建议验证 |
| B | ≥40% | 中等置信度，谨慎执行 |
| C | ≥20% | 低置信度，需要更多信息 |
| D | <20% | 建议不执行 |

## 闭环学习机制

1. **决策前**: 检查历史教训、风险、推理盲点
2. **决策中**: 生成多个备选方案
3. **决策后**: 记录结果，自动学习
4. **持续改进**: 从错误中提取规则，更新知识库

### 学习规则

```python
# 从错误中学习的规则会被记录
engine.state["learned_patterns"] = {
    "rule_trade_1": {
        "type": "learned_rule",
        "trigger": {"stock": "300418", "action": "追高"},
        "lesson": "追高买入往往导致亏损",
        "success_count": 0,
        "failure_count": 1
    }
}
```

## 与Maibot协作

### 模式1: 被动模式
```
Maibot -> 调用 /api/cognitive/think -> 获取第二大脑决策
```

### 模式2: 主动模式
```
第二大脑遇到复杂问题 -> 咨询Maibot -> 合并结果
```

### 模式3: 知识共享
```
定期同步学习到的规则和教训
```

## 启动服务

```bash
cd F:\aidanao
python server.py
```

服务启动后访问 http://localhost:8766

## 状态文件

- `data/cognitive_state.json` - 认知状态和决策历史
- `data/reason_state.json` - 跨领域推理状态
- `data/maibot_bridge_state.json` - Maibot桥接状态
