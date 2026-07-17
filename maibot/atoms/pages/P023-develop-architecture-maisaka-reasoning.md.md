---
id: P023
type: source-page
title: "Maisaka 推理引擎"
source: "https://docs.mai-mai.org/develop/architecture/maisaka-reasoning.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Maisaka 推理引擎

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/maisaka-reasoning.md](https://docs.mai-mai.org/develop/architecture/maisaka-reasoning.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
Maisaka 是 MaiBot 的核心 AI 运行时，负责对话推理、节奏控制和工具调用。本文详述其内部架构、状态机和执行流程。
源码位置：`src/maisaka/runtime.py`
每个聊天会话对应一个 `MaisakaHeartFlowChatting` 实例，由 `HeartflowManager` 管理生命周期。
运行时具有三种状态：
* **`running`** — 正在执行推理循环
* **`wait`** — 等待状态，wait 工具设定了超时时间
* **`stop`** — 空闲状态，等待新的外部消息触发
* **`session_id`** `str` — 会话 ID
* **`_chat_history`** `list[LLMContextMessage]` — 内部上下文历史
* **`message_cache`** `list[SessionMessage]` — 待处理消息缓存
* **`_internal_turn_queue`** `asyncio.Queue` — 内部循环触发队列（"message" / "timeout"）
* **`_tool_registry`** `To

## 快速要点
- **`running`** — 正在执行推理循环
- **`wait`** — 等待状态，wait 工具设定了超时时间
- **`stop`** — 空闲状态，等待新的外部消息触发
- **`session_id`** `str` — 会话 ID
- **`_chat_history`** `list[LLMContextMessage]` — 内部上下文历史
- **`message_cache`** `list[SessionMessage]` — 待处理消息缓存
- **`_internal_turn_queue`** `asyncio.Queue` — 内部循环触发队列（"message" / "timeout"）
- **`_tool_registry`** `ToolRegistry` — 统一工具注册表

## 标题树
- Maisaka 推理引擎
  - 架构总览
  - MaisakaHeartFlowChatting
    - 状态机
    - 核心属性
    - 消息触发机制
    - 强制 continue 机制
  - MaisakaReasoningEngine
    - 关键常量
    - run\_loop 主循环
    - Timing Gate
    - Planner（Action Loop）
    - Planner 打断机制
    - 工具执行
  - 内置工具定义
    - Timing Gate 工具
    - Action 工具
    - Deferred Tool 发现机制
  - ChatLoopService
    - chat\_loop\_step 流程
    - 上下文选择策略
    - Hook Specs
  - 上下文消息类型
    - ReferenceMessageType
    - 上下文窗口占用
  - Planner 消息前缀
  - 监控事件
  - 完整推理流程示例
