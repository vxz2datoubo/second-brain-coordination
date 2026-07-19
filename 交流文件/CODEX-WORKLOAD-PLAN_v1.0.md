# CODEX WORKLOAD PLAN v1.0

项目：F:\aidanao  
定位：让 Codex 作为首席技术架构师持续饱和工作，同时避免与 WorkBuddy 重叠或多任务互相覆盖。

---

## 一、调度原则

Codex不再只承担单一任务。

采用：

```text
1条主建设线
+ 2条并行审计/设计线
+ 1条结果复核线
```

每条线必须使用独立 branch 或 worktree。

Codex负责核心架构、核心代码、测试和技术债。

WorkBuddy负责真实接口、Windows环境、长期运行、数据采集和结果打包。

---

## 二、当前四条工作线

## A线：主建设线

任务ID：

`FOUNDATION-DATA-GOVERNANCE-0001`

目标：

- 统一对象模型
- 数据分层
- MarketDataAdapter
- capability schema
- quality flags
- lineage
- raw → normalized → features → signals
- memory authority boundary
- lifecycle skeleton

建议分支：

`codex/foundation-data-governance-0001`

优先级：

P0

状态：

立即执行

---

## B线：仓库架构与技术债审计

任务ID：

`REPO-ARCH-AUDIT-0001`

模式：

只读审计，不修改生产代码

目标：

1. 绘制当前仓库模块图；
2. 找出重复对象、重复技能、重复数据层；
3. 找出brain_core、bulletin、data、daytrade_system之间的耦合；
4. 标记：
   - keep
   - merge
   - refactor
   - deprecate
   - unknown
5. 输出技术债优先级；
6. 给出未来6个核心模块边界；
7. 找出所有可能的数据泄漏入口；
8. 找出所有硬编码市场规则；
9. 找出所有无测试的生产路径；
10. 不直接重构。

建议分支：

无需分支，纯只读；如需生成报告，使用：

`codex/repo-arch-audit-0001`

优先级：

P0

状态：

可与A线并行

---

## C线：测试、CI与回归治理设计

任务ID：

`TEST-CI-GOVERNANCE-0001`

目标：

- 建立测试矩阵
- 单元测试
- 集成测试
- 数据契约测试
- 防未来数据泄漏测试
- T+1测试
- 涨跌停/停牌测试
- 配置候选不可激活测试
- Adapter降级测试
- replay determinism测试
- regression baseline
- CI建议
- 测试数据fixture规范

限制：

- 不接真实券商
- 不改实盘配置
- 不与A线修改同一文件
- A线尚未稳定的对象，只能使用Mock或接口契约

建议分支：

`codex/test-ci-governance-0001`

优先级：

P1

状态：

可与A线并行，但合并顺序在A线之后

---

## D线：WorkBuddy结果复核线

任务ID模式：

`WB-RESULT-REVIEW-<原任务ID>`

目标：

每当WorkBuddy返回以下内容时，由Codex做技术复核：

- TDX MCP真实字段
- TdxQuant字段
- 历史逐笔文件Schema
- 数据质量报告
- Adapter部署结果
- 延迟/丢包/乱序报告
- 回测运行包
- 服务异常

Codex只做：

- 字段一致性检查
- Schema映射
- 工程风险
- 测试缺口
- 修复建议
- 合并建议

WorkBuddy继续负责真实运行。

状态：

常驻待命

---

## 三、第二阶段任务池

A线第一版完成后，立即启动：

### 1. A股规则与微观结构引擎

任务ID：

`ASHARE-RULES-MICROSTRUCTURE-0001`

内容：

- 集合竞价阶段
- T+1库存
- sellable_quantity
- available_cash_for_trading
- withdrawable_cash
- 涨跌停
- 停牌
- ST和特殊状态
- 逐笔成交/委托/盘口统一语义
- 规则版本化

### 2. Replay + Validation闭环

任务ID：

`REPLAY-VALIDATION-0001`

内容：

- 历史回放
- point-in-time
- walk-forward
- 样本内/样本外
- 交易成本
- 滑点
- 不可成交
- strategy lifecycle
- keep/downgrade/freeze/retire
- ValidationReport

### 3. 消息事件总线

任务ID：

`NEWS-EVENT-BUS-0001`

内容：

- NewsEvent
- EvidenceItem
- expectation gap
- prepriced score
- event window
- price/volume/volatility response
- event decay

---

## 四、禁止事项

- 不让多个Codex任务编辑同一文件；
- 不让Codex与WorkBuddy同时编辑核心代码；
- 不让并行任务都重建同一对象模型；
- 不连接真实交易；
- 不激活候选策略参数；
- 不让Codex自己假设vendor字段；
- 不把“任务多”变成“重复建设多”。

---

## 五、推荐负载

当前立即运行：

```text
A线：FOUNDATION-DATA-GOVERNANCE-0001
B线：REPO-ARCH-AUDIT-0001
C线：TEST-CI-GOVERNANCE-0001
D线：等待WorkBuddy接口审计结果
```

合并顺序：

```text
A线核心契约
→ C线测试框架
→ B线建议转成后续重构任务
→ D线真实字段映射
```

---

## 六、成功标准

Codex不是“忙起来”就算成功。

真正标准：

- 核心架构持续推进；
- 没有重复建设；
- 每条线有独立产物；
- 每条线有测试或审计结果；
- WorkBuddy能够实际部署；
- ChatGPT能够独立验收；
- 用户仍保留高风险批准权。
