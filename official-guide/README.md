# MaiBot 官方文档指南

> 📋 这不是普通的 Markdown 文件 — 这是 MaiBot 项目的**官方完整文档镜像**。
>
> 源站：https://docs.mai-mai.org  
> 快照日期：2026-06-22  
> 页面总数：70

## 🗂 文档结构

```
official-guide/
├── manual/                       # 📘 用户手册
│   ├── deployment/               # 部署方式（源码、一键包、Docker）
│   ├── adapters/                 # 消息平台适配器（QQ/Telegram/Discord）
│   ├── configuration/            # 完整配置参考（Bot/模型/MCP/A_Memorix）
│   ├── features/                 # 功能详解（消息管线/推理引擎/记忆/表情包）
│   ├── webui/                    # WebUI 管理面板操作指南
│   └── faq.md                    # 常见问题排查
├── develop/                      # 🔧 开发文档
│   ├── architecture/             # 核心架构文檔（消息管线/推理引擎/记忆/工具/MCP）
│   └── adapter-dev/              # 适配器开发指南
├── plugin/                       # 🔌 插件开发
│   ├── manifest.md               # 插件清单配置
│   ├── lifecycle.md              # 生命周期
│   ├── config.md                 # 配置管理
│   ├── tools.md                  # @Tool 组件
│   ├── commands.md               # @Command 组件
│   ├── hooks.md                  # @Hook 处理器
│   ├── event-handlers.md         # 事件处理器
│   ├── api-components.md         # @API 组件（插件间通信）
│   ├── message-gateway.md        # 消息网关
│   ├── llmprovider.md            # LLM Provider 组件
│   ├── actions.md                # Action（旧版兼容）
│   ├── api-reference.md          # API 参考
│   └── vibe-coding.md            # Vibe Coding 指南
└── changelog.md                  # 版本更新日志
```

## 🆘 快速查找

| 想做什么 | 看这里 |
|----------|--------|
| 排查启动失败 / 不回复 | `manual/faq.md` |
| 配置模型 API Key | `manual/configuration/model-config.md` |
| 理解 MaiBot 怎么思考的 | `manual/features/maisaka-reasoning.md` |
| 理解记忆系统 | `manual/features/memory-system.md` + `develop/architecture/memory-system.md` |
| 写插件 | `plugin/manifest.md` → `plugin/lifecycle.md` → `plugin/tools.md` |
| 接入新平台 | `develop/adapter-dev/platform-io.md` |
| MCP 工具 | `manual/features/mcp.md` + `develop/architecture/mcp-integration.md` |
| WebUI 使用 | `manual/webui/` |

---

⚠️ **注意**：这是只读参考镜像。修改不会同步回官方源站。如需最新版，请访问 https://docs.mai-mai.org。
