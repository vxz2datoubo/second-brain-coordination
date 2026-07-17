
# 消息管线

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/message-pipeline.md](https://docs.mai-mai.org/develop/architecture/message-pipeline.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 的消息处理管线是从入站接收到出站发送的完整链路。本文详述管线各阶段的内部机制、数据结构和 Hook 拦截点。
源码位置：`src/chat/message_receive/bot.py`
消息通过 maim-message `MessageServer` 到达后，调用 `ChatBot.message_process(message_data)` 进入主链路：
源码位置：`src/chat/message_receive/message.py`
`SessionMessage` 继承自 `MaiMessage`，是管线中流转的核心消息对象：
* **`message_id`** `str` — 消息唯一 ID
* **`platform`** `str` — 来源平台标识
* **`session_id`** `str` — 会话 ID（由 `SessionUtils.calculate_session_id()` 计算）
* **`processed_plain_text`** `str` — 经过预处理的纯文本
* **`message_info`** `MessageInfo` — 包含 `user_in

## 快速要点
- **`message_id`** `str` — 消息唯一 ID
- **`platform`** `str` — 来源平台标识
- **`session_id`** `str` — 会话 ID（由 `SessionUtils.calculate_session_id()` 计算）
- **`processed_plain_text`** `str` — 经过预处理的纯文本
- **`message_info`** `MessageInfo` — 包含 `user_info`、`group_info`、`additional_config`
- **`raw_message`** `MessageSequence` — 原始消息组件序列
- **`is_at`** `bool` — 是否 @ 了 bot
- **`is_mentioned`** `bool` — 是否提及了 bot

## 标题树
- 消息管线
  - 整体流程
  - 消息入站与反序列化
    - 入口：`ChatBot.message_process()`
    - `SessionMessage` 结构
    - `SessionMessage.process()` 预处理
  - Hook 拦截链
    - chat.receive.before\_process
    - chat.receive.after\_process
    - chat.command.before\_execute
    - chat.command.after\_execute
    - send\_service.after\_build\_message
    - send\_service.before\_send
    - send\_service.after\_send
  - 消息过滤
  - 会话管理
    - ChatManager
    - Session ID 计算
    - BotChatSession
  - 命令处理
  - HeartFlow 心流处理
    - HeartFCMessageReceiver
    - HeartflowManager
  - 出站发送
  - 内置 Hook 汇总
  - 数据流图


---
*来源: https://docs.mai-mai.org/develop/architecture/message-pipeline.md*
