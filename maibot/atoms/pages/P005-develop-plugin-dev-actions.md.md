---
id: P005
type: source-page
title: "Action 组件（Legacy）"
source: "https://docs.mai-mai.org/develop/plugin-dev/actions.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Action 组件（Legacy）

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/actions.md](https://docs.mai-mai.org/develop/plugin-dev/actions.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@Action` 装饰器已废弃，SDK 内部会自动将其转换为 `@Tool` 声明。**新插件应直接使用 [`@Tool`](./tools.md)**。使用 `@Action` 时会触发 `DeprecationWarning`。
`@Action` 和 `@Tool` 的核心区别：
* **参数类型**：`@Action` 全部为 `string` → `@Tool` 支持 `string`、`integer`、`boolean`、`array`、`object` 等 7 种类型
* **参数声明**：`action_parameters={"key": "描述"}` → `parameters=[ToolParameterInfo(...)]`
* **参数 Schema**：无 JSON Schema 生成 → 自动生成完整 JSON Schema
* **激活方式**：`activation_type` + `activation_keywords` → 始终可用（由 LLM 自行判断何时调用）
* **描述机制**：单一 `description` → `brief_description` + `detail

## 快速要点
- **参数类型**：`@Action` 全部为 `string` → `@Tool` 支持 `string`、`integer`、`boolean`、`array`、`object` 等 7 种类型
- **参数声明**：`action_parameters={"key": "描述"}` → `parameters=[ToolParameterInfo(...)]`
- **参数 Schema**：无 JSON Schema 生成 → 自动生成完整 JSON Schema
- **激活方式**：`activation_type` + `activation_keywords` → 始终可用（由 LLM 自行判断何时调用）
- **描述机制**：单一 `description` → `brief_description` + `detailed_description`
- **`NEVER`** — 从不激活
- **`ALWAYS`** — 始终作为候选工具
- **`RANDOM`** — 以一定概率随机启用

## 标题树
- Action 组件（Legacy）
  - 从 @Action 迁移到 @Tool
    - 迁移示例
  - @Action 装饰器签名（参考）
    - ActivationType 枚举
    - ChatMode 枚举
  - 内部转换机制
