# ORG-CODEX-REVIEW-DECISION-0004

日期：2026-07-16  
审核对象：`ORG-CODEX-REVIEW-PACK-0003.zip`  
审核结果：**暂不批准合并，要求修订后再审**  
修订说明：v3 已按用户确认的最新ST上下10%规则修正，同时保留每日真实涨跌停价优先和版本化规则引擎。

---

## 一、总体评价

本次迁移的架构方向正确：

- 根 `AGENTS.md` 与交易子系统规则拆分；
- 四方角色重新定义；
- QClaw 从当前组织中移除；
- Codex 升级为首席技术架构师与核心系统建设者；
- WorkBuddy 定位为本地运行、真实接口和运维执行者；
- 数值参数迁入 YAML；
- 未验证经验规则迁入假设文档；
- 原始数值优先于 `+1/0/-1` 展示标签。

但当前候选包仍包含多项会影响真实回测、风控和生产运行的错误，不能直接执行 `APPROVAL_CHECKLIST.md` 中的 D1-D6。

---

## 二、阻断级问题

### B01：交易费用已经过时，并被错误写入 AGENTS.md

当前候选中写有：

- 买入佣金 0.03%
- 卖出佣金 0.03%
- 卖出印花税 0.10%
- 卖出合计约 0.13%

问题：

1. 证券交易印花税自 2023-08-28 起已减半征收，旧的 0.10% 不应继续硬编码。
2. 佣金取决于券商和账户，通常还有最低收费。
3. 还需要考虑过户费、规费、不同品种的收费差异。
4. 根 `AGENTS.md` 自己规定参数应进入配置，却又硬编码费用，内部矛盾。

处理：

- 从根 `AGENTS.md` 和交易子系统 `AGENTS.md` 删除具体费率。
- 新建 `config/trading/cost_model.yaml`。
- 费用按证券类型、交易所、账户和生效日期版本化。
- 默认费率只能作为“候选假设”，不得冒充真实账户费率。
- WorkBuddy 从真实交割单或券商费率说明中生成账户级成本配置。

---

### B02：T+1资金语义错误

当前 `daytrade_system/AGENTS.candidate.md` 写：

> Cash settlement: sold shares fund availability on T+1.

这把以下概念混在了一起：

- 当日可卖证券数量；
- 卖出后可用于买入的资金；
- 可转出至银行卡的资金；
- 清算交收日期。

处理：

建立三个独立字段：

```text
sellable_quantity
available_cash_for_trading
withdrawable_cash
```

规则不得用一句“T+1”覆盖全部语义。真实账户行为必须由券商接口和交割单验证。

---

### B03：ST最新规则按上下10%处理，但生产系统不得依赖单一硬编码常量

用户已明确指出：当前最新ST规则应按上下10%处理。上一版沿用了旧资料口径，必须纠正。

但量化系统仍不能只写一个永久常量：

```text
ST_LIMIT = 10%
```

原因是交易规则可能继续调整，且不同交易所、板块、证券类型、上市阶段和特殊状态仍可能存在差异。

正式处理方式：

1. 当前规则基线：
   - ST股票按最新上下10%规则处理；
   - 旧的“ST=5%”全部删除；
   - “ST仅收盘清算”全部删除。

2. 运行时优先级：
   - 第一优先：正规行情源当日返回的 `upper_limit_price` / `lower_limit_price`；
   - 第二优先：版本化市场规则引擎计算；
   - 两者不一致时，阻断交易并报警，不得自行猜测。

3. 规则引擎至少使用：

```text
exchange
+ board
+ security_type
+ risk_warning_type
+ listing_stage
+ special_status
+ effective_date
```

4. 回测要求：
   - 使用历史交易日当时有效的涨跌停规则；
   - 禁止用当前规则回填全部历史；
   - 保存规则版本、生效日期和来源；
   - 对ST规则变更日前后分别回测。

5. 测试要求：
   - 主板ST上下10%；
   - 创业板、科创板、北交所及特殊上市阶段；
   - 无涨跌幅限制日；
   - 退市整理、复牌和特殊状态；
   - 行情源与规则引擎冲突时自动阻断。


### B04：停牌处理会制造回测偏差

候选写：

> Backtests must mark suspension periods and exclude them from strategy evaluation.

停牌不能简单“从评价中排除”。这会抹掉：

- 仓位无法退出的流动性风险；
- 资金占用；
- 复牌跳空；
- 停牌期间基准变化；
- 最大回撤和风险暴露。

处理：

