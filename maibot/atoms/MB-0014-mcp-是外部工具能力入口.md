---
id: MB-0014
type: concept-atom
title: "MCP 是外部工具能力入口"
snapshot: "2026-06-22"
tags: [MCP, 工具, 配置]
---

# MCP 是外部工具能力入口

## 原子结论
MCP 让 MaiBot 可以接入外部工具服务。用户侧关注如何启用和配置 MCP server；架构侧关注 MCP 工具如何被发现、调用、鉴权和接入推理流程。

## 关键事实
- MCP server 支持 stdio 和 streamable_http 等传输方式。
- stdio 需要 command/args；HTTP 需要 url；有鉴权时需要正确配置 token。
- MCP 连接失败常见原因包括 command 缺失、url 缺失、服务没启动、token 不匹配和网络不可达。

## 排错入口
先独立验证 MCP 服务可运行或 URL 可访问，再接入 MaiBot 配置；不要用宽泛 fallback 掩盖具体连接错误。

## 来源页
- [https://docs.mai-mai.org/manual/features/mcp.md](https://docs.mai-mai.org/manual/features/mcp.md)
- [https://docs.mai-mai.org/manual/configuration/mcp-config.md](https://docs.mai-mai.org/manual/configuration/mcp-config.md)
- [https://docs.mai-mai.org/develop/architecture/mcp-integration.md](https://docs.mai-mai.org/develop/architecture/mcp-integration.md)

## 本地来源笔记
- [[P025-manual-features-mcp.md|MCP 工具集成]]
- [[P026-manual-configuration-mcp-config.md|MCP 配置 🛠️]]
- [[P027-develop-architecture-mcp-integration.md|MCP 集成架构]]
