---
id: P045
type: source-page
title: "工具系统架构"
source: "https://docs.mai-mai.org/develop/architecture/tool-system.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 工具系统架构

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/tool-system.md](https://docs.mai-mai.org/develop/architecture/tool-system.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
MaiBot 的工具系统把插件工具、旧版 Action、MaiSaka 内置能力和外部 MCP 工具收敛到同一套抽象层。它不负责教插件作者如何写一个 `@Tool`，也不替代 [插件 Tool 用法](../plugin-dev/tools.md) 中的开发教程。本文聚焦内部实现，说明工具声明、工具调用、Provider 适配和 ToolRegistry 路由如何协同工作。
MaiBot 当前统一四类工具来源：
**插件 `@Tool`** ：插件运行时中的 Tool 组件。插件 SDK 使用 `@Tool` 声明工具，运行时把声明写入组件注册表，`PluginToolProvider` 再把这些工具暴露给统一工具层。
**旧 `@Action`** ：旧版插件中的 Action 组件。SDK 2.0 会把 `@Action` 自动转换为 Tool 声明，MaiBot 运行时仍保留兼容路径，使旧插件可以继续被 LLM 调用。
**MaiSaka 内置 Tool** ：推理引擎自带的系统级能力，例如 `send_emoji`、记忆查询、回复、等待、结束本轮等。这些工具由 `Maisaka

## 快速要点
- 本页以说明性内容为主，详见标题树和来源。

## 标题树
- 工具系统架构
  - 1. 概述
  - 2. 架构图
  - 3. 核心概念
    - 3.1 ToolCall
    - 3.2 ToolIcon
    - 3.3 ToolAnnotation
    - 3.4 ToolSpec
    - 3.5 ToolProvider
    - 3.6 ToolRegistry
    - 3.7 ToolExecutionContext
    - 3.8 ToolAvailabilityContext
    - 3.9 ToolExecutionResult
  - 4. 四类工具来源详解
    - 4.1 插件 `@Tool`
    - 4.2 旧 `@Action`
    - 4.3 MaiSaka 内置 Tool
    - 4.4 MCP Tool
  - 5. 关键流程
    - 5.1 工具注册
    - 5.2 工具发现
    - 5.3 推理引擎选择
    - 5.4 工具调用
    - 5.5 结果返回
  - 6. 与插件开发的关系
