
# Manifest 系统

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/manifest.md](https://docs.mai-mai.org/develop/plugin-dev/manifest.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
每个 MaiBot 插件必须在其根目录下包含一个 `_manifest.json` 文件，用于声明插件的元信息、版本兼容性、依赖关系和能力需求。Host 侧的 `ManifestValidator` 会在加载前严格校验此文件。
* `_manifest.json`：插件**元信息**（ID、版本、依赖等），由 Host 校验和管理
* `config.toml`：插件**运行时配置**（功能开关、参数等），由插件自身读取
两者用途完全不同，不要混淆。
以下是一个完整的 Manifest 示例：
* **`manifest_version`** `2` — Manifest 协议版本，当前固定为 `2`
* **`id`** `string` — 插件唯一标识符，格式为小写字母/数字，以点号或横线分隔（如 `com.author.plugin`）
* **`version`** `string` — 插件版本号，必须为严格三段式语义版本（如 `1.0.0`）
* **`name`** `string` — 插件展示名称
* **`description`** `string` — 插件描述
* **`author`** `ob

## 快速要点
- `_manifest.json`：插件**元信息**（ID、版本、依赖等），由 Host 校验和管理
- `config.toml`：插件**运行时配置**（功能开关、参数等），由插件自身读取
- **`manifest_version`** `2` — Manifest 协议版本，当前固定为 `2`
- **`id`** `string` — 插件唯一标识符，格式为小写字母/数字，以点号或横线分隔（如 `com.author.plugin`）
- **`version`** `string` — 插件版本号，必须为严格三段式语义版本（如 `1.0.0`）
- **`name`** `string` — 插件展示名称
- **`description`** `string` — 插件描述
- **`author`** `object` — 插件作者信息，包含 `name`（作者名）和 `url`（作者主页，必须为 HTTP/HTTPS URL）

## 标题树
- Manifest 系统
  - \_manifest.json 结构
  - 必填字段
  - 可选字段
    - plugin\_type 插件类型
    - display 展示元信息
    - urls 链接集合
    - host\_application / sdk 版本区间
    - i18n 国际化配置
    - llm\_providers LLM Provider 声明
  - 依赖声明
    - 插件级依赖
    - Python 包依赖
    - 依赖解析流程
  - 校验规则


---
*来源: https://docs.mai-mai.org/develop/plugin-dev/manifest.md*
