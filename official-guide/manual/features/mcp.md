
# MCP 工具集成

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/features/mcp.md](https://docs.mai-mai.org/manual/features/mcp.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 通过 MCP（Model Context Protocol）协议连接外部工具服务器，让 Maisaka 推理引擎获得超出对话本身的能力——浏览器自动化、文件操作、代码执行、API 调用，都可以通过 MCP 工具实现。
MCP（Model Context Protocol）是一个开放协议标准，定义了 AI 应用如何与外部工具和服务进行连接与交互。在 MCP 的世界里，有**客户端**和**服务端**两种角色：
* **MCP 服务端（Server）**：暴露工具、提示词、资源等能力的服务程序。比如一个"浏览器自动化"服务端会提供网页截图、点击元素等工具。
* **MCP 客户端（Client）**：连接到服务端，发现并使用其能力的程序。**MaiBot 就是 MCP 客户端**。
MaiBot 自身不包含天气查询、股票查询、网页搜索等内置工具。这些能力全部来自你连接的 MCP 服务端——MaiBot 负责发现和调用它们，具体能做什么取决于你连了哪些服务器。
MCP 工具对 Maisaka 推理引擎来说是**透明**的——MCP 工具和内置工具（`reply`、`wait`、`finish` 等）走同一个 Tool

## 快速要点
- **MCP 服务端（Server）**：暴露工具、提示词、资源等能力的服务程序。比如一个"浏览器自动化"服务端会提供网页截图、点击元素等工具。
- **MCP 客户端（Client）**：连接到服务端，发现并使用其能力的程序。**MaiBot 就是 MCP 客户端**。
- **MCPManager**（manager.py）— 全局管理器，管理所有服务器连接，提供统一的工具/Prompt/Resource 访问入口
- **MCPConnection**（connection.py）— 管理单个服务器的连接生命周期：连接 → 发现能力 → 调用 → 断开
- **MCPToolProvider**（provider.py）— 将 MCPManager 包装为标准 ToolProvider，对接 Maisaka 规划器
- **MCPHostLLMBridge**（host\_llm\_bridge.py）— 将 MCP Sampling 请求桥接到 MaiBot 自身的 LLM 调用链
- **MCPHostCallbacks**（hooks.py）— 宿主侧回调集合（Sampling、Elicitation、日志等）
- **Models**（models.py）— MCP SDK 原始对象与主程序内部模型的转换层

## 标题树
- MCP 工具集成
  - 什么是 MCP？
  - 架构概览
  - 四种能力类型
    - 1. 工具（Tools）
    - 2. 提示词（Prompts）
    - 3. 资源（Resources）
    - 4. 资源模板（ResourceTemplates）
  - 传输模式
    - stdio（本地子进程）
    - streamable\_http（远程 HTTP）
    - sse（Server-Sent Events）
  - 连接生命周期
    - 启动日志示例
    - 分页加载
  - 工具集成与 Maisaka
    - ToolProvider 接口
    - 工具调用流程
    - 名称冲突与保护
  - 客户端能力
    - Roots（文件系统路径暴露）
    - Sampling（采样 / LLM 调用桥接）
    - Elicitation（引导）
  - 工具结果的内容类型
  - 前置条件
  - 配置示例
    - Playwright 浏览器自动化
    - 文件系统服务器（配合 Roots）
    - GitHub 服务器（带 Token）
    - 远程 HTTP 服务器（Bearer 认证）
  - 故障排除
    - 检查启动日志
    - 常见问题
    - 独立验证 MCP 服务器
  - 相关文档


---
*来源: https://docs.mai-mai.org/manual/features/mcp.md*
