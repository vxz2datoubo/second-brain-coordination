你是一个知识库架构师。请分析并优化第二大脑知识库。

## 背景
知识库文件: F:/ai/data/knowledge-graph.json
审计数据: F:/ai/qclaw-output/brain-audit.json
产出目录: F:/ai/qclaw-output/

## 已知问题（来自审计）
1. 全孤立节点：190个节点全部孤立，但edges有7694条
2. 标签污染：热门标签是单字如"话""录""0""f"
3. 重复节点：多个"WorkBuddy 跨项目记忆"标题重复
4. 分类失衡：tech-programming占46%，design/academic/inbox几乎空
5. content字段包含大量WorkBuddy会话日志，噪音多

## 任务

### 阶段1：诊断
1. 读取 knowledge-graph.json，检查edges的source/target是否匹配node的id
2. 检查tags字段的真实数据格式
3. 找出重复节点（按title去重）
4. 统计content字段的长度分布

### 阶段2：修复
修改 knowledge-graph.json（先备份为 knowledge-graph-backup-{timestamp}.json）：

1. 边连接修复：检查edges的source/target是否应匹配nodes的key。如果匹配规则不对，修正它
2. 标签清洗：移除content中提取的噪音单字标签，保留语义标签
3. 重复节点合并：同标题节点合并内容
4. 分类调整：把明显放错分类的节点重新归类

### 输出
1. 打印每个阶段的详细发现
2. 保存修复后的 knowledge-graph.json
3. 生成修复报告 qclaw-output/brain-fix-report.md
