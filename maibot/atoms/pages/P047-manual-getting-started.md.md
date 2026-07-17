---
id: P047
type: source-page
title: "🚀 MaiBot 快速上手"
source: "https://docs.mai-mai.org/manual/getting-started.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 🚀 MaiBot 快速上手

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/getting-started.md](https://docs.mai-mai.org/manual/getting-started.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
**欢迎使用 MaiBot！** 本文档会带你从零开始，让麦麦成功跑起来。
你需要准备以下 3 样东西：
* **必须是 QQ 小号**（机器人账号有被限制登录的风险，不要用主号）
* **能正常登录**（建议先在手机上确认账号正常）
MaiBot 需要调用大语言模型来思考和回复。**首次启动时会自动生成默认配置，默认使用阿里云百炼（通义千问）**，你只需要获取百炼的 API 密钥即可。
| 服务商 | 价格 | 特点 | 获取方式 |
|--------|------|------|----------|
| **阿里云百炼 (Qwen)** 🏆 默认 | 便宜 | 默认集成，国内直连稳定；通义千问全系列 + 第三方模型，**文本/视觉/向量**全能力覆盖 | [百炼控制台](https://bailian.console.aliyun.com/) → API-KEY |
| **硅基流动** | 便宜 | 聚合 200+ 模型（DeepSeek、Qwen、GLM 等），**一个 API Key 覆盖文本/视觉/向量**，支持支付宝/微信支付 | [官网注册](https://cloud.siliconflow.cn/)

## 快速要点
- **必须是 QQ 小号**（机器人账号有被限制登录的风险，不要用主号）
- **能正常登录**（建议先在手机上确认账号正常）
- **不想折腾？用阿里云百炼** — 默认配置直接可用，只需填 API Key
- **追求极致性价比？用 DeepSeek** — 极低价格获得顶级推理能力
- **想要免费？用智谱 GLM** — Flash 模型永久免费，注册即送 2000 万 tokens
- 大部分服务商提供**免费试用额度**，可以先体验再决定
- 访问 [MaiBot Releases 页面](https://github.com/Mai-with-u/MaiBot/releases)
- 找到最新版本，展开 **Assets**，下载 **Source code (zip)**

## 标题树
- 🚀 MaiBot 快速上手
  - 📋 准备工作
    - 1️⃣ 一个 QQ 小号 🆔
    - 2️⃣ 一个 AI 模型的 API 密钥 🔑
  - 🏃‍♂️ 安装步骤
    - 第 1 步：下载 MaiBot 📥
    - 第 2 步：安装 Python 🐍
    - 第 3 步：安装 uv（包管理器）📦
    - 第 4 步：安装项目依赖
    - 第 5 步：首次启动（生成配置 + 同意协议）
- 先运行一次，终端会显示需要的 hash 值
- 复制终端显示的 EULA_AGREE=xxx 和 PRIVACY_AGREE=xxx
- 然后设置环境变量重新启动
    - 第 6 步：再次启动，进入 WebUI
    - 第 7 步：浏览器打开 WebUI，完成设置 🌐
  - 📱 连接 QQ
    - 安装 NapCat
    - 安装 NapCat 适配器
  - 🎉 开始聊天
    - 测试机器人
  - 🆘 常见问题
    - 启动后自动退出？
    - 端口被占用？
- Windows（CMD）
- 记下最后一列的 PID，然后用任务管理器或命令关闭
- Linux/macOS
- 记下 PID，然后
    - 机器人不回复？
    - API Key 无效？
    - 浏览器打不开？
    - 如何修改配置？
  - 🎯 下一步
