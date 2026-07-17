# 【Codex模式：普通执行】

**选择原因：** 本轮是范围明确的 P0 修复、分类器加固和测试补齐，不需要项目计划模式，也不需要目标模式。

## 任务

`TDX-L2-AGGREGATE-HARDENING-0013`

## 当前状态

上一任务 `TDX-L2-AGGREGATE-CODE-REVIEW-0011` 已完成审查，但 ChatGPT 在完整 diff 中发现一个未被测试捕获的 P0 错误。

当前代码状态保持：

- `IMPLEMENTED_EXPERIMENTAL`
- `P0_FIX_REQUIRED`
- `NOT_APPROVED_FOR_FORMAL_PHASE_1`

本任务完成并通过验收前，不得进入真实券商、真实行情或正式实时集成。

---

## 1. P0 修复：`_to_number`

当前 `brain_core/realtime_l2_aggregate.py` 中：

- `_to_number()` 只处理 `None` 和空字符串；
- 非空输入没有执行数值转换；
- 原本的 `try/except` 被错误放在 `_has_text()` 的 `return` 之后，成为不可达代码。

修复要求：

| 输入 | 预期 |
|---|---|
| `None` | `None` |
| `""` | `None` |
| `" "` | `None` |
| `"0"` | `0.0` |
| `0` | `0.0` |
| `"123.45"` | `123.45` |
| `123` | `123.0` |
| `"-5.2"` | `-5.2` |
| `"abc"` | `None` |
| `object()` | `None` |

不得把非数字字符串静默转为 `0`。删除 `_has_text()` 中 `return` 之后的不可达代码。

---

## 2. 缺失、错误与数值状态

当前 `missing_kind` 只有 `present` 和 `zero_value`，需要扩展并测试：

- `missing`
- `empty`
- `zero_value`
- `present_numeric`
- `present_non_numeric`
- `permission_denied`
- `interface_error`
- `not_applicable`
- `unknown_sentinel`

不要猜测通达信未确认的错误哨兵。未知字符串必须保留原值，并标记为 `present_non_numeric` 或 `unknown_sentinel`。

---

## 3. 禁止单条载荷过度声明能力

`normalize_tdx_l2_aggregate_payload()` 当前无条件声明：

- `FIVE_LEVEL_SNAPSHOT`
- `L2_AGGREGATE`
- `UPDATE_TRIGGER_COMPATIBLE`

但该函数输入只是 `get_more_info` 聚合载荷。

修改为：

- 单条 `get_more_info` 载荷默认只声明 `L2_AGGREGATE`
- 五档能力由 `get_market_snapshot` 的独立证据声明
- 更新触发能力由 `subscribe_hq` 的独立证据声明
- 路由级能力组合进入 `SourceCapabilityRegistry`
- 不得把某一路由的能力复制到不含对应数据的单条载荷

---

## 4. 分类器生命周期 v0.2

未来完整生命周期：

- `insufficient`
- `needs_documentation`
- `qualified_for_readonly_probe`
- `runtime_probe_failed`
- `runtime_verified_research_only`
- `approved_for_governed_integration`
- `blocked`

本轮分类器只允许输出探针前状态：

- `insufficient`
- `needs_documentation`
- `qualified_for_readonly_probe`
- `blocked`

其余状态只建立枚举和迁移规则，不得伪造运行结果。

---

## 5. 探针候选硬门槛

### 普通程序化行情能力

客户经理口头承诺、UI 截图或 `capabilities=yes`，都不能直接进入 `allowed_capabilities`。

五档、十档、L2 聚合至少需要：

- 官方字段表或 SDK 文档
- 或脱敏真实样本 payload

证据不足只能进入 `needs_documentation`。

### `RAW_TRADE_TICK`

进入 `qualified_for_readonly_probe` 至少需要：

- 官方字段表
- SDK 文档
- 样本 payload
- 自动化许可
- 本地研究许可
- 明确时间戳语义
- 可稳定排序的序列号、事件 ID 或等价顺序字段

### `RAW_ORDER_EVENT` / `ORDER_QUEUE` / `CANCEL_EVENT`

除上述要求外，还需要：

- 委托序列
- 频道号或等价分区字段
- 日初基线或订单簿恢复方法
- 断线恢复或补包说明

### 本地存储与自动化

- `local_storage_allowed=no`：不得进入当前母系统正式候选
- `automation_allowed=no`：不得进入自动采集探针
- 可标记 `transient_view_only` 或 `view_only_not_automatable`
- 不得进入 `approved_for_governed_integration`

---

## 6. SDK 交易能力隔离

SDK 中存在交易方法本身不能导致 `blocked`。

只有以下情况才阻断：

