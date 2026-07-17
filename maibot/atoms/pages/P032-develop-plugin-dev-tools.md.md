---
id: P032
type: source-page
title: "Tool 组件"
source: "https://docs.mai-mai.org/develop/plugin-dev/tools.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Tool 组件

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/tools.md](https://docs.mai-mai.org/develop/plugin-dev/tools.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@Tool` 是 MaiBot 插件系统中最核心的组件类型。它允许插件向 LLM 暴露可调用的工具函数，使 LLM 能够在推理过程中主动调用外部能力——例如搜索知识库、查询数据库、调用外部 API 等。
`@Action` 是旧版装饰器，SDK 内部会自动将其转换为 `@Tool` 声明。新插件应直接使用 `@Tool`，不再使用 `@Action`。详见 [Action 组件（Legacy）](./actions.md)。
* **`name`** `str` — 工具名称，需在插件内唯一。LLM 通过此名称调用工具
* **`description`** `str` — 工具备选描述。当 `brief_description` 为空时使用此字段
* **`brief_description`** `str` — 工具主描述（优先使用）。传给 LLM 的工具描述摘要，帮助 LLM 判断是否需要调用
* **`detailed_description`** `str` — 详细描述，可包含参数使用说明、注意事项等。SDK 会自动合并参数 Schema 生成完整描述
* **`parameters`** `list | di

## 快速要点
- **`name`** `str` — 工具名称，需在插件内唯一。LLM 通过此名称调用工具
- **`description`** `str` — 工具备选描述。当 `brief_description` 为空时使用此字段
- **`brief_description`** `str` — 工具主描述（优先使用）。传给 LLM 的工具描述摘要，帮助 LLM 判断是否需要调用
- **`detailed_description`** `str` — 详细描述，可包含参数使用说明、注意事项等。SDK 会自动合并参数 Schema 生成完整描述
- **`parameters`** `list | dict | None` — 工具参数定义，支持两种格式（见下文）
- `description`：关于工具的描述，包括使用方法，使用情景，注意事项。当 `brief_description` 为空时，`description` 会作为回退描述。
- `brief_description`：给主程序或小模型快速判断"这个工具是做什么的"的简要描述
- `detailed_description`：描述参数、必填项、可选项和调用约束的详细描述

## 标题树
- Tool 组件
  - 装饰器签名
    - 参数说明
  - 参数定义
    - 方式一：结构化参数（推荐）
    - 方式二：dict 参数（兼容旧式声明）
  - ToolParameterInfo 字段
  - ToolParamType 枚举
  - 处理函数
    - 返回值
    - 返回图片和其他媒体
    - kwargs 中常见的额外参数
  - 描述生成规则
  - 完整示例
  - 与旧版 Action 的关系