- 停牌资产继续保留在组合账本。
- 禁止交易，但不得从组合收益和风险中消失。
- 明确估值策略和复牌处理。
- 记录 `stale_price_flag`、`illiquid_position` 和 `days_suspended`。
- 仅在某些信号统计中允许排除不可观测窗口，但组合P&L不得排除。

---

### B05：候选配置存在“假审批”

三个 YAML 中大量出现：

```yaml
approved_by: user
last_validated_at: 2026-07-16
status: candidate
```

问题：

- 用户尚未批准激活。
- 多数参数尚未真实验证。
- `last_validated_at` 容易让系统误以为已经过回测或生产验证。

处理：

改为：

```yaml
proposed_by: user_or_legacy_doc
approval_status: pending
approved_by: null
approved_at: null
last_reviewed_at: 2026-07-16
last_validated_at: null
validation_evidence: null
runtime_enabled: false
```

---

### B06：直接重命名 YAML 可能误激活策略参数

当前批准清单 D4 是：

> 把 `.candidate.yaml` 复制成 `.yaml`

如果运行程序只检查文件名而不检查内部状态，候选参数就可能被加载。

处理：

1. 配置加载器必须拒绝：
   - `runtime_enabled: false`
   - `approval_status != approved`
   - 缺少用户批准时间
2. 治理协议和策略参数分开批准。
3. 本轮最多激活组织协议，不能同时激活未经验证的交易参数。
4. 激活前必须运行配置加载测试。

---

### B07：激活流程缺少原子切换和真实回滚

当前 D1-D6 主要是直接 `cp` 覆盖。

处理：

必须增加：

1. 预激活备份；
2. 所有文件 SHA256；
3. 临时目录部署；
4. YAML解析与Schema测试；
5. Codex指令发现测试；
6. 原子重命名；
7. 激活后健康检查；
8. 失败自动回滚；
9. 回滚命令和上一版本路径；
10. 激活审计记录。

“HARD_LIMIT_VS_HYPOTHESIS”声称生产回滚已被隐式保护，这不充分，必须显式实现。

---

## 三、高优先级问题

### H01：数据源描述仍然自相矛盾

候选协议和 `TRADING-GOVERNANCE.md` 仍写：

> TDX MCP：亚秒级、独有四渠道资金

但冲突报告 C8 已承认：

- TDX MCP 不直接提供四渠道分类；
- 四渠道资金主要来自 WeStock。

处理：

统一修正为：

```text
TDX MCP：实时行情快照、盘口、分钟线、通达信上下文
WeStock：四渠道资金、资金流历史、筹码、板块、新闻等结构化数据
```

“亚秒级”也必须以实测 p50/p95/p99 为准，不能仅按描述写死。

---

### H02：集合竞价仍使用“烟雾弹期/真实意图期/决定性”

候选中仍写：

- 9:15-9:20 烟雾弹期
- 9:20-9:25 真实意图期、决定性

处理：

改成：

- 9:15-9:20：可撤单、低承诺探索期；
- 9:20-9:25：不可撤单、高承诺形成期；
- 不可撤单提高证据权重，但不等于真实方向一定延续；
- 意图只能概率化，并由开盘后量价验证。

---

### H03：根指令优先级与 Codex 官方层级规则需要重新表述

Codex官方规则是：

- 根目录到当前目录逐层加载；
- 越接近当前目录的 `AGENTS.md` 越具体，后加载并覆盖更宽泛规则。

候选把任务包排在嵌套 `AGENTS.md` 之前，可能导致任务包试图覆盖子系统安全规则。

处理：

- 用户当前明确指令最高；
- 根 `AGENTS.md` 定义全局边界；
- 更接近工作目录的 `AGENTS.md` 提供更具体规则；
- TASK-PACKET定义目标、范围和验收，但不得覆盖全局或子系统安全不变量；
- 冲突时停止并上报。

---

### H04：ChatGPT的“模型晋级决定权”需要区分研究与生产

修改为：

- ChatGPT可以做研究阶段的晋级、淘汰建议和独立验收；
- 进入仿真、影子、有限实盘和正式生产，必须由用户批准；
- Codex负责工程验收；
- WorkBuddy负责运行验证。

---

### H05：若干固定门槛不应进入 AGENTS 硬规则

需要从 `daytrade_system/AGENTS.candidate.md` 移出：

- 测试集至少30笔；
- Walk-forward 至少12个月；
- 样本内外退化不超过5%；
- 仿真至少20个交易日；
- 停牌超过5日触发审查。

这些可以作为候选策略治理配置，但不是普适统计定律。

---

### H06：置信度等级没有定义，却带有“立即执行”

