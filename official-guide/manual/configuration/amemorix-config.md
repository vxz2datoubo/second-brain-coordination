
# A\_Memorix 记忆系统配置

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration/amemorix-config.md](https://docs.mai-mai.org/manual/configuration/amemorix-config.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
A\_Memorix 是 MaiBot 的长期记忆系统，负责记忆的存储、向量化、检索、人物画像、记忆演化和 Web 运维。它替代了旧版 `[memory]` 配置段落，提供了更细粒度的控制。
本文详细介绍如何在 `bot_config.toml` 中配置 `[a_memorix]` 段落。
如果你还不熟悉记忆系统是什么，建议先阅读 [记忆系统功能介绍](../features/memory-system.md)，了解它能做什么。
A\_Memorix 配置位于 `bot_config.toml` 的 `[a_memorix]` 段落下，包含 12 个子段落。TOML 段名区分大小写，请使用小写 `a_memorix`：
旧资料或旧版独立配置文件中可能出现 `A_memorix` 或 `config/a_memorix.toml`。当前 MaiBot 主配置以 `config/bot_config.toml` 中的 `[a_memorix]` 为准；旧版 `config/a_memorix.toml` 仅作为兼容迁移来源。
控制麦麦在聊天中如何使用长期记忆。包括记忆检索工具、人物画像查询/注入、聊天摘要写回和反馈纠错。
* *

## 快速要点
- **`enable_memory_query_tool`** — 是否允许麦麦在聊天时查询长期记忆。默认开启
- **`memory_query_default_limit`** — 每次默认从长期记忆中取回多少条结果，范围 `1-20`。默认 5
- **`enable_person_profile_query_tool`** — 是否允许麦麦查询人物画像记忆。默认开启
- **`enable_person_profile_injection`** — 是否在 Maisaka Planner 调用前自动注入当前对象相关的人物画像。默认开启
- **`person_profile_injection_max_profiles`** — 每轮自动注入的人物画像数量上限，范围 `1-5`。默认 3
- **`person_fact_writeback_enabled`** — 是否在发送回复后自动提取并写回人物事实到长期记忆。默认开启
- **`chat_summary_writeback_enabled`** — 是否在 Maisaka 聊天过程中按消息窗口自动写回聊天摘要到长期记忆。默认开启
- **`chat_summary_writeback_message_threshold`** — 自动写回聊天摘要的消息窗口阈值（高级）。默认 36

## 标题树
- A\_Memorix 记忆系统配置
  - 配置结构总览
  - 记忆集成 \[a\_memorix.integration]
    - 基础集成
    - 反馈纠错
  - 记忆系统 \[a\_memorix.plugin]
  - 存储 \[a\_memorix.storage]
  - 记忆向量化 \[a\_memorix.embedding]
    - 基础配置
    - Embedding 回退 \[a\_memorix.embedding.fallback]
    - 段落向量回填 \[a\_memorix.embedding.paragraph\_vector\_backfill]
  - 检索 \[a\_memorix.retrieval]
    - 基础检索配置
    - 稀疏检索 \[a\_memorix.retrieval.sparse]
  - 阈值过滤 \[a\_memorix.threshold]
  - 聊天过滤 \[a\_memorix.filter]
  - Episode \[a\_memorix.episode]
  - 人物画像 \[a\_memorix.person\_profile]
  - 记忆演化 \[a\_memorix.memory]
  - 高级运行时 \[a\_memorix.advanced]
  - Web 运维 \[a\_memorix.web]
    - 导入中心 \[a\_memorix.web.import]
    - 调优中心 \[A\_memorix.web.tuning]
  - 从旧版 \[memory] 迁移
    - 字段映射
    - 默认值变更
    - 迁移示例
  - 配置示例
    - 最小配置
    - 推荐日常配置
    - 高级配置
  - 常见问题
    - Q: 启用记忆系统后检索不到内容？
    - Q: 向量化失败怎么排查？
    - Q: 反馈纠错应该开启吗？
    - Q: 人物画像是怎么工作的？
    - Q: 记忆演化会影响已有的记忆吗？
    - Q: 稀疏检索模式怎么选？
  - 下一步


---
*来源: https://docs.mai-mai.org/manual/configuration/amemorix-config.md*
