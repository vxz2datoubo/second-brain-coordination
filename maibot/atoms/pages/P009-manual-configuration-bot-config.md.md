---
id: P009
type: source-page
title: "Bot 配置"
source: "https://docs.mai-mai.org/manual/configuration/bot-config.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Bot 配置

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration/bot-config.md](https://docs.mai-mai.org/manual/configuration/bot-config.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`bot_config.toml` 是 MaiBot 的主配置文件，包含机器人身份、人设、聊天行为、记忆、学习、表情、WebUI、MCP、插件等全部主设置。
配置文件由 MaiBot 自动生成和升级，不建议手动新增不存在的字段。
机器人身份信息，包含平台、账号、昵称等。
**`platform`** — 平台标识。**类型**：`str`。**默认值**：`""`。填写平台名称，如 `qq`。
**`qq_account`** — QQ 账号。**类型**：`str`。**默认值**：`""`。机器人登录的 QQ 号（字符串格式），用于识别 @ 消息和自身消息。
**`platforms`** — 其他平台列表。**类型**：`list[str]`。**默认值**：`[]`。多平台部署场景填写。
**`nickname`** — 机器人昵称。**类型**：`str`。**默认值**：`"麦麦"`。聊天中显示的名称。
**`alias_names`** — 别名列表。**类型**：`list[str]`。**默认值**：`[]`。被提及时参与回复判断。
控制麦麦的人设和语言风格。
**`personality`** — 人格设

## 快速要点
- `"auto"` — 根据模型信息自动选择
- `"text"` — 纯文本模式，不发送视觉输入
- `"multimodal"` — 多模态模式，发送视觉输入
- `"compress"` — 压缩后继续处理
- `"discard"` — 丢弃该图片组件
- **`[bot]`** — 机器人身份、平台、昵称、别名
- **`[personality]`** — 人设和回复风格
- **`[visual]`** — 图片理解模式和识图提示词

## 标题树
- Bot 配置
- 基础
- 人格
- 视觉
- 聊天
  - 字段说明
  - no\_action 退避策略
  - talk\_value\_rules
  - chat\_prompts
- 实验性功能
- 消息接收
- 记忆
- 快速启用
- 表达学习
    - learning\_list
- 黑话
    - learning\_list
- 语音
- 表情包
- 关键词反应
- 回复后处理
- 中文错别字
- 回复分割
- 日志
- 遥测
- 调试
- 消息服务
- WebUI
- 数据库
- MCP
- 插件管理
- 插件运行时
  - 配置文件总览
  - 下一步
