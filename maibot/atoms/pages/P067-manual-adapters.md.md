---
id: P067
type: source-page
title: "适配器概览"
source: "https://docs.mai-mai.org/manual/adapters.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 适配器概览

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters.md](https://docs.mai-mai.org/manual/adapters.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
适配器负责把 QQ、Telegram、微信、Discord 等消息平台接入 MaiBot。不同适配器支持的平台、运行方式和维护状态不同，第一次部署建议优先选择维护活跃、文档完整的适配器。
| 适配器 | 支持平台 | 状态 | 简介 |
| --- | --- | --- | --- |
| [NapCat](./napcat.md) | QQ | 推荐使用 | 麦麦官方维护的 QQ 适配器，支持插件版和独立版，插件版是当前推荐方案。 |
| [GoCQ](./gocq.md) | QQ | 可用，偏旧 | 基于 go-cqhttp / AstralGocq 的 QQ 适配方案，适合已有 GoCQ 环境或特定需求。 |
| [SnowLuma](./snowluma.md) | QQ | 可用（测试中） | 新一代QQ适配方案 |
| [Telegram](./telegram.md) | Telegram | 社区适配 | Telegram平台适配方案 |
| [Discord](./discord.md) | Discord | 社区适配 | Discord平台适配方案 |
| [桌宠 适配器](https://gith

## 快速要点
- 下载或克隆适配器项目。
- 确认切换到适配器要求的插件分支。
- 将适配器目录放入 MaiBot 的 `plugins/` 目录。
- 启动 MaiBot，让插件系统自动加载适配器。
- 下载或克隆适配器项目。
- 按适配器文档安装依赖。
- 填写适配器自己的配置文件。
- 单独启动适配器进程。

## 标题树
- 适配器概览
  - 选择适配器
  - 旧版 / 社区适配器列表（可能未及时维护）
    - 插件版适配器
    - 独立版适配器
  - 配置连接
  - 确认连接成功
