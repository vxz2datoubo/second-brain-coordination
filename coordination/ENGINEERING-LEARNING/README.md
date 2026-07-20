# 工程学习系统入口

## 权威蓝图

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

## 生命周期

```text
TaskImpactForecast
→ 任务执行与Agent执行反馈v2
→ OutcomeCalibrationReview
→ EngineeringLearningRecord
→ 模板、规则、蓝图、测试和后续任务回写
```

## 模板

- `TASK-IMPACT-FORECAST-TEMPLATE.yaml`
- `OUTCOME-CALIBRATION-REVIEW-TEMPLATE.yaml`
- `ENGINEERING-LEARNING-REGISTRY.yaml`

## 强制原则

- 非 trivial 任务发布前必须预测正面收益、负面影响和风险门禁。
- 重大风险先告知用户，一般可逆风险由GPT设置控制后继续。
- 验收时必须对比预测与实际。
- 意外正收益需要因果分析和复现实验，不因单次成功直接标准化。
- 意外损害需要根因、控制更新和回归测试，不能只写“下次注意”。
- 新证据可以推翻旧经验，经验必须允许降级和废弃。
