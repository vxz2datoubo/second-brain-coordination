# Repository Agent Instructions

## Codex短命令路由

当用户对Codex说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引；若本地有未提交内容，不得为了同步而覆盖工作区。
3. 读取最新 `coordination/CODEX-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 只执行入口文件中 `status: READY`、依赖已满足的 `active_issue`。
6. 必须读取该Issue正文和全部评论，并遵守其中显式标注的Codex模式。
7. 不得根据历史TIMEOUT、INVALID、UNKNOWN回执推断任务已完成。
8. 不得自行选择其他Issue，不得猜测任务编号，不得重新执行索引中 `supersedes` 的旧任务。
9. 完成后按Agent执行反馈v2回传实际证据，并创建独立PR；不得自行合并。
10. 无法确认远端最新索引时必须停止并报告，不得继续执行。

固定协调仓库：`vxz2datoubo/second-brain-coordination`

唯一Codex任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。

## WorkBuddy短命令路由

当用户对WorkBuddy说“读取任务”“执行任务”“开始任务”或同义短句时：

1. 固定协调仓库为 `vxz2datoubo/second-brain-coordination`。
2. 先同步或直接读取远端最新 `main`，不得使用未经确认的本地旧索引，不得覆盖未提交工作区。
3. 读取最新 `coordination/WORKBUDDY-TASK-ROUTER.md`。
4. 再读取最新 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
5. 只执行其中 `status: READY`、依赖已满足的 `active_issue`，不得读取Codex活动索引代替。
6. 必须读取Issue正文、全部评论、任务影响预测、允许列表和安全边界。
7. 现场操作不得超出Issue授权，不能因为拥有本机访问能力就扩大扫描、读取秘密或修改服务。
8. 完成后按完整Agent执行反馈v2和结果观察要求回传，创建独立PR，不自行合并。
9. 无法确认远端索引、路径允许列表或权限边界时必须停止并报告。

唯一WorkBuddy任务真源：远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。

## 工程学习与结果校准硬规则

适用于所有非 trivial 的GPT、Codex和WorkBuddy任务。权威蓝图：

`coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

### 任务发布前

1. GPT必须先完成第一性原理拆解：真实目标、因果机制、约束、证据、失败模式、可观察性、替代方案和停止条件。
2. 必须建立 `TaskImpactForecast`，记录预期正面收益、预期负面影响、执行成本、机会成本、净价值和验证信号。
3. 任务Issue正文或评论必须包含简明的“预期收益与潜在负面影响”段落，并链接或内嵌预测记录。
4. 低风险、可逆风险由GPT自行设置控制并继续，不必频繁打断用户。
5. 出现不可逆损害、真实资金、凭证、重大数据风险、系统级传播、高概率高严重度风险、无可靠回滚或预期净价值为负时，必须先告知用户并等待决定。
6. 没有完成影响预测的任务不得标记为 `READY`，紧急止损、安全隔离和纯信息读取除外，但必须事后补录。

模板：

`coordination/ENGINEERING-LEARNING/TASK-IMPACT-FORECAST-TEMPLATE.yaml`

### 执行期间

1. 执行者必须观察预测收益和风险信号，并在Agent执行反馈v2中报告实际正负效果。
2. 意外损害达到高严重度、跨模块传播或接近停止条件时，立即中止或报告，不得等任务结束。
3. 不得为了符合任务前预测而隐藏相反证据。

### 交付验收时

1. GPT必须建立 `OutcomeCalibrationReview`，逐项对比预期收益、预期负面影响和实际结果。
2. 必须识别意外收益、意外损害、执行成本偏差、复杂度偏差和风险控制副作用。
3. 偏差必须分类为：预测错误、执行错误、环境变化、测量错误或未知未知。
4. 实际负面效果高于预期时，不得只写“下次注意”，必须形成根因、控制更新和回归测试。
5. 意外正收益必须分析因果链、必要条件、替代解释、放大风险和最小复现实验。
6. 单次成功不能直接升级为长期标准，必须保留反证并通过复现提高成熟度。

模板：

`coordination/ENGINEERING-LEARNING/OUTCOME-CALIBRATION-REVIEW-TEMPLATE.yaml`

### 经验回写

1. 可复用经验写入：
   `coordination/ENGINEERING-LEARNING/ENGINEERING-LEARNING-REGISTRY.yaml`
2. 根据影响范围同步更新任务模板、AGENTS规则、路由、专项蓝图、测试、禁止清单或本地权威蓝图差异包。
3. 每个后续任务必须检查是否存在可继承的相关工程经验。
4. 新证据推翻旧经验时，必须将旧经验降级为 `DEPRECATED` 或 `CONTRADICTED`，不得维护虚假一致性。
