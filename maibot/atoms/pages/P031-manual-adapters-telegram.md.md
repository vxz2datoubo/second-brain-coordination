---
id: P031
type: source-page
title: "Telegram 适配器"
source: "https://docs.mai-mai.org/manual/adapters/telegram.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Telegram 适配器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters/telegram.md](https://docs.mai-mai.org/manual/adapters/telegram.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 的 Telegram 平台适配器，通过 Telegram Bot API 长轮询将 Telegram Bot 与 MaiBot 无缝桥接。
Telegram 适配器的源码：[exynos967/MaiBot-Telegram-Adapter](https://github.com/exynos967/MaiBot-Telegram-Adapter)
在使用适配器之前，你需要先在 Telegram 上创建一个 Bot 并获取 Token。
1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`，按照提示输入 Bot 名称和用户名
3. 创建完成后，BotFather 会返回 Bot Token，格式类似 `123456:ABC-DEF...`
4. 将此 Token 填入适配器配置的 `telegram_bot.token` 字段
默认情况下，Telegram Bot 在群聊中只能接收以 `/` 开头的命令和直接 @Bot 的消息。如果需要 Bot 在群聊中接收所有消息，必须关闭 Privacy Mode：
1. 向 @BotF

## 快速要点
- 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
- 发送 `/newbot`，按照提示输入 Bot 名称和用户名
- 创建完成后，BotFather 会返回 Bot Token，格式类似 `123456:ABC-DEF...`
- 将此 Token 填入适配器配置的 `telegram_bot.token` 字段
- 向 @BotFather 发送 `/setprivacy`
- 选择你创建的 Bot
- 选择 **Disable**
- `maibot_sdk` >= 2.0.0（由 MaiBot 主程序提供）

## 标题树
- Telegram 适配器
  - 适配器仓库
  - 创建 Telegram Bot
    - 第一步：通过 @BotFather 创建 Bot
    - 第二步：关闭 Privacy Mode
  - 安装
    - 依赖
  - 配置
    - 适配器配置
    - MaiBot 主配置
  - 配置参考
    - `[plugin]` — 插件设置
    - `[telegram_bot]` — Telegram Bot 连接配置
    - `[chat]` — 聊天过滤
  - 消息类型支持
  - 代理配置
    - HTTP/HTTPS 代理
    - SOCKS5 代理
    - 从环境变量读取代理
    - 自定义 API 地址
  - Topic 分流
  - @Bot 识别机制
  - 验证连接
    - 常见问题
