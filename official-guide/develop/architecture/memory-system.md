
# 记忆系统（A-Memorix）

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/memory-system.md](https://docs.mai-mai.org/develop/architecture/memory-system.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
A-Memorix 是 MaiBot 内置的长期记忆子系统，负责持久化用户偏好、对话记忆和人物画像等数据。本文详述其架构、存储机制和检索流程。
源码位置：`src/A_memorix/core/runtime/sdk_memory_kernel.py`
`SDKMemoryKernel` 是 A-Memorix 的核心运行时，初始化时加载配置并构建所有存储和检索组件。
检索请求的数据结构：
* **`query`** `str` · 默认为空 — 查询文本
* **`limit`** `int` · 默认 `5` — 返回条数
* **`mode`** `str` · 默认 `"search"` — 检索模式
* **`chat_id`** `str` · 默认为空 — 聊天流 ID
* **`person_id`** `str` · 默认为空 — 人物 ID
* **`time_start`** `Optional[str|float]` · 默认 `None` — 起始时间
* **`time_end`** `Optional[str|float]` · 默认 `None` — 结束时间
* **`respect_fil

## 快速要点
- **`query`** `str` · 默认为空 — 查询文本
- **`limit`** `int` · 默认 `5` — 返回条数
- **`mode`** `str` · 默认 `"search"` — 检索模式
- **`chat_id`** `str` · 默认为空 — 聊天流 ID
- **`person_id`** `str` · 默认为空 — 人物 ID
- **`time_start`** `Optional[str|float]` · 默认 `None` — 起始时间
- **`time_end`** `Optional[str|float]` · 默认 `None` — 结束时间
- **`respect_filter`** `bool` · 默认开启 — 是否应用聊天过滤配置

## 标题树
- 记忆系统（A-Memorix）
  - 架构总览
  - SDKMemoryKernel
    - 初始化流程
    - KernelSearchRequest
    - 检索模式
  - AMemorixHostService
    - invoke 调用入口
    - 配置管理
  - 存储层
    - VectorStore
    - GraphStore
    - MetadataStore
    - knowledge\_types.py
  - 检索层
    - 双路检索架构
    - 关键组件
    - RetrivalResult
  - 策略层
  - 辅助服务
    - EpisodeService
    - PersonProfileService
    - RelationWriteService
    - AggregateQueryService
    - ImportTaskManager
  - 基础工具接口
    - search\_memory
    - ingest\_summary
    - ingest\_text
    - get\_person\_profile
    - maintain\_memory
  - 管理工具接口
  - 与 MaiBot 的集成
    - 插件模式（Legacy）
    - 配置
  - 元数据版本
  - 删除语义（source 模式）


---
*来源: https://docs.mai-mai.org/develop/architecture/memory-system.md*
