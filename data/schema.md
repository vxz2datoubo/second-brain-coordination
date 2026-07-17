# 第二大脑 Schema 约束文件
# 灵感来源: Karpathy LLM Wiki 的 CLAUDE.md 模式
# LLM agent 读取此文件后知道如何维护这个知识库
# 此文件由你和 AI 共同迭代，越用越精确

## 系统概述
- 第二大脑是一个本地个人知识库，数据以 JSON 存储，通过 HTTP API + SPA 前端操作
- 端口: 8766
- 核心模块: graph.py(知识图谱) / digest.py(知识消化) / tfidf.py(检索) / syncer.py(同步) / memory.py(记忆) / evolve.py(进化)

## 知识节点规范
- 每个知识节点包含: id, title, content, summary, source, tags, category, importance(1-5)
- 分类: tech-programming(编程) / tech-ai(AI) / design(设计) / business(商业) / film-video(影视) / life(生活) / academic(学术)
- 来源标记: manual(手动输入) / workbuddy-session(会话同步) / workbuddy-memory(记忆同步) / file(文件导入) / url(网页导入) / demo(演示数据)
- 标签: 自动从内容提取8个关键词 + 手动补充
- 摘要: 自动生成首句截取(80字内)

## 工作流程
1. **Ingest 摄入**: 用户粘贴文本 → 自动分词/分类/标签/摘要 → 存入知识图谱 + 自动关联
2. **Query 查询**: 用户搜索 → TF-IDF检索 + 标签加权 + 图谱扩展 → 返回排序结果
3. **Sync 同步**: 扫描 WorkBuddy 会话 → 提取用户消息 → 拆分话题 → 摄入知识图谱
4. **Evolve 进化**: 评估系统状态 → 生成洞察 → 识别失败案例 → 应用优化规则
5. **Lint 检查**: 定期扫描 → 孤立节点/矛盾标签/过期内容 → 生成修复建议

## 优化规则
- 当某个分类连续5次差评 → 检查该分类关键词是否准确
- 当图谱关联密度 < 0.2 → 建议运行全局 auto_link
- 当节点数 > 100 → 建议启用 SQLite 存储 (v2)
- 当搜索命中率 < 30% → 检查 Bigram 分词是否需要升级 jieba

## 文件结构
```
data/
├── knowledge-graph.json   # 知识图谱: nodes + edges
├── memory-index.json      # 记忆索引: 交互记录
├── feedback-log.json      # 反馈日志
├── evolution-log.json     # 进化日志
├── errors-log.json        # 错误日志
├── category-index.json    # 分类配置
├── user-profile.json      # 用户画像
├── sync-state.json        # 同步状态
└── schema.md              # 本文件 ← Schema 约束
```

## 每日检查清单 (Lint)
运行 `POST /api/evolve/evaluate` 后检查:
- [ ] 是否有孤立节点（入度=0 且 出度=0）？
- [ ] 是否有关键词与分类不匹配的节点？
- [ ] 是否有超过30天未更新的节点？
- [ ] 知识图谱关联密度是否 > 0.2？
- [ ] 搜索索引是否与图谱同步？
