# 第二大脑＋A股交易研究企业蓝图收敛与依赖地图 v1.1

> agent_id: `CODEX`
>
> supersedes: `ENTERPRISE-BLUEPRINT-CONVERGENCE-AND-DEPENDENCY-MAP-v1.0.md`
>
> governance_issue: `#72`
>
> status: `CODEX_VERIFIED_CANDIDATE_PENDING_GPT`
>
> boundary: `research_only / NO_TRADE`

> R1 correction: implementation maturity and canonical authority readiness are
> separate axes. W3 remains `UNKNOWN_MIGRATION_REQUIRED` for physical
> authority, W12 is `CONTRACTED_NOT_IMPLEMENTED` on main, and PR #66 is
> `CANDIDATE_ONLY` evidence. PR #75 has substantive candidate counterevidence
> but no proven preregistered procedural independence.

## 1. 收敛后的系统

系统保持四个平面和十三个工作流，不创建 W14：

```text
治理控制 W1/W8/W9
        ↓
事实证据 W2/W3/W5/W13
        ↓
研究模型 W4/W6/W12
        ↓
决策生存 W10/W11/W7 + embedded 0017/0018
        ↓
W9 outcome calibration -> next versioned research cycle
```

逻辑写权威按 bounded context 唯一；物理类名或数据库存在不自动取得权威。0017 嵌入 W4/W7，0018 嵌入 W7/W9/W11。

## 2. 唯一写权威

| 对象域 | 写权威 | 当前实现现实 |
|---|---|---|
| AMED、任务和索引 | W1 | 治理已实现，待本 PR 验收 |
| Agent 运行与交接 | W8 | 部分实现 |
| 市场时间、规则和回放 | W2 | P1/P2/P3 部分实现 |
| 来源、证据、知识和记忆 | W3 | 逻辑权威已冻；本地/公开物理迁移 UNKNOWN |
| 事件政策证据 | W5 | 合同未实现 |
| 参与者资金证据 | W13 | 合同未实现，不拥有真实身份裁决 |
| 特征策略和实验族 | W4 | 局部候选 |
| 竞争性参与者假设 | W6 | 蓝图级，不是身份事实 |
| `ProbabilityEstimate` | W12/DS-02 | PR #66 Draft 候选，尚不在 main |
| `DecisionEpisode` | W10 | 合同未实现 |
| `W11CandidateAllocation` | W11 | 合同未实现，上游阻断 |
| `ValidationReport/W7RiskEnvelope` | W7 | 部分实现，最终否决唯一 |
| `OutcomeCalibrationRecord` | W9 | 治理部分，canonical runtime 未实现 |

机器权威和接口入口为 `coordination/GOVERNANCE/ENTERPRISE-BLUEPRINT-AUTHORITY-AND-INTERFACE-REGISTRY-v1.1.yaml`。

## 3. 共享接口和成熟度

十一项接口继续采用 C1-C11。每项必须保留 producer、consumer、版本、证据、成熟度和 UNKNOWN。当前没有一项可声称完成所有消费者兼容性验证；下游不得用默认值补造缺失语义。

成熟度凭证据升级：蓝图、Skill、单元测试、合成回放、A 股样本外和影子对账是不同等级。当前 `A_SHARE_BACKTESTED`、`SHADOW_VALIDATED`、`VALIDATED_RESEARCH_CAPABILITY` 和 `LIVE_TRADING` 数量均为零。

## 4. 物理记忆权威的未决事项

W3 只有一个逻辑 owner，但可访问本地 `brain_core` 与公开 Phase 3 各有存储实现。Issue #72 不删除、不覆盖、不迁移。后续必须先完成：

1. 对象和版本清单；
2. 不可覆盖快照；
3. 双向或单向映射；
4. dry-run 数量与内容哈希对账；
5. 查询等价和冲突/UNKNOWN 保留测试；
6. 回滚演练；
7. GPT 系统记录源决策。

P2 和 adapter 内存网关只作为测试 facade。

## 5. 依赖关键路径

资本路径仍被 `ProbabilityEstimate -> DecisionEpisode/W7RiskEnvelope -> W11CandidateAllocation -> 0018 -> W9 calibration` 阻断。W13 和 PMN 仍需 point-in-time 来源与字段证据。

第一条可独立证伪的业务路径为：

```text
Issue #72 GPT acceptance
→ Issue #73 independent audit or explicit waiver
→ W2 bar/time/rule/replay
→ W4 experiment ownership
→ W7 validation
→ 0017 BAR_ONLY breach/reclaim/T+1 slice
```

## 6. 唯一下一切片

推荐且只推荐 `0017 BAR_ONLY reference-zone breach/reclaim plus T+1 validation`。这是一项候选选择，不是启动授权。

它只能基于当时可得 bar 定义可观察参考区，保存穿越、收复失败、延续和稳定化结果；不得声称看见隐藏止损、主力身份、逐笔订单或操纵意图。验证必须含简单基线、成本、T+1、涨跌停/停牌、不可执行退出、purge/walk-forward、多时期/制度和样本外门。

## 7. WIP 和并行

- Codex 一个活动任务，首批业务切片最多一个；
- QCLAW 独立审计使用不同分支和文件，不编辑 Codex authority artifacts；
- 同一上游接口冻结前不并行实现多个消费者；
- W13、PMN、W12 child、W11 和 0018 本轮均不激活；
- 本地只读证据可并行，但不得写相同目录或改变运行服务。

## 8. 完成和回滚

本候选蓝图只有在 PR #74 测试通过、Issue #73 反方审计完成或被 GPT 明确豁免、并通过 GPT AMED 七门后才能替代 v1.0。回滚方式是撤销 PR #74；v1.0 和既有运行时保持完整。
