# QClaw 输出 | 2026-06-15 23:30
> 模型: openclaw/default | Token: 0

## Inbox 117节点消化方案

### 1. 25个有价值节点的结构化拆分
- **project-memory日报**：每条决策/洞察拆为独立原子节点，打上 `decision` / `insight` / `action-item` 标签，保留原始日期来源引用
- **conversation摘录**：按主题聚类（技术决策、业务方向、问题诊断），相同主题的摘录合并为一个 `conversation-summary` 节点
- 拆分后预估产出约80-120个独立知识节点，用JSON/YAML格式存储，字段：`id, type, title, content, date, source, tags, related[]`

### 2. 92个低价值节点处理策略
- **workbuddy-session原始同步**属于过程日志，价值极低，建议直接**归档压缩**（打包为一个 `archive-workbuddy-2026Q1.md`）后删除原节点
- 归档前做一次关键词扫描，若某条碰巧包含关键决策/报错修复记录，则提升为有价值节点进入步骤1
- 删除92个节点时保留一条 `archived: 92 workbuddy-sessions → archive-workbuddy-2026Q1.md` 的索引记录，方便回溯

### 3. 交叉引用建立方案
- **自动关联**：新节点生成后，按 `tags` + 关键词匹配现有分类（film-video / decision-lessons / business），双向写入 `related[]` 数组
- **人工确认层**：匹配度低于阈值的挂入 `inbox/uncategorized` 队列，待迪迪手动归类
- **分类节点更新**：每批消化完成后，更新对应分类索引页的 `children[]` 和统计计数，保持可浏览结构

### 4. 批量处理执行步骤
1. **导出清单** → 拉取117节点列表，标记类型（project-memory / conversation / workbuddy-session），生成 `inbox-117-inventory.csv`
2. **低价值分离** → 92条 workbuddy 扫描关键词 → 批量归档 → 删除原节点，保留1条索引记录
3. **高价值拆分** → 25条逐条读取 → LLM辅助提取决策/洞察 → 生成80-120个原子节点JSON，写入第二大脑API
4. **交叉引用** → 运行关联脚本匹配 tags → 更新分类索引 → 生成 `digestion-report.md` 汇总本批消化结果

---

[SAVE: inbox消化方案.md]