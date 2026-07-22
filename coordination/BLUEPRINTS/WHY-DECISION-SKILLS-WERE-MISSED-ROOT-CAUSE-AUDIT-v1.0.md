# 决策科学技能遗漏根因审计 v1.0

> `module_id: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
>
> `implementation_issue: #63`
>
> `boundary: research_only / NO_TRADE`

## 一、结论

凯利、Markowitz、Black-Litterman、风险平价、Almgren-Chriss、White Reality Check、PBO、Deflated Sharpe等并非从未进入旧蓝图。它们曾作为方法名、能力标签、粗粒度模块或验收条目出现，但没有被继续编译为独立、可调用、可验证的技能。

因此，遗漏不是单纯的“没有想到”，而是系统缺少从知识发现到工程能力的强制转换机制。

## 二、根因

### 2.1 广度优先后缺少技能化门禁

早期蓝图需要尽快覆盖数据、特征、策略、组合、风险、执行、治理和协作，因此优先建立能力地图。问题在于，方法名进入能力地图后，没有自动要求生成：

- Skill ID；
- 输入输出合同；
- 适用条件与非目标；
- 负责人；
- 数据依赖；
- A股制度映射；
- 反例与对抗测试；
- 实施Issue；
- 真实验证和停止条件。

### 2.2 粗粒度模块吞掉独立决策问题

`Portfolio/Risk`、`Execution`、`Validation`等上下文过大，使内部本应分别治理的问题被折叠为一句能力说明。例如：

- “组合优化”同时包含观点融合、协方差估计、权重优化、风险预算和整数约束；
- “执行”同时包含目标仓位转换、成本估计、冲击、排队、时机和TCA；
- “研究审计”同时包含多重检验、数据窥探、试验族登记、锁箱和失败保留。

### 2.3 成熟度语言不精确

旧系统没有统一区分：

`MENTIONED / MAPPED / CONTRACTED / IMPLEMENTED / A_SHARE_TESTED / SHADOW_VALIDATED`。

于是“蓝图里写过”容易被误读为“系统已经具备”。

### 2.4 没有决策生命周期覆盖矩阵

系统按技术模块拆分，而没有反向检查一个完整决策是否覆盖：

`FRAME → BELIEVE → LEARN → CHOOSE → TIME → SIZE → PORTFOLIO → SURVIVE → EXECUTE → VALIDATE → MONITOR → ATTRIBUTE → EVOLVE`。

凯利解决`SIZE`的一部分，但此前没有工具自动指出`LEARN`、`TIME`、`ATTRIBUTE`等环节是否存在可执行能力。

### 2.5 数据闭环优先的合理副作用

先完成真实数据、回放、知识权威和验证闭环是正确的，否则上层技能没有可靠输入。但项目长期处于基础设施建设时，候选决策方法缺少专门Owner，容易永久停留在资料目录。

### 2.6 多Agent按项目分工，没有技能组合治理

Codex、WorkBuddy、QCLAW和GPT各自有项目职责，但过去没有`Skill Portfolio Owner`持续扫描：

- 蓝图术语是否有Skill ID；
- Skill是否存在重复运行时；
- Skill是否只有文档没有合同；
- Skill是否有A股适配和真实测试；
- Skill是否已过时或被更高层能力替代。

### 2.7 新概念触发机制过弱

用户提出“凯利公式和索普”后，系统才从名词回溯完整能力。这说明此前缺少规则：每当重要新理论、大师、论文或专业术语进入正式蓝图，必须进行一次相邻能力扫描。

## 三、永久修复：Blueprint-to-Skill Gap Compiler

建立以下编译链：

```text
蓝图 / Issue / PR / 论文 / 用户要求
→ 术语、理论、方法和大师案例抽取
→ 决策生命周期映射
→ Skill Registry与代码/测试检索
→ 重复、孤儿、幽灵和成熟度判断
→ 候选技能、依赖、优先级和验收门
→ GPT与用户审批
→ Codex实施 / QCLAW消化 / WorkBuddy验证
→ 长期记忆、蓝图和成熟度回写
```

## 四、强制分类

正式蓝图中的每个重要方法必须属于以下一种：

1. `EXISTING_SKILL_SUBCAPABILITY`：明确指向已有Skill和字段；
2. `CANDIDATE_INDEPENDENT_SKILL`：登记Skill ID、Issue和依赖；
3. `REFERENCE_ONLY`：只作知识参考，并说明为什么不计划实现；
4. `REJECTED`：不适合本系统，并保留理由和证据；
5. `UNKNOWN_NEEDS_RESEARCH`：证据或边界不足。

不允许无状态地停留在表格中。

## 五、自动缺口案例

至少检测：

- `ORPHAN_TERM`：重要术语无Skill或子能力映射；
- `GHOST_CAPABILITY`：文档声称具备但无运行时或测试；
- `FORMULA_WITHOUT_ASSUMPTIONS`：公式无假设、边界和反例；
- `SKILL_WITHOUT_A_SHARE_MAPPING`：交易技能未处理A股制度；
- `IMPLEMENTED_WITHOUT_VALIDATION`：有代码无样本外和影子证据；
- `DUPLICATE_RUNTIME`：多个Agent创建相同权威能力；
- `REFERENCE_ONLY_WITHOUT_REASON`：只引用方法却未说明不实施原因；
- `MATURE_STATUS_INFLATION`：蓝图、原型或回测被标为已验证；
- `NO_OWNER_OR_ISSUE`：能力没有负责人和实施任务；
- `NO_NEGATIVE_CASES`：测试只覆盖成功路径；
- `NO_DATA_LINEAGE`：输出无法追溯输入和版本；
- `STALE_RULE_MAPPING`：使用过期交易规则。

## 六、以后如何避免再次遗漏

1. 每次母蓝图升级执行Gap Compiler；
2. 每次用户引入重要新概念，扫描同一决策生命周期的相邻技能；
3. 每季度或重大版本执行Skill Portfolio Review；
4. PROGRAM-INDEX只把`CONTRACTED`以上能力称为已设计；
5. 只有`SHADOW_VALIDATED`以上能力可称为已验证研究能力；
6. 任何升级必须保留失败、反例、UNKNOWN和负面影响；
7. 不以技能数量为目标，合并高度重叠能力，避免技能动物园。

## 七、当前状态

```yaml
root_cause_audit: COMPLETE
blueprint_to_skill_gap_compiler: BLUEPRINTED_NOT_IMPLEMENTED
skill_family_issue: 63
runtime_scanner: NOT_IMPLEMENTED
local_repository_audit: NOT_STARTED
protected_master_backwrite: USER_APPROVED_LOCAL_EXECUTION_PENDING
```
