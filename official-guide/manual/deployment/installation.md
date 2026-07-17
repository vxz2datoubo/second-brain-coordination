
# 📦 MaiBot 安装指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/deployment/installation.md](https://docs.mai-mai.org/manual/deployment/installation.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
* **Python 3.12 及以上版本**（推荐 3.12 / 3.13）
* **Git**
从 [GitHub Release](https://github.com/Mai-with-u/MaiBot/releases/) 下载最新版本，或者直接克隆仓库：
`dev` 分支有新功能但可能不稳定。第一次用建议选 `main` 分支。
我们推荐你用 [uv](https://github.com/astral-sh/uv) 管理依赖。
第一次启动会要求你同意用户协议，很简单：
**在终端输入"同意"就行！**
`model_config.toml` 中必须至少包含一个模型配置。如果自动升级失败，需要手动创建模型配置文件，包括：
* 至少一个 API 提供商（`[[api_providers]]`）
* 至少一个文本模型（`[[models]]`）
* 对应的任务分配（`[model_task_config.xxx]`）
视觉模型和嵌入模型是可选的——视觉模型仅在需要看图时配置，嵌入模型仅在启用记忆功能时配置。
参考 [模型配置文档](../configuration/model-config.md) 进行配置。
安装

## 快速要点
- **Python 3.12 及以上版本**（推荐 3.12 / 3.13）
- 至少一个 API 提供商（`[[api_providers]]`）
- 至少一个文本模型（`[[models]]`）
- 对应的任务分配（`[model_task_config.xxx]`）

## 标题树
- 📦 MaiBot 安装指南
  - 环境要求
  - 下载 MaiBot
  - 安装依赖
    - 安装 uv
    - 安装项目依赖
  - 启动
  - 用户协议确认
  - 常见问题
    - 启动后提示"模型列表不能为空"？
    - uv 命令找不到？
- Linux/macOS
- 或者重新打开终端
- 验证安装
    - 非交互环境下如何同意用户协议？
- 方法一：使用程序提示的 hash 值（每次可能不同，以实际提示为准）
- 方法二：先运行一次看提示的 hash 值，记录后用环境变量启动


---
*来源: https://docs.mai-mai.org/manual/deployment/installation.md*
