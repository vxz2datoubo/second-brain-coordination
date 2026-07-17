---
id: P007
type: source-page
title: "API 参考"
source: "https://docs.mai-mai.org/develop/plugin-dev/api-reference.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# API 参考

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/api-reference.md](https://docs.mai-mai.org/develop/plugin-dev/api-reference.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 插件通过 `self.ctx`（`PluginContext`）访问 16 种能力代理。所有调用自动通过 RPC 转发到 Host 处理，SDK 会自动解包结果。
此外，`self.ctx.logger` 提供标准 `logging.Logger` 实例，不属于能力代理体系。详见下方的 [logger](#logger) 章节。
* `await send.text(text, stream_id)` — 发送文本消息
* `await send.image(image_data, stream_id)` — 发送图片
* `await send.emoji(emoji_data, stream_id)` — 发送表情
* `await send.command(command, stream_id)` — 发送指令消息
* `await send.forward(messages, stream_id)` — 发送转发消息
* `await send.hybrid(segments, stream_id)` — 发送图文混合消息
* `await send.custom(custom_type, data,

## 快速要点
- `await send.text(text, stream_id)` — 发送文本消息
- `await send.image(image_data, stream_id)` — 发送图片
- `await send.emoji(emoji_data, stream_id)` — 发送表情
- `await send.command(command, stream_id)` — 发送指令消息
- `await send.forward(messages, stream_id)` — 发送转发消息
- `await send.hybrid(segments, stream_id)` — 发送图文混合消息
- `await send.custom(custom_type, data, stream_id)` — 发送自定义类型消息
- `await db.query(model_name, query_type="get", data=None, filters=None, order_by=None, limit=None, single_result=False)` — 通用数据库操作

## 标题树
- API 参考
  - send — 消息发送
- 发送文本
- 发送图片（base64）
- 图文混合
  - db — 数据库操作
- 查询
- 获取单条记录
- 插入
- 更新
- 删除
- 计数
  - llm — LLM 调用
- 简单文本生成
- 用消息列表格式
- 带工具调用
- 单条文本嵌入
- 批量文本嵌入
- ASR 语音识别
- 获取可用模型列表
  - config — 配置读取
- 读取单个值
- 读取指定插件配置
- 读取全部配置
  - message — 历史消息
- 方式 1：传入已查询的消息列表
- 按消息 ID 查询
- 方式 2：通过关键字参数传入 chat_id + 时间范围，由 Host 端查询
  - chat — 聊天流
- 获取所有群聊流
- 获取私聊聊天流
- 按 Group ID 获取聊天流
- 按用户 ID 获取聊天流
- 打开或创建私聊聊天流
- 打开或创建群聊聊天流
  - maisaka — Maisaka 主动任务
- 请求 Maisaka 基于指定聊天流主动处理一轮对话
- 向指定聊天流追加一条插件上下文消息
  - person — 用户信息
- 获取 person_id
- 获取昵称
  - emoji — 表情包管理
  - frequency — 发言频率
  - component — 插件与组件管理
  - api — 跨插件 API
- 调用其他插件公开的 API
- 查询可见 API
  - gateway — 消息网关
  - tool — 工具定义
  - render — HTML 渲染
  - knowledge — 知识库搜索
  - logger — 日志
- 方式一：通过 ctx.logger（名称自动为 plugin.<plugin_id>）
- 方式二：直接用 stdlib logging（同样会被自动传输）
