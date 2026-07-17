# Brain Rebuild Report

Generated: 2026-06-17T13:18:23

## 1. Inbox 处理详情

- 处理前 inbox 节点: 16
- 处理后 inbox 节点: 11
- 原则: 有明确知识结论的节点移入对应分类；仅有会话路径、端口、时间的节点保留 inbox 作为溯源索引。

| ID | 标题 | 原分类 | 新分类 | 处理说明 |
|---|---|---|---|---|
| `c0ff0655` | 脏图修复自动化流程 | inbox | film-video | 脏图修复流程属于 AI 视频生成与图像修复工作流。 |
| `c01ab69e` | 进化机制与自动修复 | inbox | tech-ai | 进化机制、索引、Schema 和自动修复属于第二大脑 AI 系统治理。 |
| `0dfe1ec4` | 贾维斯事件引擎: 自动提取+冲突检测+多渠道提醒 | inbox | tech-ai | 贾维斯事件引擎属于智能助手/第二大脑能力。 |
| `d43218f7` | 规则: 本对话是最优先知识来源，自动自我摄入 | inbox | decision-lessons | 这是行为规则和自我摄入决策标准。 |
| `fd5587d7` | 会话: ai (2026-06-16) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `d959d6ac` | 会话: .workbuddy (2026-06-15) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `6875a369` | 会话: ai (2026-06-15) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `09ed829c` | 项目记忆: 2026-06-15 | inbox | tech-ai | 项目记忆记录第二大脑同步、索引与健康评估。 |
| `4761351c` | 会话: work (2026-06-16) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `ce2cb83b` | 会话: .workbuddy (2026-06-16) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `6b05e1e9` | 会话: QQSafeChat (2026-06-16) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `cf4cd700` | 会话: QQSafeChat (2026-06-17) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `ecf91bbd` | 会话: ai (2026-06-17) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `0f8707b7` | 会话: 2026-06-17-00-10-50 (2026-06-17) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `719fd6f1` | 会话: .workbuddy (2026-06-17) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |
| `c6f21f1a` | 会话: work (2026-06-17) | inbox | inbox | 纯会话元数据，缺少可归纳的知识结论，保留为溯源索引。 |

## 2. 标签系统 V2

每个节点新增 `tags_v2`，包含 `domain`、`type`、`entity`、`difficulty`、`keywords` 五个维度。旧 `tags` 保留为语义关键词列表，并清理单字、数字、UUID/hex 片段和会话噪音词。

### 分布
- domain: {'business': 18, 'programming': 16, 'tech-ai': 35, 'film-video': 26}
- type: {'concept': 33, 'tool': 45, 'tutorial': 8, 'methodology': 37, 'case-study': 30, 'lesson-learned': 14}
- difficulty: {'beginner': 43, 'intermediate': 25, 'advanced': 27}
- entity: {'QClaw': 19, 'PromptStudio': 4, '小樱花': 15, 'WorkBuddy': 32, 'Jarvis': 8, 'Codex': 10}
- category: {'life': 3, 'tech-programming': 16, 'tech-ai': 18, 'film-video': 26, 'business': 9, 'decision-lessons': 6, 'inbox': 11, 'academic': 3, 'design': 3}

## 3. 新增交叉关联

新增 cross-category edges: 12

| Edge | Source | Target | Relation | Strength |
|---|---|---|---|---|
| `bc480430` | AI视频提示词系统架构 | 焊接台工厂市场拓展方案 | cross_category: AI视频提示词模板可迁移为焊接台工厂短视频获客脚本，提高商业转化。 | 0.72 |
| `86468cfc` | AI视频10维度导演框架 | Serenity市场评价与机会 | cross_category: AI视频导演框架可用于 Serenity 市场机会的内容表达和视觉包装。 | 0.66 |
| `ccb02d5f` | 进化机制与自动修复 | 自我纠偏机制: 不降级标准 + 决策前查教训 | cross_category: 自动修复机制需要接入决策前查教训，避免重复犯错。 | 0.78 |
| `3baada3b` | 贾维斯事件引擎: 自动提取+冲突检测+多渠道提醒 | 决策前自动检索系统 (decision-consult) | cross_category: 贾维斯事件提醒可触发决策检索，把日程事件和历史教训联动。 | 0.80 |
| `ffafabb1` | 规则: 本对话是最优先知识来源，自动自我摄入 | 第二大脑系统设计 | cross_category: 自我摄入规则直接强化第二大脑系统设计中的实时学习闭环。 | 0.84 |
| `86721ebd` | 【默认风格】AI视频/图像生成标准风格参数 | 抖音分析:  | cross_category: 默认电影风格参数可作为抖音内容分析后的生成标准。 | 0.70 |
| `5fd90430` | QClaw算力引擎验证报告 (2026-06-16) | Codex集成方案-WorkBuddy高级智能体层 | cross_category: 算力引擎验证结果为 Codex/WorkBuddy 高级智能体层提供运行基础。 | 0.67 |
| `e24b866a` | task3-decision-engine | AI女友系统:双层人格演化架构 | cross_category: 决策引擎与双层人格演化架构共同决定小樱花行为输出。 | 0.82 |
| `7b6ce4b3` | A股个股分析: 昆仑万维300418 蓝色光标300058 | QClaw能力清单: A股量化+Agent调度+本地AI+技能生态 | cross_category: A股个股分析依赖 QClaw 的量化和 Agent 调度能力。 | 0.76 |
| `a92ca54f` | 抖音分析: 丧尸清道夫提示词模板教程 | 抖音分析: 科创的第二轮 IPO 快的话这俩月？ - 抖音 | cross_category: 丧尸清道夫提示词教程与 IPO 抖音分析共享短视频拆解和运营方法。 | 0.64 |
| `2e5b6431` | 瓶颈理论方法论 | 教训: 未验证核心假设就全力推进方案 | cross_category: 瓶颈理论可解释未验证核心假设就推进方案的决策错误。 | 0.71 |
| `fd8f5270` | 脏图修复自动化流程 | 即梦Seedance视频自动化管道设计 | cross_category: 脏图修复流程是即梦视频自动化管道的质量补救环节。 | 0.86 |

## 4. 思考维度覆盖分析

| 维度 | 已覆盖节点 | 缺失节点 |
|---|---:|---:|
| 是什么 | 55 | 40 |
| 为什么 | 28 | 67 |
| 怎么做 | 48 | 47 |
| 谁 | 43 | 52 |
| 何时 | 45 | 50 |
| 哪里 | 54 | 41 |
| 多少钱/多少量 | 22 | 73 |
| 影响 | 32 | 63 |
| 相关关系 | 39 | 56 |

相对薄弱维度: 为什么, 多少钱/多少量, 影响。

## 5. 知识蒸馏

- 内容超过 3000 字节点: 8
- 已为长节点刷新 `summary` 字段，用于快速回忆。

## 6. 下一步建议

- 把仍在 inbox 的会话元数据与原始会话文件二次解析，提取其中真正的决策、教训和项目产物。
- 为 `thinking_dimensions` 增加人工校准入口，避免关键词规则误判。
- 对 cross-category edges 增加来源证据字段，例如引用的句子或触发关键词。
- 将 `tags_v2` 写入检索权重，支持按领域、类型、实体和难度组合检索。

