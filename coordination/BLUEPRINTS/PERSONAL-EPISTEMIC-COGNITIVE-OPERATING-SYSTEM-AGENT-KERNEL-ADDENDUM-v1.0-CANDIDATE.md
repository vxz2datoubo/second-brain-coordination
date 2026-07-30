# PEOS 0010 厂商中立 Agent 内核增量 v1.0 候选

> `target: PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-BLUEPRINT-v1.0.md`
>
> `proposal: VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROPOSAL-0011`
>
> `authority: CANDIDATE_DELTA_ONLY`
>
> `canonical_target_modified: false`

## 一、目的

本文件给出章节级集成增量。它不替换 PEOS 0010，也不复制其正文。
GPT 可以逐项接受、修改或拒绝。

## 二、总体架构增量

建议在 `TaskContextModel` 与输出之间加入：

```text
VendorNeutralAgentOperatingKernel
├─ AuthorityResolver
├─ IntentCompiler
├─ ContextAssembler
├─ DeliberationController
├─ CapabilityRouter
├─ ExecutionAndRecovery
└─ CompletionAuditor
```

该运行协议不是第六个世界模型。它不拥有事实、用户画像、概率、记忆或
交易权限，只协调五个核心模型和已有 W1/W3/W8/W10/Phase 3 接口。

## 三、数据与记忆增量

在 L0 到 L5 之间传播八条来源通道：

`USER_ASSERTED / USER_ADOPTED / TOOL_OBSERVED / INFERRED / HYPOTHESIS /
DECISION / OUTCOME / UNKNOWN`

建议映射：

| 通道 | 现有对象 |
|---|---|
| USER_ASSERTED | SourceRecord + EvidenceItem |
| USER_ADOPTED | DecisionEpisode + user model candidate |
| TOOL_OBSERVED | SourceRecord + EvidenceItem |
| INFERRED | KnowledgeAtom candidate + evidence links |
| HYPOTHESIS | ForecastRecord or research candidate |
| DECISION | DecisionRecord + DecisionEpisode |
| OUTCOME | ReviewRecord + OutcomeCalibrationRecord |
| UNKNOWN | UNKNOWN registry + ContextBundle |

## 四、个人认知合同增量

- 工具观察和用户陈述不得被模型推断覆盖；
- 模型推断必须携带反证、替代解释和失效条件；
- 用户采纳只证明选择，不证明建议中的全部理由；
- 用户纠正必须传播到 ContextBundle；
- 模型不得将“像用户”误当成“理解用户”；
- 关系记忆必须来源可追踪，不能伪造亲密或情感。

## 五、决策账本增量

建议 DecisionEpisode 关联：

- `AuthorityResolution`
- `TaskIntent`
- `ContextBundle.content_hash`
- `ToolRouteDecision`
- `ExecutionCheckpoint`
- `CompletionReceipt`
- `ModelBehaviorProfile` 版本

这些对象帮助回放一次判断如何产生，但不改变 W10 对 DecisionEpisode 的
唯一所有权。

## 六、推理与元认知增量

增加以下审计问题：

1. 结论是观察、推断还是假设；
2. 是否有厂商品牌或工具展示名影响选择；
3. 是否使用接收时间冒充来源时间；
4. 是否把同名字段误当成同义字段；
5. 是否重复执行已完成副作用；
6. 是否用窄测试证明宽结论；
7. 是否把自己的候选建议升级为 canonical；
8. 是否因用户同意而回填未经用户陈述的理由。

## 七、评测增量

建议加入：

- Vendor Preference Leakage Rate
- Provenance Lane Confusion Rate
- Inference-to-Observation Promotion Rate
- Unnecessary Verification Rate
- Duplicate Side Effect Rate
- Recovery State Drift
- Cross-Model Contract Equivalence
- Unowned Artifact Mutation Rate
- Requirement-Evidence Overclaim Rate
- Canonical Self-Promotion Attempt Rate

## 八、实施路线增量

在 PEOS C0 与 C1 之间加入候选 K 系列：

```text
K0 来源、权威和非重复审计
-> K1 合同、Schema 和参考解释器
-> K2 W3/Phase 3 记忆与 W8 能力适配
-> K3 恢复、回执和 Agent 交接
-> K4 跨模型一致性与突变评测
-> K5 GPT 验收和 feature flag 影子启用
```

## 九、根指令增量

GPT 验收后，Root `AGENTS.md` 只建议加入短指针：

```text
公共 Agent 运行语义由 PEOS 0010 的 Vendor-Neutral Agent Operating
Kernel Protocol 定义。模型、厂商和领域特有行为必须进入 Profile、
Adapter 或 Skill，不得写入公共权威内核。
```

不得把完整 Prompt 或蓝图复制进 `AGENTS.md`。

## 十、回滚

本增量是独立候选文件。拒绝或关闭 PR 即可完整回滚；现有 PEOS v1.0
没有被修改。
