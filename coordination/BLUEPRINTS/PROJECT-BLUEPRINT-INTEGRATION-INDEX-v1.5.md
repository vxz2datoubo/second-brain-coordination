# 第二大脑与A股交易研究项目蓝图集成索引 v1.5

> agent_id: `CODEX`
>
> supersedes: `PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.4.md`
>
> governance_task: `#72`
>
> status: `CODEX_VERIFIED_CANDIDATE_PENDING_GPT`
>
> boundary: `research_only / NO_TRADE`

## 权威入口

1. 企业章程：`coordination/BLUEPRINTS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.4.md`
2. 收敛蓝图：`coordination/BLUEPRINTS/ENTERPRISE-BLUEPRINT-CONVERGENCE-AND-DEPENDENCY-MAP-v1.1.md`
3. 机器权威：`coordination/GOVERNANCE/ENTERPRISE-BLUEPRINT-AUTHORITY-AND-INTERFACE-REGISTRY-v1.1.yaml`
4. 证据包：`coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/ENTERPRISE-BLUEPRINT-CONVERGENCE-0019A/`

## 收敛变化

- 保留 W1-W13，不创建 W14；
- 0017 归 W4/W7，0018 归 W7/W9/W11；
- 将逻辑写权威与物理系统记录源分开；
- 把本地 `brain_core` 与公开 Phase 3 的记忆迁移登记为 UNKNOWN，而不是静默选边；
- 将所有模块成熟度校准到可验证证据，当前没有 A 股回测、影子或生产级模块；
- 将 PR #64/#65/#8/#34 和测试 facade 给出明确保留、迁移或拒绝处置；
- 只选择 0017 BAR_ONLY 作为下一候选业务切片，不授权实施。

## 决策链

```text
W2/W3/W5/W13 facts and evidence
→ W4 experiments + W6 competing hypotheses
→ W12 ProbabilityEstimate
→ W10 DecisionEpisode
→ W11 candidate allocation
→ W7 final validation/veto
→ W9 outcome calibration
```

0017 可从 W2/W4 进入 W7 进行独立验证。0018 必须等待 W12/W11/W7/W9，不得成为上游。

## 共享合同

统一使用 C1-C11。详细字段、版本、成熟度和 UNKNOWN 见任务包 `SHARED-INTERFACE-REGISTRY.yaml`。任何消费者不得复制 producer 的写权威，也不得将 UNKNOWN 改成 False、0 或默认真值。

## 当前 WIP

- Codex：Issue #72 / Draft PR #74；
- QCLAW：PR #70 收口，之后按 GPT 路由执行 Issue #73 独立审计；
- 其他业务切片：未激活；
- 真实交易：禁止。

## 下一候选

唯一推荐：`0017 BAR_ONLY reference-zone breach/reclaim plus T+1 validation`。激活条件为 GPT 接受 Issue #72，并接受 Issue #73 审计或明确豁免。详细评分和 kill conditions 见任务包 `NEXT-VERTICAL-SLICE-SELECTION.md`。

## 验收

索引、活动序列、权威注册和任务包必须通过 YAML/JSON/UTF-8、引用、单写者、依赖无环、秘密扫描和 Git diff 检查。业务回测不属于 Issue #72。
