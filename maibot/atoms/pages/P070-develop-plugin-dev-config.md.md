---
id: P070
type: source-page
title: "配置管理"
source: "https://docs.mai-mai.org/develop/plugin-dev/config.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 配置管理

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/config.md](https://docs.mai-mai.org/develop/plugin-dev/config.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 插件支持声明式的配置管理机制，通过 `PluginConfigBase` 和 `Field` 定义强类型配置模型，Runner 会自动生成默认配置、补齐缺失字段，并向 WebUI 暴露可渲染的配置 Schema。
每个插件的配置文件位于插件目录下的 `config.toml`：
* `config.toml`：插件的**运行时配置**（功能开关、参数等），由插件自身读取
* `_manifest.json`：插件的**元信息**（ID、版本、依赖等），由 Host 校验和管理
两者用途完全不同，不要混淆。
通过嵌套 `PluginConfigBase` 类实现分组配置：
`Field` 用于声明配置字段的元数据：
* **`default`** `Any` — 字段默认值
* **`default_factory`** `Callable` — 默认值工厂函数，用于 `list`、`dict`、嵌套 `PluginConfigBase` 等可变类型
* **`description`** `str` — 字段描述，WebUI 中显示为表单标签
* **`json_schema_extra`** `dict` —

## 快速要点
- `config.toml`：插件的**运行时配置**（功能开关、参数等），由插件自身读取
- `_manifest.json`：插件的**元信息**（ID、版本、依赖等），由 Host 校验和管理
- **`default`** `Any` — 字段默认值
- **`default_factory`** `Callable` — 默认值工厂函数，用于 `list`、`dict`、嵌套 `PluginConfigBase` 等可变类型
- **`description`** `str` — 字段描述，WebUI 中显示为表单标签
- **`json_schema_extra`** `dict` — 额外元数据，传递给 WebUI Schema 生成器。常用键: `placeholder`（输入框占位符文本）、`group`（UI 分组提示）
- `placeholder`：输入框的占位符提示文本
- `group`：WebUI 中的配置分组提示

## 标题树
- 配置管理
  - 配置文件位置
  - PluginConfigBase 配置模型
    - 基本用法
    - 嵌套配置
  - Field 字段
    - **ui\_label**
    - **ui\_icon**
    - **ui\_order**
    - json\_schema\_extra
  - 访问配置
    - 强类型访问（self.config）
    - 原始字典访问
  - 配置热重载
  - config.toml 格式
    - config\_version
  - 默认配置与 Schema 生成
    - 自动补齐
- 如果 config.toml 只有:
- [plugin]
- enabled = false
- Runner 会自动补齐 greeting 和 advanced 部分的默认值
    - WebUI Schema
- 插件类上的方法（通常不需要手动调用）
  - 通过 API 读取配置
- 读取插件自身配置
- 读取其他插件配置
- 读取全局 Bot 配置
  - 不使用 config\_model
