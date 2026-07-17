## MEMORY PATCH

patch_id: QMEM-20260716-0002
date: 2026-07-16
reason: Codex完成首次永久记忆总纲审阅，补充母系统工程缺口和优先级。

add:
  - 统一母系统对象模型必须覆盖来源、证据、市场数据、特征、回测、验证、决策、预测、交易日志和自我演化。
  - 数据层必须明确raw、normalized、features、signals、reports、runtime_logs的边界和写入权。
  - 策略必须具备candidate/research/validated/simulation/shadow/limited_live/production生命周期。
  - 验证结果支持keep、downgrade、freeze、retire。
  - 数据接口必须建立正式capability schema、quality flags、fallback和source reliability规则。
  - 永久记忆总纲是导航索引，不是运行配置。

modify:
  - 第一阶段建设顺序调整为：
    1. 统一对象模型、数据适配、能力协商和质量治理；
    2. A股规则引擎、微观结构与时段语义；
    3. Replay + Validation闭环。
  - 暂不把治理链从brain_core + bulletin + data迁移到memory目录。
  - 使用Memory Patch进行桥接。

deprecate:
  - 旧的“先单独建设接口Adapter，而不补对象模型和数据层边界”的狭窄任务定义。

evidence:
  - Codex首次完整审阅回复。
  - 用户确认Codex作为首席技术架构师。

affected_modules:
  - brain_core
  - bulletin
  - data
  - market_data_adapters
  - validation
  - memory_governance

approved_by: pending_user_confirmation
status: proposed
