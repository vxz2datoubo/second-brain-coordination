---
id: MB-0005
type: concept-atom
title: "WebUI 是运维与配置入口"
snapshot: "2026-06-22"
tags: [WebUI, 配置管理, 运维]
---

# WebUI 是运维与配置入口

## 原子结论
WebUI 是 MaiBot 面向用户和管理员的主要可视化入口，覆盖配置管理、插件管理、记忆管理、聊天记录和统计等功能；开发层面还有独立的内部机制文档。

## 关键事实
- 默认访问地址为 `http://127.0.0.1:8001`。
- 配置管理用于降低 TOML 手改风险。
- 插件管理能安装、启用、配置和查看插件状态。
- 记忆管理用于查看、搜索和维护机器人记忆。

## 项目约束
当前项目约定 WebUI 开发服务固定使用 7999 端口；修改 WebUI 后不要急着 `npm run build`，构建应由人工决定。

## 来源页
- [https://docs.mai-mai.org/manual/webui.md](https://docs.mai-mai.org/manual/webui.md)
- [https://docs.mai-mai.org/manual/webui/config-management.md](https://docs.mai-mai.org/manual/webui/config-management.md)
- [https://docs.mai-mai.org/manual/webui/plugin-management.md](https://docs.mai-mai.org/manual/webui/plugin-management.md)
- [https://docs.mai-mai.org/manual/webui/memory-management.md](https://docs.mai-mai.org/manual/webui/memory-management.md)
- [https://docs.mai-mai.org/manual/webui/chat-stats.md](https://docs.mai-mai.org/manual/webui/chat-stats.md)
- [https://docs.mai-mai.org/develop/architecture/webui-internals.md](https://docs.mai-mai.org/develop/architecture/webui-internals.md)

## 本地来源笔记
- [[P003-manual-webui.md|🖥️ WebUI 管理面板]]
- [[P042-manual-webui-config-management.md|在浏览器里改配置]]
- [[P043-manual-webui-plugin-management.md|安装和管理插件]]
- [[P051-manual-webui-memory-management.md|查看和管理记忆]]
- [[P060-manual-webui-chat-stats.md|聊天记录和统计]]
- [[P035-develop-architecture-webui-internals.md|WebUI 内部机制]]
