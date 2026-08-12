# 工程学习系统入口

## 权威蓝图

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

## 生命周期

```text
TaskImpactForecast
→ 发布前匹配本地问题模式与预防门禁
→ 任务执行与Agent执行反馈v2
→ OutcomeCalibrationReview
→ EngineeringLearningRecord
→ 永久修复 / 回避控制 / 回归测试
→ 模板、规则、蓝图、测试和后续任务回写
```

## 模板与登记表

- `TASK-IMPACT-FORECAST-TEMPLATE.yaml`
- `OUTCOME-CALIBRATION-REVIEW-TEMPLATE.yaml`
- `ENGINEERING-LEARNING-REGISTRY.yaml`
- `LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`：跨Agent本地执行问题模式与发布前预防门禁。

## 本地问题预防闭环

`LOCAL-EXECUTION-ISSUE-PATTERNS.yaml` 不属于任何单一业务项目。它用于 GPT、Codex、QCLAW、WorkBuddy 和未来 Agent 的跨项目执行治理，重点覆盖编码、中文/Unicode字符、路径、YAML/JSON解析、shell quoting、脚本调用、Git传输等可复现问题。

任务发布者只读取与本任务工具、格式、平台和操作匹配的模式：

1. 能安全、低风险、在授权范围内永久消除根因时，优先永久修复并增加回归；
2. 根因未明或永久修复越权时，采用已验证回避/containment，并保留精确Unknown或follow-up；
3. 已知高频问题不得只写“下次注意”或机械重试；
4. 单次修复不能直接升级为长期标准；成熟度服从工程学习登记表；
5. YAML/JSON/代码等存在正式parser/compiler/runtime时，必须用真实工具验证，而不是仅grep或肉眼检查。

## 强制原则

- 非 trivial 任务发布前必须预测正面收益、负面影响和风险门禁。
- 发布前必须检查与任务技术栈匹配的本地问题模式，并把适用的预防项写入验收。
- 重大风险先告知用户，一般可逆风险由GPT设置控制后继续。
- 验收时必须对比预测与实际。
- 意外正收益需要因果分析和复现实验，不因单次成功直接标准化。
- 意外损害需要根因、控制更新和回归测试，不能只写“下次注意”。
- 新证据可以推翻旧经验，经验必须允许降级和废弃。
