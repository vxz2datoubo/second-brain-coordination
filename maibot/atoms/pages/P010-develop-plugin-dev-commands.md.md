---
id: P010
type: source-page
title: "Command 组件"
source: "https://docs.mai-mai.org/develop/plugin-dev/commands.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Command 组件

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/commands.md](https://docs.mai-mai.org/develop/plugin-dev/commands.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@Command` 是基于正则匹配的命令组件。当用户发送的消息匹配到某个 Command 的正则模式时，MaiBot 会调度执行对应的 Command 处理函数。
* **`name`** `str` — 命令名称，需在插件内唯一
* **`description`** `str` — 命令描述
* **`pattern`** `str` — 正则匹配模式字符串。当用户消息匹配此模式时，触发该命令
* **`aliases`** `list[str] | None` — 命令别名列表，提供额外的触发方式
使用 `/greet`、`/hi` 或 `/hey` 均可触发此命令。
Command 处理函数接收 `**kwargs`，其中包含以下参数：
* **`stream_id`** `str` — 当前聊天流 ID，用于发送消息
* **`matched_groups`** `dict` — 正则命名捕获组的匹配结果
* **`raw_message`** `str` — 用户发送的原始消息文本
* **`message`** `dict` — 完整的消息对象
Command 处理函数必须返回三元组：
* **`succes

## 快速要点
- **`name`** `str` — 命令名称，需在插件内唯一
- **`description`** `str` — 命令描述
- **`pattern`** `str` — 正则匹配模式字符串。当用户消息匹配此模式时，触发该命令
- **`aliases`** `list[str] | None` — 命令别名列表，提供额外的触发方式
- **`stream_id`** `str` — 当前聊天流 ID，用于发送消息
- **`matched_groups`** `dict` — 正则命名捕获组的匹配结果
- **`raw_message`** `str` — 用户发送的原始消息文本
- **`message`** `dict` — 完整的消息对象

## 标题树
- Command 组件
  - 装饰器签名
    - 参数说明
  - 基本用法
    - 带别名的命令
    - 带正则捕获组的命令
  - 处理函数参数
    - 返回值
- 命令成功执行
- 命令执行失败
  - 正则模式编写指南
    - 推荐模式
- 精确匹配 /hello
- 匹配 /hello 加可选参数
- 匹配 /echo 加必填参数
- 匹配 /set 加键值对
    - 使用命名捕获组
  - 命令执行流程
  - 命令相关 Hook
  - 完整示例
