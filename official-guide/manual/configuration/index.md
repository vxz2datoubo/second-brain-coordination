
# 配置概览

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/configuration.md](https://docs.mai-mai.org/manual/configuration.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 有两个主要的配置文件，都放在 `config/` 文件夹里：
| 📁 文件 | 📝 作用 | 🔗 详细说明 |
|---------|---------|------------|
| `bot_config.toml` | 机器人的基本信息、性格、聊天、记忆（含 A\_Memorix）、学习、日志等全部主配置 | [查看详情](./bot-config.md) |
| `model_config.toml` | AI模型设置，设置麦麦使用的LLM | [查看详情](./model-config.md) |
这些配置文件需要启动一次MaiBot之后才会生成。如果无法找到，请先启动一次。
麦麦现在支持配置热重载。修改配置文件后无需重启，保存即可自动重新加载新配置。
(有些配置（比如换AI模型）可能需要重新初始化相关服务才能完全生效。)
如果你不喜欢手动改文件，MaiBot 还提供了网页版的配置界面（1.0.0 已内置 WebUI 配置界面）：
* 🌐 默认地址：`http://127.0.0.1:8001`
* 🖱️ 点点鼠标就能改配置
* 📱 手机、电脑都能用

## 快速要点
- 🌐 默认地址：`http://127.0.0.1:8001`
- 🖱️ 点点鼠标就能改配置
- 📱 手机、电脑都能用

## 标题树
- 配置概览
  - 📋 配置文件清单
  - 🌐 WebUI 配置


---
*来源: https://docs.mai-mai.org/manual/configuration.md*