- 行情必须调用账户、资产、持仓、委托或下单接口
- 必须提供交易密码
- 必须连接交易柜台且无法隔离
- 无法建立只读白名单
- 初始化自动启用实盘交易连接

增加结构化字段：

- `readonly_process_supported`
- `method_whitelist_supported`
- `separate_market_data_entitlement`
- `trading_password_required`
- `trading_counter_required`

---

## 7. 公开爬虫政策

保留：

`usage_class = auxiliary_crosscheck_only`

不要再把 `0.55` 描述成实测可靠度。

增加：

- `reliability_calibration_status = uncalibrated`
- `evidence_quality = official | licensed_vendor | public_portal | unofficial | unknown`
- `default_reliability_hint` 可保留，但明确不是测量结果

为未来动态可靠度预留：

- `delay_ms`
- `missing_rate`
- `timestamp_quality`
- `staleness_rate`
- `cross_source_consistency`
- `license_status`

---

## 8. 测试补齐

至少覆盖：

### 数值转换

- `None`
- 空字符串
- 空格
- 数字 `0`
- 字符串 `"0"`
- 正整数
- 浮点数
- 负数
- 非数字
- 非标准对象

### 字段状态

- missing
- zero
- nonnumeric
- permission_denied
- interface_error
- not_applicable
- unknown_sentinel

### 聚合语义

- 13 字段完整
- 部分字段缺失
- 全部字段缺失
- 出现额外字段
- 字段语义版本变化
- 同日负 delta 异常
- 跨日 reset 允许
- 累计值在未知重置边界下降时不得静默生成 delta

### 分类器

至少覆盖：

- L2 只有口头承诺
- 十档只有 UI 截图
- Tick 有文档但无样本
- Tick 无交易所时间
- Tick 无顺序字段
- 禁止本地落盘
- 禁止自动化
- SDK 含交易方法但可完全隔离
- 必须连接交易柜台
- 完整证据进入 `qualified_for_readonly_probe`

测试不得只断言当前常量，必须断言具体行为。

---

## 9. 母系统纠偏写回

不要删除历史记录。

测试全部通过后，追加纠偏记录：

- 旧分类器 v0.1 标记为 `Experimental / Superseded`
- 新分类器注册为 v0.2
- `validation_status = hardened_tests_passed`
- 旧 TDX 聚合模块保留历史证据
- 不把任何券商路线提升为已验证
- 不解除任何 raw L2 能力门禁

公告栏明确记录：

- P0 numeric conversion bug fixed
- classifier lifecycle hardened
- no runtime broker route approved

---

## 10. 回归测试

至少运行：

```bash
python -m unittest tests.test_realtime_l2_aggregate tests.test_foundation_data_governance
```

并运行新增测试文件。

保存：

- Python 绝对路径
- Python 版本
- 工作目录
- 完整 stdout / stderr
- exit code
- 测试名称清单

说明是否需要更广泛交易域回归测试，以及依据。

---

## 11. 禁止事项

本轮不得：

- 调用 TdxQuant
- 调用 TDX MCP
- 访问或修改 `F:\tongdaxin`
- 联系券商
- 登录账户
- 运行任何交易、资产、持仓、委托、撤单或下单接口
- 进入真实券商或行情 runtime probe
- Git init / add / commit / push
- 删除历史母系统记录

---

## 12. 输出目录

创建：

`F:\aidanao\coordination\RESULTS\TDX-L2-AGGREGATE-HARDENING-0013\`

至少输出：

- `P0-BUG-ROOT-CAUSE.md`
- `CODE-PATCH.diff`
- `NUMERIC-CONVERSION-TESTS.md`
- `MISSING-KIND-SEMANTICS.md`
- `CLASSIFIER-V2-LIFECYCLE.md`
- `CLASSIFIER-V2-EDGE-CASES.json`
- `CRAWLER-RELIABILITY-REVISION.md`
- `TEST-RUN-EVIDENCE.json`
- `MOTHER-SYSTEM-CORRECTION-WRITEBACK.md`
- `FINAL-HARDENING-REVIEW.md`
- `STATUS.yaml`
- `RUN-RECEIPT.md`

---

## 13. 最终回复格式

只回复：

- `task_id`
- `mode=normal_execution`
- `status`
- P0 数值转换错误是否确认
- 根因
- 修复文件
- `numeric_value` 是否恢复
- `zero_value` 是否正确识别
- 分类器生命周期是否升级
- 无时间戳或顺序字段是否仍能进入探针候选
- 禁止本地落盘是否仍能进入正式候选
- 十档口头承诺是否仍能进入 allowed
- 爬虫可靠度是否标记为未校准
- 新增测试数量
- 全部测试结果
- 是否存在范围外修改
- 母系统如何纠偏
- 是否建议批准正式 Phase 1
- 输出目录

完成后停止。
