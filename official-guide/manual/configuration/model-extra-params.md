
# 模型额外参数 (extra\_params)

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration/model-extra-params.md](https://docs.mai-mai.org/manual/configuration/model-extra-params.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`model_config.toml` 中每个模型都可以设置 `extra_params` 字段，用于在 API 调用时传递服务商特有的参数。最常见的用途是控制大模型的思考模式和推理强度。
`extra_params` 不会以原样整体发送给服务商，实际请求前客户端会按规则拆分转换：
* **`headers`** — 作为请求头传入
* **`query`** — 作为 URL 查询参数传入
* **`body`** — 合并到请求体
* **其他普通键** — 作为请求体额外字段传入（OpenAI SDK 的 `extra_body`）
当 `client_type = "google"` 时，`extra_params` 不按上述规则拆分，而是由 Gemini 客户端按自身支持的字段筛选和映射到 `GenerateContentConfig`。
很多大模型支持"思考模式"，让模型在回答前先进行深度推理，从而提升复杂问题的回答质量。MaiBot 支持两种 API 体系，配置方式不同：
* **OpenAI 兼容 API**（`client_type = "openai"`）：DeepSeek、OpenAI、阿里云百炼等
*

## 快速要点
- **`headers`** — 作为请求头传入
- **`query`** — 作为 URL 查询参数传入
- **`body`** — 合并到请求体
- **其他普通键** — 作为请求体额外字段传入（OpenAI SDK 的 `extra_body`）
- **OpenAI 兼容 API**（`client_type = "openai"`）：DeepSeek、OpenAI、阿里云百炼等
- **Gemini 原生 API**（`client_type = "google"`）：Google Gemini 系列
- DeepSeek V4 的 `reasoning_effort` 仅支持 `high`（默认）和 `max`（极限推理）两个有效等级。`low`/`medium` 映射为 `high`，`xhigh` 映射为 `max`
- **多轮对话规则**：如果思考轮次没有工具调用，不需要把思考内容回传；如果有工具调用，必须回传

## 标题树
- 模型额外参数 (extra\_params)
- 思考与非思考模式
  - OpenAI 兼容 API
  - Gemini 原生 API
    - Gemini 2.5（thinking\_budget）
    - Gemini 3.0+（thinking\_level）
    - Gemini 总览
- 自定义 HTTP 请求
- 高级鉴权配置
- 其他高级参数
  - 模型级参数覆盖
  - 优先级说明
  - API 提供商高级配置
  - 运行时配置
- 常用参数速查
  - OpenAI 兼容 API
  - Gemini 原生 API


---
*来源: https://docs.mai-mai.org/manual/configuration/model-extra-params.md*
