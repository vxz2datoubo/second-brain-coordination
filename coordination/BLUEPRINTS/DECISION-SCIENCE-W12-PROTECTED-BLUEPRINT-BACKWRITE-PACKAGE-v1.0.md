# W12决策科学技能族本地权威蓝图回写差异包 v1.0

> `module_id: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
>
> `implementation_issue: #63`
>
> `user_approval: GRANTED_BY_CURRENT_BLUEPRINT_INTEGRATION_REQUEST`
>
> 本文件描述三份本地受保护权威蓝图需要增加的章节和引用，不复制本地正文。

## 一、写回“第二大脑权威总蓝图”

新增一级子系统：

`决策科学技能族与蓝图缺口编译器`

必须增加：

1. 决策生命周期：FRAME、BELIEVE、LEARN、CHOOSE、TIME、SIZE、PORTFOLIO、SURVIVE、EXECUTE、VALIDATE、MONITOR、ATTRIBUTE、EVOLVE；
2. DS-01至DS-13的Skill ID、职责、非目标、依赖和成熟度；
3. Blueprint-to-Skill Gap Compiler；
4. 术语强制分类：已有子能力、新候选技能、REFERENCE_ONLY、REJECTED或UNKNOWN；
5. Skill成熟度状态机；
6. 与WorldModel、TaskContextModel、DecisionEpisode、MetacognitiveAudit的数据流；
7. 个人模型不得暗中设定世界概率、效用函数、组合权重或风险限额；
8. 研究、失败、反例、状态和技能版本进入长期记忆；
9. Gap Compiler的误报、漏报和错误合并评测；
10. 第一轮最多三个P0纵向切片。

## 二、写回“A股交易系统权威总蓝图”

新增一级工作流：

`W12 决策科学技能族与技能完整性治理`

必须增加：

1. DS-01问题框定与影响图；
2. DS-02概率更新和预测融合；
3. DS-03信息价值和研究停止；
4. DS-04模糊不确定性和稳健选择；
5. DS-05序贯决策和最优停止；
6. DS-06影子探索利用；
7. DS-07观点到组合权重；
8. DS-08风险预算、CVaR、回撤和资本生存；
9. DS-09执行成本、Implementation Shortfall和TCA；
10. DS-10多重检验、PBO、DSR、White和SPA；
11. DS-11市场状态、结构突变和模型衰减；
12. DS-12市场、因子、选择、仓位、执行和随机性归因；
13. DS-13多目标效用、机会成本和资本配给；
14. 与W2/W4/W5/W6/W7/W9/W10/W11及OMS的非重复建设边界；
15. 所有交易技能共享按生效日版本化的A股规则合同；
16. Shadow、Paper和高风险部署的升级门，保持NO_TRADE。

## 三、写回“第二大脑与交易系统协作机制权威蓝图”

新增链路：

```text
用户目标和问题
→ DS-01框定
→ WorldModel / DS-02概率更新
→ DS-03信息价值
→ DS-04稳健选择 / DS-05时机
→ W11期望值和资本配置
→ DS-07组合 / DS-08生存
→ DS-09执行研究
→ DS-10研究审计
→ DS-11状态监控
→ DS-12归因
→ DS-13目标与资源更新
→ DecisionEpisode、工程学习和长期记忆
```

必须明确：

- GPT负责研究边界、优先级、反向审视和验收；
- Codex负责Gap Compiler、机器合同和canonical集成；
- QCLAW负责论文消化、术语原子、候选技能和对抗夹具；
- WorkBuddy负责本地蓝图/代码实况、A股规则和运行证据；
- 用户拥有目标、风险、资本和高风险批准权；
- 任何Agent不得因为发现术语而自动创建实盘技能；
- 第一轮最多三个P0切片，避免技能动物园和并行冲突。

## 四、机器引用

三份本地蓝图Manifest建议登记：

- module_id: `DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
- task_id: `DECISION-SCIENCE-SKILL-GAP-COMPILER-0012`
- implementation_issue: `63`
- program_charter: `v1.3`
- integration_index: `v1.3`
- root_cause_audit: `WHY-DECISION-SKILLS-WERE-MISSED-ROOT-CAUSE-AUDIT-v1.0.md`
- specialized_blueprint: `DECISION-SCIENCE-SKILL-FAMILY-AND-GAP-COMPILER-BLUEPRINT-v1.0.md`
- research_validation: `DECISION-SCIENCE-SKILL-FAMILY-RESEARCH-VALIDATION-v1.0.md`
- skill_registry: `DECISION-SCIENCE-SKILL-FAMILY-REGISTRY-v1.0.yaml`
- protected_backwrite_status: `USER_APPROVED_LOCAL_EXECUTION_PENDING`
- runtime_status: `NOT_IMPLEMENTED`
- boundary: `research_only / NO_TRADE`

## 五、回写验收

本地权威回写完成需要：

1. 用户批准，当前已满足；
2. 三份本地蓝图增加对应章节或正式引用；
3. Manifest、版本或哈希更新；
4. 原有Portfolio/Risk/Execution能力与新技能无权威冲突；
5. 旧蓝图方法名被登记为已有子能力、候选技能或明确参考项；
6. 不把候选技能写成已实现；
7. NO_TRADE和秘密边界一致；
8. 完成状态反馈至Issue #31和#63。

当前状态：`USER_APPROVED / LOCAL_PROTECTED_MASTER_EXECUTION_PENDING`。
