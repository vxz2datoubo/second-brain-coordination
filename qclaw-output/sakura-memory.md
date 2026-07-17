# QClaw 输出 | 2026-06-15 23:56
> 模型: openclaw/default | Token: 0

三步方案已写入 `sakura-memory.md`：

**API链**：封装 MemoryBridge 层，对话后 POST `/api/digest/text` 写入摘要+标签，对话前 GET `/api/search` 检索 Top-5 注入 context。**检索策略**：BM25 粗排 Top-20 → 时间衰减加权（近期 1.5x / 7天外 0.3x）→ score>0.4 阈值过滤，每次 ≤5 条 ≤800 token。**人格存储**：SOUL.md 等以 `type:persona` 标签锁定存入，weight=MAX 永不过期，每会话启动强制检索 `tag:persona` 确保角色零漂移，SQLite 降级为离线缓存。

[SAVE: sakura-memory.md]