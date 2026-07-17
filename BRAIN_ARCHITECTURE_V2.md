# 波仔智慧大脑 · 完整系统架构 v2.0

> 基于2026年AI Agent最新研究（arxiv 2601.01743, Stanford CS224G, 12大框架横评）
> 核心公式: **Agent = Model + Harness** — Harness决定天花板，不是模型

## 一、系统定位

一个覆盖 **交易 / 创作 / 决策 / 工作流 / 人际** 五大领域的统一AI智能体系统。
对标 Jarvis 级别：不是单一工具，是"会学习、有记忆、能推理、可决策"的认知体。

---

## 二、六层统一架构

```
┌─────────────────────────────────────────────────────────┐
│  Layer 6: 交互层 (Interface)                             │
│  Web Dashboard / CLI / 桌面快捷方式 / MCP桥接            │
├─────────────────────────────────────────────────────────┤
│  Layer 5: 决策层 (Decision Engine)                       │
│  通用决策: /api/deep/decide                               │
│  交易决策: /api/deep/trading/signal                       │
│  认知评估: /api/cognitive/think                            │
│  置信度体系: A++(>80)→A(>60)→B(>40)→C(>20)→D            │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ 交易引擎 │ 创作引擎 │ 系统引擎 │ 人际引擎 │ 未来引擎     │
│ 6因子信号 │ 提示词生成│ Codex调度 │ 关系推理 │ 可扩展        │
│ Medallion │ AI视频流水线│ QClaw算力 │ 情感模型 │             │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│  Layer 4: 推理与规划层 (Reasoning & Planning)            │
│  递归规划 / 因果推理 / 反事实推演 / 跨领域类比            │
│  微分推理: /api/deep/reason  (NeuralLP+置信传播)          │
│  元认知:   /api/deep/meta/decide (自我监控+纠错)         │
├─────────────────────────────────────────────────────────┤
│  Layer 3: 记忆体系 (Memory System)                      │
│                                                          │
│  情景记忆     ← 神经记忆     ← 知识图谱     ← 工作记忆   │
│  Episodic       Neural          Knowledge      Working    │
│  /api/deep/     /api/deep/      /api/retrieve/ 短期上下文  │
│  episodic/*     memory/*        search                     │
│                                                          │
│  记忆三原则: 主动索引 / Ebbinghaus遗忘 / Hebbian强化     │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 持续学习层 (Continual Learning)                │
│  EWC防遗忘 / 经验回放 / 知识蒸馏 / 动态正则化              │
│  /api/deep/continual/learn → consolidate → report        │
├─────────────────────────────────────────────────────────┤
│  Layer 1: 工具与数据层 (Tools & Data)                    │
│  MCP协议 ┆ TDX数据 ┆ neodata ┆ 通达信本地文件 ┆ Web搜索  │
│  标准协议  A股行情   全球金融   日K/5分K二进制   信息获取  │
└─────────────────────────────────────────────────────────┘
```

---

## 三、三大核心协议

| 协议 | 作用 | 我们的实现 |
|------|------|----------|
| **MCP** (Model Context Protocol) | LLM与外部工具通信 | `mcp/` 目录下的QClaw桥/Codex桥/TDX连接器 |
| **A2A** (Agent-to-Agent) | 多Agent协作通信 | Super Jarvis的 inbox/tasks/protocols |
| **Skills** | 延迟加载的子Agent | WorkBuddy的136个技能 + 专家系统 |

---

## 四、五领域知识分类

| 类别 | 标签前缀 | 存储层 | 内容 |
|------|---------|--------|------|
| 📊 **trading** | `trading/` | Neural + Episodic + Knowledge | 交易规则/因子/策略/回测/实时信号 |
| 🎬 **film** | `knowledge/film-` | Neural + Knowledge | 王家卫/特摄/原子朋克提示词/运镜/美学 |
| ⚖️ **decision** | `decision/` | Neural + Meta | 硬规则/闭环教训/置信度评估 |
| 🔧 **workflow** | `workflow/` | Neural + Continual | 沙箱策略/Agent协作/数据管线 |
| 🧬 **evolution** | `evolution/` | Continual + Meta | 自动进化/因果推理/认知引擎 |

---

## 五、运行时数据流

```
用户输入
    │
    ▼
[Layer 6] 桌面快捷方式 / CLI / MCP
    │
    ▼
[Layer 5] deep/decide → 评估意图 + 选择引擎
    │
    ├─ 交易意图 → Medallion 6因子 → trading/signal
    ├─ 创作意图 → AI视频流水线 → Prompt Studio
    ├─ 系统意图 → Codex调度 → QClaw算力
    └─ 知识问答 → 检索 + 推理
    │
    ▼
[Layer 4] deep/reason → 因果推演 + 反事实
    │
    ▼
[Layer 3] memory/read → 查情景/神经/知识图谱
    │
    ▼
[Layer 2] continual/learn → 记录+更新模型
    │
    ▼
[Layer 1] MCP/TDX/neodata → 获取实时数据
    │
    ▼
响应给用户 → 随后: episodic/record + continual/consolidate
```

---

## 六、决策层闭环

```
决策前检查:
  1. deep/memory/read("trading")     ← 查历史教训
  2. retrieve/search("decision")      ← 查硬规则
  3. market data (TDX/neodata)        ← 查实时数据
        ↓
  生成方案A/B/C + 置信度评分
        ↓
  用户确认 or 自动执行
        ↓
  episodic/record → 记录结果
        ↓
  continual/learn → 更新模型权重
        ↓
  下次同样场景: 自动引用上次教训
```

---

## 七、关键设计决策

### 7.1 为什么不直接用LangChain/AutoGen？
我们的8767 deep_server已经是定制化的推理引擎（差分推理+神经记忆+持续学习）。外部框架可以做，但我们的优势是:
- 完全适配A股+TDX数据生态
- 已内置27条领域记忆
- 闭环学习系统自洽
- 无需依赖外部API付费

### 7.2 为什么分五类知识而不是混在一起？
行业最佳实践: 层次化记忆体系。不同类型的知识需要不同的检索频率和遗忘曲线:
- 硬规则(decision): 永不遗忘, 每次决策必查
- 交易知识(trading): 高频检索, 日级更新
- 创作知识(film): 低频检索, 按需加载
- 工作流(workflow): 中频检索, 模式匹配

### 7.3 Harness > Model
2026年共识: Agent的天花板不由底层LLM决定，由Harness(框架+记忆+工具+规则)决定。我们的8767 deep_server就是Harness——模型可以换，但架构不换。

---

## 八、启动命令

```bash
# 1. 启动智慧大脑
python F:/aidanao/deep_server.py               # → localhost:8767

# 2. 启动第二大脑知识图谱
python F:/aidanao/server.py                     # → localhost:8766

# 3. 同步全部知识
python F:/aidanao/medallion_bridge/brain_sync.py

# 4. 盘中交易决策
python F:/aidanao/medallion_bridge/unified_brain.py 300418 --decision

# 或从桌面双击: 启动交易大脑.bat
```

---

## 九、知识总量

| 层 | 数据量 |
|------|------|
| 神经记忆 | 27条 (5类) |
| 知识图谱 | 48节点 + 113边 |
| 情景记忆 | 待积累 (每笔交易写入) |
| 持续学习 | 待训练 (需要>20笔记录触发) |
| 工作记忆 | 运行时上下文 |

---

_基于: arxiv 2601.01743, Stanford CS224G, 2026 Agent框架全景横评, Anthropic MCP协议_
_设计: 迪迪 · 2026-07-06_
