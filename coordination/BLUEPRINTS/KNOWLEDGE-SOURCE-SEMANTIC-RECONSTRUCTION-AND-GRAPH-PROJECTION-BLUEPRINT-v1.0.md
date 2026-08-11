# 第二大脑 W3 原始资料语义重建与知识图谱投影蓝图 v1.0

> `owner: GPT`
>
> `workstream: W3 Knowledge Authority and Long-Term Memory`
>
> `implementation_issue: #216`
>
> `implementation_agent: QCLAW`
>
> `boundary: CANDIDATE_ONLY / PUBLIC_SAFE / NO_TRADE`

## 一、定位

本蓝图把用户真实资料入口扩展为一条可审计、可追溯的四层知识链：

```text
L0 RawSourceSnapshot（原始证据，不可改写）
→ L1 NormalizedSemanticView（语义重建派生视图）
→ L2 CandidateKnowledgeAtoms（E47 已验收原子化模式）
→ L3 KnowledgeGraphProjection（图谱派生投影）
```

它属于现有 W3，不创建第二套知识权威。L1 与 L3 都是可重建投影，不能覆盖 L0 原始证据，也不能取代 W3 的正式知识/证据/长期记忆系统记录源。

正式 PROJECT/GLOBAL 写入仍受 Codex E61 与 `GPT_ACCEPTED_REAL_PRODUCTION_DURABLE_AUTHORITY_BINDING` 门禁约束。

## 二、真实输入场景

目标输入包括但不限于：

- 抖音/短视频口播与字幕；
- ASR 语音转写；
- OCR 文本；
- 论坛、聊天、口语笔记；
- 专业知识博主文案；
- 断句不完整、错别字、同音误识、口头赘词、指代不清和术语不统一的中文文本。

系统不得把“表达噪声”直接固化成知识，也不得为了“写得顺”而静默改写证据。

## 三、L0 原始证据层

L0 必须：

1. 保存原始文本/字节身份与 SHA-256；
2. 保留精确 source span；
3. 永不被规范化文本覆盖；
4. 作为最终证据回溯锚点；
5. 私人资料默认只在本地/私有上下文处理，不因实现测试上传公开仓库。

## 四、L1 语义重建层

### 4.1 允许处理

- 断句与标点修复；
- 口头填充词与无意义重复清理；
- 明显错别字修正；
- ASR/同音识别修正；
- 术语标准化与别名映射；
- 有证据支持的指代恢复；
- 语义分段；
- 歧义候选生成；
- 不确定项进入 UNKNOWN。

### 4.2 每次修改必须可审计

每个规范化片段至少记录：

- 原始 span；
- before / after；
- edit_type；
- confidence；
- rationale category；
- alternatives（如存在）；
- unresolved/UNKNOWN 状态。

### 4.3 禁止事项

- 不得把低置信度猜测静默写成事实；
- 不得修改 L0；
- 不得用 L1 替换 SOURCE_EXTRACT 的证据身份；
- 不得为了完整度强制消除歧义；
- 不得把博主观点自动升级为已验证事实。

## 五、L2 原子化层

L2 继承 E47 已验收规则：

- 概念、定义、机制、因果链、条件、反例、指标、数据源、适用范围、失效条件、验证方法、可执行动作；
- SOURCE_EXTRACT / USER_CLAIM / EXTERNAL_CLAIM / INFERENCE / VALUE_JUDGMENT 分离；
- 推断置信度校准；
- 真矛盾才记录矛盾；
- 真知识缺口才生成 UNKNOWN；
- 候选记忆/技能必须有证据；
- 禁止用数量配额 Goodhart 化知识质量。

即使 L2 的理解使用 L1，证据链仍必须可回溯到 L0 原始 span。

## 六、L3 知识图谱投影层

L3 是派生视图，不是权威数据库。

### 6.1 节点

可包含：

- source/document；
- normalized segment；
- knowledge atom；
- UNKNOWN；
- candidate memory；
- candidate skill。

### 6.2 关系

至少复用 E47：

- SUPPORTS；
- DEPENDS_ON；
- REFINES；
- CONTRADICTS；
- RAISES_UNKNOWN；
- VERIFIED_BY。

并允许派生 provenance/normalization links，例如 atom → normalized segment → raw source span。

任何图边必须来自真实语义关系或明确 provenance，不得为了视觉密度“补线”。

## 七、用户可视化目标

首版应提供本地可打开的神经元/脑网络式 force-directed graph 或等价交互图。

最低交互：

- 搜索节点；
- 按 atom type / relation type / evidence kind / confidence / source 过滤；
- 点击节点查看内容、置信度、证据类型、来源、原始/规范化上下文；
- UNKNOWN 与 CONTRADICTS 明显区分；
- 支持图数据导出。

应优先复用现有前端/图组件。若需新依赖，先比较至少两种低维护、可回滚方案，并基于官方文档选择。

## 八、数据合同建议

允许根据 E47 复用审计后适配命名，但不得建立平行 canonical：

- `NormalizedSemanticView`
- `NormalizedSegment`
- `NormalizationEdit`
- `AmbiguityCandidate`
- `TerminologyAlias`
- `KnowledgeGraphProjection`

建议输出 library-neutral JSON，并在低成本情况下增加 GraphML 或其他可互操作格式。

## 九、质量门

1. L0 hash/bytes 不因规范化改变；
2. L1 每个 segment 有真实 L0 span；
3. 所有文本修改有 edit record；
4. 不确定修正保留 alternatives/UNKNOWN；
5. L2 证据仍锚定 L0；
6. 图节点/边数量从真实列表派生；
7. 所有 edge endpoint 有效；
8. 允许零矛盾、稀疏图；
9. 不以最小节点/关系/修改数量作为质量门；
10. 公共测试只用 PUBLIC_SAFE 合成噪声语料；
11. 私人用户资料不因测试进入公开仓库；
12. 资源遵循 FOREGROUND_PRIORITY 与进程回收规则。

## 十、系统接口与权威

```text
输入：USER_SELECTED / GPT_SELECTED raw source
写权威：W3
L0：证据源
L1：派生语义视图
L2：候选知识包
L3：派生图谱投影
正式写入：E61 gate 后的受控认证路径
```

图谱 UI、缓存、Supabase 或其他投影均可从 W3 权威重建，不得反向成为系统记录源。

## 十一、实施与验收

实现任务：Issue #216 / QCLAW E48。

验收必须由 GPT 独立检查：

- 原始证据是否真正不可变；
- 规范化是否可追溯且不脑补；
- E47 证据语义是否保持；
- 图谱是否只投影真实关系；
- UI 是否能回溯原始证据；
- 是否引入重复 schema/runtime；
- 是否存在隐私、资源或依赖扩张。

完成信号：

`QCLAW_E48_SEMANTIC_RECONSTRUCTION_AND_KNOWLEDGE_GRAPH_READY_FOR_GPT_REVIEW`
