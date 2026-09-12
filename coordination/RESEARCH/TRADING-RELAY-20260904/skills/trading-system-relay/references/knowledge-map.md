# 四层认识与系统映射

agent_id: CODEX | CANDIDATE | 不写用户持久画像

复用已有 EPISTEMIC-0013、PEOS、W3、Method Discovery、Gap Compiler。以下是本次解释计划，不是对用户能力的认证。用户未说不等于用户不知道；“知道但未说”仅能有证据地推断并接受纠正。

| 四层 | 本次内容与证据 | 通俗桥梁 | 专业概念/系统位置 | 验证或下一步 |
|---|---|---|---|---|
| KNOWN_SAID | 用户明确要求 GPT 方向、Codex 架构、WB 实施 | 三人分工接力 | role assignment / handoff contract | 每次交接写实际执行者和待复核者 |
| KNOWN_SAID | 用户明确要 GitHub 同步、本地专用目录、实际跑通 | 图纸与机器都要有 | GitOps / reproducible execution | 指定版本跑出工件，而非回答“可以” |
| KNOWN_SAID | 用户明确考虑算力不足和 WB 成本 | 换人也能继续 | capability-based routing / fallback | 相同测试、不同执行者；成本用真实账单 |
| KNOWN_UNSAID_INFERRED 候选 | 可推断用户希望不丢进度、无需重复解释；仅为需求推断，掌握证据不足 | 接班人拿到完整工作记录 | checkpoint / provenance / idempotency | 让下一人用同一版本重放；不能称用户已精通这些术语 |
| UNKNOWN_BUT_ACCESSIBLE 解释候选 | GitHub 存储与 runner 计算的区别；用户认知状态 UNOBSERVED | 仓库放图纸，运行器开机器 | control plane / data plane / execution plane | 展示 run URL、输出、退出码 |
| UNKNOWN_BUT_ACCESSIBLE 解释候选 | 哈希、版本锁、数据许可、时间戳 | 每份材料有编号、封条和日期 | content addressing / entitlement / PIT | 改一字节被拒绝；晚到数据不能提前可见 |
| UNKNOWN_REQUIRES_SCAFFOLDING 解释候选 | 多重检验、相关样本、概率校准、概念漂移 | 试很多答案总会碰巧中几个，要留下一场考试 | DSR / PBO / purged validation / regime / calibration | 先学训练与考试分开，再解释试验族和时间相关性 |
| UNOBSERVED / ABSTAIN | 未提及的数学掌握、券商权限、具体模型环境 | 不知道就写待核实 | evidence gap / capability unknown | 向对应执行环境做最小探针，勿捏造事实 |

## 端到端概念关系

```text
用户目标 → 需求/风险/成功定义 → GPT版本化设计
      → 接口/测试/数值字典 → Codex工程化
      → WB实现/采集/安装 → 运行器执行
      → 原始数据 → PIT标准化 → 特征 → 候选信号
      → 规则/质量/验证 → 弃权或研究结果
      → Evidence/ContextBundle/LearningPacket → W3候选知识
      → 复核/反证/漂移 → 改良提案 → 下一版本设计
```

横切关系：每条箭头附版本、时间、来源、许可、Owner、验收与失败语义。技能目录只描述能力意图；`skill → input contract → runner → tests → receipt → maturity` 才是可运行映射。

## 技能联动与去重

| 现有能力 | 本技能如何调用/映射 | 不能越过的边界 |
|---|---|---|
| 本地 a-share-point-in-time-market-capture | WB 数据准入阶段读字段/时间/采集回执 | 本次不运行真实采集；不另建 bar model |
| 本地 a-share-four-bucket-fund-flow-observatory | 研究资金分桶时保留源语义，等待能力审计 | 分桶不是已识别机构/游资身份 |
| technical-analysis | 未来明确 RSI/MACD 等指标请求时使用 | 不能替代总体架构、撮合和策略验证 |
| EPISTEMIC-0013 / PEOS | 使用四层解释与 mastery 分离 | 不复制正式用户画像或知识权威 |
| DS-10 / DS-11 / DS-12 | 过拟合、周期漂移、结果归因 | 不以引用论文当作测试已通过 |
| W3 / Integrated Offline Memory | 消费带来源 LearningPacket 候选 | 运行器输出不能自动晋升真理 |
| skill-creator | 校验此技能结构、触发范围、引用 | 技能安装不等于正式治理晋升 |
| openai-docs | 每次产品能力变化时核实工具权限 | GPT模型能力与产品工具能力分开 |

## 从文献到工程的可持续学习

每次新资料进入 `claim → source/version/date → applicable_market/horizon → existing_skill_ref → counterevidence → test → decision`。状态用 DISCOVERED、READ、REPRODUCED、LOCALLY_VALIDATED、REJECTED、REVALIDATION_REQUIRED；不把 READ 写成深度学习完成或模型权重更新。

新增技能须先证明没有合适旧能力、有独立输入输出、有真实使用场景、有负例、有维护 Owner。其余优先补现有技能的子能力或参考材料。每周资料审阅是候选运维流程，本次没有创建自动定时任务；来源优先交易所/供应商变更、项目 release、论文正式发表/预印本状态，周刊仅作发现入口。

优先研究：点时语义、确定性回放、试验选择偏差、执行现实约束、模型切换后的质量。每项同时保留最强反证；没有适用授权数据时停在合成/方法论层。
