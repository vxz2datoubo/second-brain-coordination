
# LLMProvider 组件

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/llmprovider.md](https://docs.mai-mai.org/develop/plugin-dev/llmprovider.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@LLMProvider` 用于声明插件提供新的 LLM Provider `client_type`。主程序会将该 `client_type` 注册到 LLM 客户端注册表中，因此现有 `LLMService` 和模型任务配置不需要改调用方式——只要模型配置里的 `api_providers[].client_type` 指向插件声明的值，请求就会通过插件 Provider 发起。
LLM Provider 必须同时满足两处声明，缺一不可：
1. `_manifest.json` 顶层 `llm_providers` 中静态声明 `client_type`
2. 插件代码中使用 `@LLMProvider("同一个 client_type")` 修饰处理方法
Runner 会校验 manifest 与装饰器收集结果完全一致。任意一边漏写、拼写不一致或同一插件内重复声明，插件都会拒绝加载。不同插件声明同一个 `client_type` 时，冲突双方都会被阻止加载。
* **`client_type`** `str` · 必填 — 客户端类型标识，对应模型配置中的 `api_providers[].client_type`。

## 快速要点
- `_manifest.json` 顶层 `llm_providers` 中静态声明 `client_type`
- 插件代码中使用 `@LLMProvider("同一个 client_type")` 修饰处理方法
- **`client_type`** `str` · 必填 — 客户端类型标识，对应模型配置中的 `api_providers[].client_type`。不能为空
- **`name`** `str` · 默认 `""` — Provider 展示名称。留空时使用 `client_type`
- **`description`** `str` · 默认 `""` — Provider 描述信息
- **`version`** `str` · 默认 `"1.0.0"` — Provider 实现版本号
- **`**metadata`** `Any` — 额外元数据键值对
- **`client_type`** `str` · 必填 — Provider 客户端类型，必须与模型配置 `api_providers[].client_type` 一致

## 标题树
- LLMProvider 组件
  - 装饰器签名
    - 参数说明
  - Manifest 声明
    - llm\_providers 字段说明
  - Operation 类型
  - 请求与返回字段
    - 处理方法参数
    - 返回值字段
  - 基本用法
    - 方式一：手动分发（简单场景）
    - 方式二：LLMProviderBase 基类（推荐，逻辑较多时）
  - 完整示例
  - 卸载与回退
- MaiBot 1.0.0 更新专题
  - 这次升级改变了什么
  - Maisaka 回复核心
  - A\_Memorix 记忆系统
  - Dashboard 新工作台
  - 插件、MCP 与工具
  - 图片、表情包与多模态
  - 性能、稳定性与安全
  - 相关文档


---
*来源: https://docs.mai-mai.org/develop/plugin-dev/llmprovider.md*