`strategy_parameters.candidate.yaml` 中：

```text
A++ → 立即执行
A → 正常执行
```

但 score 的定义、校准、样本外准确率均未给出。

处理：

- 改为 advisory label；
- `execution_action: none`；
- 所有等级保持 `pending_definition`；
- 完成概率校准和仿真验证后再设计执行政策。

---

### H07：WorkBuddy修改权限过于绝对

当前写：

> WorkBuddy may NOT modify trading strategy logic.

应改为：

- WorkBuddy不得在未有任务包、Codex审查和用户必要审批时，直接修改或激活核心策略逻辑；
- WorkBuddy可以在独立分支提出接口映射、运行适配和Bug修复候选；
- 核心代码由Codex审查合并。

---

## 四、内部审计矛盾

### I01：OHLCV r=0.294

`LEGACY-RULES-AUDIT.md` 一处写“已验证”，`STRATEGY-HYPOTHESES.md` 又写“无完整复现脚本，待验证”。

处理：

- 删除“MF r=0.294 已验证”的表述；
- 保留原则：
  - OHLCV不能被标记为交易所级真实资金流；
  - OHLCV可以作为成交活跃度、价格和量能特征；
  - 相关系数需要独立复现。

### I02：审查报告称数据源冲突已修正，但候选正文仍未修正

需要全文统一。

### I03：打包清单

ZIP内实际有23个文件；旧的 `FILE_MANIFEST.sha256` 主要覆盖17个候选/结果文件，不是完整审查包清单。

处理：

- 为整个 `ORG-CODEX-REVIEW-PACK` 重新生成顶层manifest；
- 包含全部文件、ZIP自身SHA256和生成时间。

---

## 五、可以保留的内容

以下内容通过审核：

- 四方角色基本结构；
- Codex作为首席技术架构师和核心建设者；
- WorkBuddy作为本地运行和真实接口执行者；
- QClaw从当前组织模型移除；
- 根规则与交易子系统规则拆分；
- 单写者原则；
- TASK-PACKET协议；
- 原始指标优先，`+1/0/-1`仅展示；
- Wyckoff降级为模型特征/研究框架；
- 未验证经验规则进入假设库；
- 候选文件未直接覆盖正式文件；
- 敏感信息扫描未发现明显秘密。

---

## 六、审批决策

当前状态：

```text
组织架构：原则通过
文件结构：原则通过
交易规则：需修订
配置治理：需修订
激活流程：不通过
正式合并：暂缓
```

不得执行原 `APPROVAL_CHECKLIST.md` 的 D1-D6。

---

## 七、外部量化研究摄入机制

以后搜索到对量化交易有价值的规则、论文、接口或工程方法，不直接散落在聊天中，应进入统一增量流程：

```text
发现资料
→ 可信度分级
→ 判断适用A股范围
→ 转成可验证假设或工程需求
→ Codex建设
→ WorkBuddy取数和运行
→ 回测验收
→ 决定是否进入正式系统
```

建议由 WorkBuddy 维护：

```text
F:\aidanao\research_intake\QUANT-RESEARCH-INTAKE.md
F:\aidanao\research_intake\SOURCE-REGISTRY.csv
```

每条记录至少包括：

- source_title
- source_type
- publication_date
- retrieved_at
- authority_level
- claim
- applicable_market
- required_data
- validation_method
- status
- codex_task_id
- workbuddy_task_id
- accepted_or_rejected_reason

未经回测或工程验证的内容，只能标记为：

- candidate
- hypothesis
- engineering_reference

不得直接升级为交易铁律。

---

## 八、给 WorkBuddy 的修订任务

任务ID：`ORG-CODEX-PATCH-0004`

目标：

根据本审核报告修订候选协议、交易子系统规则、YAML配置、治理文件和激活流程，生成 v2 候选审查包。

必须完成：

1. 修正费用模型；
2. 修正T+1资金语义；
3. 删除ST“仅收盘清算”；
4. 将涨跌幅规则改为版本化规则引擎；
5. 修正停牌组合处理；
6. 清除假审批字段；
7. 配置加载器拒绝候选参数；
8. 增加原子激活和回滚；
9. 修正TDX/WeStock数据源归属；
10. 修正竞价阶段措辞；
11. 修正指令层级；
12. 移出固定统计门槛；
13. 删除未定义置信度的自动执行动作；
14. 统一OHLCV证据状态；
15. 生成完整23+文件manifest。

输出：

```text
F:\aidanao\handoff\ORG-CODEX-REVIEW-PACK-0004.zip
```

在新包通过审核前，不得激活任何候选文件。
