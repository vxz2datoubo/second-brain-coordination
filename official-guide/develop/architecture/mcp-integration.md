
# MCP 集成架构

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/mcp-integration.md](https://docs.mai-mai.org/develop/architecture/mcp-integration.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
MaiBot 的 MCP 集成位于 `maibot/src/mcp_module/`，职责不是把某个固定能力写进主程序，而是把外部 MCP 服务器变成 MaiBot 工具系统的一部分。MCP 服务器提供工具、Prompt、Resource 等能力，MaiBot 作为 MCP 客户端连接这些服务器，发现能力，再把工具能力适配到统一 `ToolProvider` 接口。
本文聚焦开发视角的内部架构，不重复用户手册中关于配置和使用的说明。
**MCP 的角色** ：MCP 是 Model Context Protocol。MaiBot 在集成中扮演 MCP Client，外部服务扮演 MCP Server。MaiBot 不内置外部工具实现，只负责协议连接、能力发现、调用路由和结果归一化。
**能力来源** ：MCP Server 暴露的能力可以包括 Tools、Prompts、Resources 和 Resource Templates。当前对 Maisaka 推理引擎最直接生效的是 Tools，因为工具会被转换成 `ToolSpec` 并进入统一工具列表。
**集成目标** ：MCP 工具

## 快速要点
- 本页以说明性内容为主，详见标题树和来源。

## 标题树
- MCP 集成架构
  - 1. 概述
  - 2. 架构图
  - 3. 核心概念
    - 3.1 MCP Server 与 MCP Client
    - 3.2 MCPConnectionManager，也就是 MCPManager
    - 3.3 MCPConnection
    - 3.4 MCPToolProvider
    - 3.5 HostLLMBridge
    - 3.6 MCPHostCallbacks 与 Hook 边界
  - 4. 关键流程
    - 4.1 MCP 服务器连接
    - 4.2 工具发现
    - 4.3 注册到 ToolProvider
    - 4.4 推理引擎调用
    - 4.5 结果返回与历史写入
  - 5. 与工具抽象层 tool-system 的交互
  - 6. 与 Maisaka 的交互
    - 6.1 工具列表进入推理引擎
    - 6.2 function\_call 路由
    - 6.3 与 Host LLM 桥接的关系
  - 7. Hook 集成点
    - 7.1 当前协议层 Hook
    - 7.2 插件命名 Hook 设计点
  - 8. 数据模型转换
  - 9. 运行时配置
  - 10. 容错与安全边界
  - 11. 与其他文档的边界
  - 12. 总结


---
*来源: https://docs.mai-mai.org/develop/architecture/mcp-integration.md*
