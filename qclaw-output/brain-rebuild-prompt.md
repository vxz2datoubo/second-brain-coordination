你是一位知识库架构师 + 认知科学家。目标是：把第二大脑知识库升级为"类人脑"的联想式知识网络，实现全方位思考不遗漏。

## 当前状态
- 知识库: F:/ai/data/knowledge-graph.json (95节点, 117边, 9个分类)
- 分类索引: F:/ai/data/category-index.json (分类定义和关键词)
- 修复报告: F:/ai/qclaw-output/brain-fix-report.md

## 任务

### 阶段1: 处理 inbox（16个节点）
1. 读取所有 `inbox` 分类的节点
2. 根据节点标题和内容，判断它们真正属于哪个分类
3. 把能归类的移到合适分类，留下确实无法归类的保持在 inbox
4. 对每个节点做内容总结提炼（精简内容到核心知识，去掉冗余日志）

### 阶段2: 重建标签索引系统
当前标签系统太弱。需要重新设计：

1. **多维度标签**：每个节点不只是打标签，而是从多个维度标记：
   - 领域（domain）：film-video / tech-ai / business / programming
   - 知识类型（type）：methodology / tool / case-study / lesson-learned / tutorial / concept
   - 关联实体（entity）：QClaw / Codex / PromptStudio / 小樱花
   - 复杂度（difficulty）：beginner / intermediate / advanced

2. **标签清洗增强**：
   - 保留现有语义标签（ai, 视频, 提示词, imax 等）
   - 自动从节点 content 提取新的语义关键词
   - 移除无意义的单字和噪音标签

3. **标签文件独立存储**：
   - 在 knowledge-graph.json 的每个节点中增加 `tags_v2` 字段，格式为：
   ```
   tags_v2: {
     "domain": ["film-video"],
     "type": ["methodology", "tutorial"],
     "entity": ["PromptStudio"],
     "difficulty": "intermediate",
     "keywords": ["提示词模板", "ComfyUI", "Shotlab"]
   }
   ```

### 阶段3: 增强知识关联（联想能力）
"类人脑"的关键是联想能力。需要做到：

1. **交叉关联**：对不同分类的节点之间建立 cross-category edges
   - 例如：一个 "提示词技术" 节点 → 连接 → "市场分析" 节点（因为提示词有商业价值）
   - 找出这些隐含关联，每条 edge 加上 relation 描述

2. **层次化思考维度**：确保知识库覆盖以下思考维度，如果一个维度缺失就标记出来：
   - 是什么（What）：事实、概念、定义
   - 为什么（Why）：原因、原理、动机
   - 怎么做（How）：方法、步骤、流程
   - 谁（Who）：人物、角色、责任
   - 何时（When）：时间线、时机
   - 哪里（Where）：场景、环境、领域
   - 多少钱（How much）：成本、规模、量化
   - 有什么影响（Impact）：后果、连锁反应
   - 和什么相关（Relation）：关联、对比、类比

3. **知识蒸馏**：对内容超过3000字的节点，提取摘要（summary字段），确保快速回忆

### 阶段4: 输出
1. 保存更新后的 knowledge-graph.json
2. 生成完整重构报告 qclaw-output/brain-rebuild-report.md，包含：
   - inbox处理详情
   - 标签系统V2说明
   - 新增的交叉关联
   - 思考维度覆盖分析（哪些维度已覆盖，哪些缺失）
   - 下一步建议
3. 生成一个 "思考检查清单" qclaw-output/thinking-checklist.md，列出知识库当前所有覆盖的思考维度，下次做决策时可以逐条对照

## 注意
- 先备份原文件
- 每次修改都验证 JSON 合法性
- 耗时会较长，请耐心执行完所有阶段
