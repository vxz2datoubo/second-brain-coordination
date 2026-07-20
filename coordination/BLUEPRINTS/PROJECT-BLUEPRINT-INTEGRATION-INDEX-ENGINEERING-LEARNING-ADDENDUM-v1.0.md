# 项目蓝图集成索引增补：工程学习与结果校准 v1.0

> `agent_id: GPT`
>
> 状态：ACTIVE
>
> 关联主索引：`PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.0.md`

## 模块登记

- `module_id: ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM`
- `layer: L1_PROJECT_FOUNDATION_CAPABILITY`
- `scope: all non-trivial GPT / Codex / WorkBuddy tasks`
- `boundary: research_only / NO_TRADE by default`

## 权威蓝图

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

## 系统作用

本模块横跨第二大脑、交易系统和多Agent协作流程，负责：

1. 任务发布前的第一性原理拆解；
2. 正面收益、负面影响、成本和机会成本预测；
3. 重大风险的用户告知与审批；
4. 执行期正负效果和停止条件观测；
5. 交付后预测与实际结果校准；
6. 意外收益的因果分析、复现和受控强化；
7. 意外损害的根因分析、控制更新和回归测试；
8. 将经验回写到模板、路由、Agent规则、蓝图、测试和后续任务。

## 强制接口

每个重要任务必须形成：

```text
TaskImpactForecast
→ Agent执行反馈v2
→ OutcomeCalibrationReview
→ EngineeringLearningRecord（存在可复用经验时）
```

## 当前实现状态

```yaml
blueprint: COMPLETE
task_forecast_template: COMPLETE
outcome_review_template: COMPLETE
learning_registry: INITIALIZED
agents_rule_integration: COMPLETE
codex_router_gate: COMPLETE
active_task_forecast_link: COMPLETE
machine_validation_and_ci: QUEUED_IN_ISSUE_30
historical_calibration_backfill: NOT_STARTED
```

## 验收边界

- 结构化表单不能替代因果判断；
- 单次结果不能直接升级为项目标准；
- 经验必须允许被新证据降级或推翻；
- 低风险可逆任务不得因流程负担被无意义阻塞；
- 高风险、不可逆、真实资金、凭证和权威数据源变化仍需用户决定。
