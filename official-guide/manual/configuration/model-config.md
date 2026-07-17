
# 模型配置

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration/model-config.md](https://docs.mai-mai.org/manual/configuration/model-config.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`model_config.toml` 给麦麦配置"AI 大脑"——决定不同组件使用什么 LLM 模型，以及如何连接 API 服务商。
最少启动只需一个 LLM 模型和一个 API 提供商（`models` 和 `api_providers` 均非空）。完整功能还需 VLM 模型（看图）和嵌入模型（记忆搜索）。
每个 `[[api_providers]]` 块定义一个 API 服务商。一个配置文件可以有多个提供商。
**要点：**
* **必填**：`name`（服务商名称）、`base_url`（端点地址）、`api_key`（密钥，`auth_type = "none"` 时除外）
* **鉴权**：默认 `bearer` 适用于绝大部分服务商。其他可选 `header` / `query` / `none`
* **客户端**：默认 `openai`。Google Gemini 用 `"google"`，见 [模型额外参数](./model-extra-params.md#gemini-原生-api)
* **超时与重试**：`timeout` 默认 60s，`max_retry` 默认 3 次，`retry_inte

## 快速要点
- **必填**：`name`（服务商名称）、`base_url`（端点地址）、`api_key`（密钥，`auth_type = "none"` 时除外）
- **鉴权**：默认 `bearer` 适用于绝大部分服务商。其他可选 `header` / `query` / `none`
- **客户端**：默认 `openai`。Google Gemini 用 `"google"`，见 [模型额外参数](./model-extra-params.md#gemini-原生-api)
- **超时与重试**：`timeout` 默认 60s，`max_retry` 默认 3 次，`retry_interval` 默认 5s
- 其余字段参见上方注释，均有合理默认值
- **必填**：`model_identifier`（API 标识符）、`name`（自定义名称）、`api_provider`（归属服务商）
- **价格**：`price_in` / `price_out` 用于统计，单位 元/百万 token。开启 `cache` 后可单独设置 `cache_price_in`
- **模型级覆盖**：`temperature` / `max_tokens` 可覆盖任务配置，不设则使用任务默认值

## 标题树
- 模型配置
  - API 提供商
- organization = "org-xxxx"                # [可选] OpenAI 官方接口可选的 organization
- project = "proj-xxxx"                    # [可选] OpenAI 官方接口可选的 project
  - 模型
- temperature = 0.7                          # [可选] 模型级别温度，会覆盖任务配置中的 temperature
- max_tokens = 4096                          # [可选] 模型级别最大 token 数，会覆盖任务配置中的 max_tokens
  - 任务配置
- [必填] 回复器：将 Planner 收集的信息转为最终回复文本。追求语言质量和表达风格，推荐 pro 模型 + 思考模式。
- [必填] 规划器：战略核心——决定何时说话、回复谁、调用哪些工具（MCP/插件）。需较强推理和 tool 调用能力。
- [必填] 组件模型：表情包分析、学习分析、取名、关系模块、情绪变化等。麦麦必须的模型。
- [可选] 长期记忆：记忆总结、抽取、写回等高质量任务（A_Memorix 子系统）。
- 默认 model_list 为空（不自动回退），未配置时调用方按需处理。
- [可选] 中期摘要：上下文裁切时将历史聊天压缩为摘要。留空时自动回退到 planner。
- [可选] 节奏控制：独立判断是否该在此时说话。留空时自动回退到 planner。
- [可选] 学习模型：表达方式学习和黑话学习。留空时自动回退到 utils。
- [可选] 表情包选择：从候选表情包中选出合适的一张发送。
- 选择优先级：emoji 有模型→用 emoji，planner 全视觉→用 planner，否则→用 vlm
- [强烈建议] 看图说话：理解图片内容。需 visual=true 的多模态模型。
- [可选] 语音识别：语音转文字。
- [强烈建议] 嵌入模型：生成文本向量，用于长期记忆的语义搜索。
- 推荐专门的嵌入模型（如 text-embedding-3-small）。未配置时记忆搜索不可用。
    - 回退规则
  - 下一步


---
*来源: https://docs.mai-mai.org/manual/configuration/model-config.md*
