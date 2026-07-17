
# Prompt 模板系统

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/prompt-templates.md](https://docs.mai-mai.org/develop/architecture/prompt-templates.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
Prompt 模板系统是 MaiBot 赋予 AI 角色灵魂的核心机制。它将 LLM 的指令（System Prompt）、任务逻辑（Task Templates）与运行时数据（Runtime Parameters）解耦，使得开发者可以在不修改代码的情况下，通过编辑 `.prompt` 文件快速调整 AI 的行为模式、回复风格和推理逻辑。
Prompt 模板系统在 MaiBot 整体架构中属于基础服务层，与 Config 配置模块、i18n 国际化模块和 Maisaka 推理引擎深度协作。它向下屏蔽了文件系统和多语言路由的复杂性，向上为 ChatLoopService、学习模块等消费者提供统一的模板获取接口。通过这套系统，MaiBot 能够在多种语言环境下保持一致的回复质量，同时支持运行时的行为热更新。
Prompt 系统的核心目标是提供一个可国际化、可热重载、且支持复杂变量注入的模板管理机制。它将静态的模板文件转换为可动态渲染的 Prompt 实例，并允许通过上下文构造函数将实时的业务数据注入到模板中。整个系统在 MaiBot 中承担着"AI 行为定义层"的角色——它决定了 LLM

## 快速要点
- **存储层**：负责模板文件的物理存储，划分为内置模板目录（`/prompts/`）和自定义模板目录（`/data/custom_prompts/`），按 locale 子目录组织，支持 UTF-8 编码的纯文本 `.prompt` 文件。
- **管理层**：`PromptManager` 作为中央控制器，维护模板的注册、缓存、版本检测和热重载逻辑，通过版本号计数器实现增量更新。
- **渲染引擎层**：接收 `Prompt` 实例和上下文构造函数，执行异步变量替换与递归渲染，输出纯文本 Prompt。渲染管线基于 `asyncio` 实现并发解析。
- **Locale 切换**：当 `common.i18n.set_locale()` 被调用时，`PromptManager` 标记所有缓存为 stale，下次 `get_prompt()` 调用触发全量重新加载并重建 locale → 文件路径映射表。
- **文件修改检测**：通过周期性的版本号轮询（非实时文件监听，无 inotify 依赖）检测模板文件变更。检测间隔由 `Config` 模块中的 `prompt_reload_interval` 参数控制，默认值为 60 秒。
- **显式刷新**：开发者可通过 `PromptManager.reload_prompts()` 强制刷新缓存，适用于部署后的模板热修复场景，调用后将清空全部缓存并重新扫描模板目录。
- **模板不存在回退**：当请求的模板名称在当前 locale 下不存在时，系统自动回退至默认 locale（`en-US`）查找，若仍不存在则抛出 `PromptNotFoundError`。
- **内部构造函数**：绑定在特定 Prompt 实例上的函数，优先度最高，仅在当前克隆实例的生命周期内有效。

## 标题树
- Prompt 模板系统
  - 架构概述
  - 架构图
  - 核心概念
  - 关键流程
  - 模块交互
  - 与其它模块交互
  - 开发注意事项
  - Hook/扩展点


---
*来源: https://docs.mai-mai.org/develop/architecture/prompt-templates.md*
