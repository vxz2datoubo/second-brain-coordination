
# MCP 配置 🛠️

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration/mcp-config.md](https://docs.mai-mai.org/manual/configuration/mcp-config.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MCP（Model Context Protocol）让 MaiBot 能够连接外部工具，从"只会聊天"变成"又能说又能做"——查天气、搜新闻、读文件、调 API，全都可以。
本文详细介绍如何在 `bot_config.toml` 中配置 MCP。
如果你还不熟悉 MCP 是什么，建议先阅读 [MCP 功能概述](../features/mcp.md)，了解它能做什么。
MCP 配置位于 `bot_config.toml` 的 `[mcp]` 段落下，分为三个层级：
* **`enable`** — 是否启用 MCP，设为 `false` 时所有 MCP 服务器都不会连接。默认开启
这部分配置 MaiBot 作为 MCP **客户端**时，向服务端声明自己的能力。
一般不需要改，除非你希望 MCP 服务端看到不同的客户端标识。
* **`client_name`** — 客户端实现名称。默认 `"MaiBot"`
* **`client_version`** — 客户端实现版本。默认 `"1.0.0"`
Roots 允许你向 MCP 服务器暴露本地文件系统路径，让服务器能读写这些路径下的文件。
* **`enable`**

## 快速要点
- **`enable`** — 是否启用 MCP，设为 `false` 时所有 MCP 服务器都不会连接。默认开启
- **`client_name`** — 客户端实现名称。默认 `"MaiBot"`
- **`client_version`** — 客户端实现版本。默认 `"1.0.0"`
- **`enable`** — 是否向 MCP 服务器暴露 Roots 能力。默认关闭
- **`items`** — Roots 列表。默认为空
- **`enabled`** — 是否启用。默认开启
- **`uri`** — Root URI，通常为 `file://` 路径，启用时必填。默认为空
- **`name`** — 显示名称。默认为空

## 标题树
- MCP 配置 🛠️
  - 配置结构总览
  - 总开关 \[mcp]
  - 客户端能力 \[mcp.client]
    - 基础信息
    - Roots 能力 \[mcp.client.roots]
    - Sampling 能力 \[mcp.client.sampling]
    - Elicitation 能力 \[mcp.client.elicitation]
  - 服务器配置 \[\[mcp.servers]]
    - 通用字段
    - stdio 模式
      - 通过 uvx 运行（推荐）
      - 通过 npx 运行
      - 通过 Python 运行
    - streamable\_http 模式
      - 无认证的远程服务
      - 带 Bearer Token 的远程服务
      - 带自定义请求头的远程服务
  - 完整示例
    - 基础配置：只连接一个服务
    - 日常使用配置：两个服务 + 基础能力
- 连接 Playwright（浏览器自动化）
- 连接文件系统服务器
    - 高级配置：启用 Sampling + Roots
- 本地服务
- 远程服务
  - 常见问题
    - Q: 配置后不生效？
    - Q: 可以配置多少个服务？
    - Q: 如何在网上找 MCP 服务？
    - Q: stdio、streamable\_http 和 sse 怎么选？
    - Q: 从哪里获取 API Token？
  - 下一步


---
*来源: https://docs.mai-mai.org/manual/configuration/mcp-config.md*
