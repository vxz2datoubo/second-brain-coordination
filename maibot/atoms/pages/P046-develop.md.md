---
id: P046
type: source-page
title: "开发指南"
source: "https://docs.mai-mai.org/develop.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 开发指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop.md](https://docs.mai-mai.org/develop.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot（麦麦 / MaiSaka）是基于大语言模型的可交互智能体。本节面向希望参与开发或编写插件的开发者，介绍项目的技术栈、目录结构与开发环境搭建。
| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI |
| ORM | SQLModel |
| ASGI 服务器 | Uvicorn |
| 配置管理 | Pydantic + TOML + 热重载 |
| 插件 IPC | msgpack over UDS / TCP / Named Pipe |
| 包管理 | uv |
| 代码检查 | Ruff |
| 许可证 | GPL-3.0 |
* **config/**：使用 Pydantic 模型管理配置，支持 TOML 文件热重载，配置修改通过模版+版本号方式发布，不直接编辑运行时配置。
* **chat/**：聊天消息入口与主链路调度。包含 `ChatBot`（消息处理入口）、`ChatManager`（会话管理）、`HeartFlow`（心流消息处理器）等。
* **maisaka/**：核心 AI 运行时。以 `ChatLoo

## 快速要点
- **config/**：使用 Pydantic 模型管理配置，支持 TOML 文件热重载，配置修改通过模版+版本号方式发布，不直接编辑运行时配置。
- **chat/**：聊天消息入口与主链路调度。包含 `ChatBot`（消息处理入口）、`ChatManager`（会话管理）、`HeartFlow`（心流消息处理器）等。
- **maisaka/**：核心 AI 运行时。以 `ChatLoopService` 为中心，负责 LLM 对话循环、工具调用规划、上下文消息管理等。
- **A\_memorix/**：长期记忆引擎，负责持久化用户偏好、对话记忆等心理学维度数据。
- **plugin\_runtime/**：插件运行时系统。采用 Host（主进程）/ Runner（子进程）IPC 架构，使用 msgpack 编解码，支持 Hook 机制、组件注册与热重载。
- **platform\_io/**：平台抽象层。通过 `RouteKey` 路由机制实现多平台消息收发的统一管理，支持驱动的注册、路由绑定、入站去重与出站跟踪。
- **llm\_models/**：LLM 客户端实现，封装各模型 API 的调用逻辑。
- **services/**：业务服务层，包含 `SendService`（出站消息发送）等核心服务。

## 标题树
- 开发指南
  - 技术栈
  - 项目结构
    - 核心模块说明
  - 开发环境搭建
    - 前置条件
    - 安装依赖
    - 启动项目
    - 运行测试
    - 代码检查与格式化
- Lint 检查
- 自动格式化
  - 架构详解
    - 基础域（Wave 1）—— 底层基础设施
    - 核心功能域（Wave 2）—— 主要业务链路
    - 辅助功能域（Wave 3）—— 增强能力模块
  - 下一步
