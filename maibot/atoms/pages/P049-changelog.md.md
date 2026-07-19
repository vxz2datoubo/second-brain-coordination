---
id: P049
type: source-page
title: "更新日志"
source: "https://docs.mai-mai.org/changelog.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 更新日志

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/changelog.md](https://docs.mai-mai.org/changelog.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本页记录 MaiBot 的主要版本更新内容。完整更新日志请参阅 [GitHub Releases](https://github.com/Mai-with-u/MaiBot/releases)。
1.0.0 是一次系统性升级。如果想看更完整的图文说明，可以阅读 [MaiBot 1.0.0 更新专题](./v1-0-0.md)。
* **Maisaka 推理引擎重构**：全面升级规划建设与回复生成的协作机制，Planner 与 Replyer 现已实现深度联动
* **思考力度机制**：动态控制回复时间和长度，让回复节奏更自然
* **A-Memorix 记忆引擎 v1.0**：全新长期记忆系统，支持知识图谱、人物画像、聊天摘要
* **反馈纠错系统**：根据用户反馈自动修正过时记忆，保持记忆时效性
* **MCP 内置插件**：Model Context Protocol 作为内置插件加入，默认不启用
* **全局记忆**：新增全局记忆配置，可选择让记忆跨会话检索
* **模型预设市场**：可以将模型配置完整分享，分享按钮位于模型配置界面右上角
* **全面安全加固**：所有 WebUI API 和 WebSocket 端点

## 快速要点
- **Maisaka 推理引擎重构**：全面升级规划建设与回复生成的协作机制，Planner 与 Replyer 现已实现深度联动
- **思考力度机制**：动态控制回复时间和长度，让回复节奏更自然
- **A-Memorix 记忆引擎 v1.0**：全新长期记忆系统，支持知识图谱、人物画像、聊天摘要
- **反馈纠错系统**：根据用户反馈自动修正过时记忆，保持记忆时效性
- **MCP 内置插件**：Model Context Protocol 作为内置插件加入，默认不启用
- **全局记忆**：新增全局记忆配置，可选择让记忆跨会话检索
- **模型预设市场**：可以将模型配置完整分享，分享按钮位于模型配置界面右上角
- **全面安全加固**：所有 WebUI API 和 WebSocket 端点添加身份认证保护，Cookie 添加 Secure 和 SameSite 属性

## 标题树
- 更新日志
  - v1.0.0
    - 重大更新
    - WebUI 重大更新
    - 细节功能更新
  - v0.12.2
  - v0.12.1
    - 🌟 主要更新
    - 细节功能更改
  - v0.12.0
    - 🌟 重大更新
  - 更早版本
- 服务层架构
  - 服务层在架构中的位置
  - 架构图
  - 服务目录总览
  - 核心服务详解
    - SendService
    - LLMService
    - MemoryService
    - DatabaseService
    - StatisticsService
    - MemoryAutomationService
  - 服务间依赖关系
  - Hook 扩展点
  - 与 Maisaka 的交互
  - 典型调用链
  - 开发注意事项
  - 小结
