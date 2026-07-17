---
id: P062
type: source-page
title: "表情系统内部架构"
source: "https://docs.mai-mai.org/develop/architecture/emoji-internals.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 表情系统内部架构

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/emoji-internals.md](https://docs.mai-mai.org/develop/architecture/emoji-internals.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
本文面向开发者，说明 `emoji_system/` 目录、`send_emoji` 内置工具、表情包数据库、内存缓存、VLM 描述生成、PIL 拼图合成和定期维护之间的协作关系。它与 `docs/manual/features/emoji-system.md` 的用户视角互补，不重复介绍如何管理表情包，也不把 WebUI 操作当成内部实现。
**定位** ：表情系统是 MaiBot 的视觉表达素材层。它负责把图片文件、数据库记录、情绪标签、使用次数和维护状态组织成可被推理引擎调用的能力。
**核心单例** ：`EmojiManager` 是表情包的集中管理器。它保存 `self.emojis` 内存池，维护 `self._emoji_num` 数量，注册配置热重载回调，并调度描述构建和定期维护任务。
**用户边界** ：用户文档解释“什么时候会发表情包、如何上传和审核”。本文解释“为什么能选中这张图、图片如何变成 base64、使用次数如何写入数据库”。
**实现边界** ：当前实现不把表情包选择权重直接交给 `ExpressionLearner`。表情包有 `query_count

## 快速要点
- 本页以说明性内容为主，详见标题树和来源。

## 标题树
- 表情系统内部架构
  - 概述
  - 架构图
  - 核心概念
  - 表情包加载
  - 表情匹配算法
  - 关键流程一：表情选择算法
  - PIL 图片合成
  - 关键流程二：PIL 图片合成
  - 表情发送
  - 与 Maisaka 的交互
  - 与学习模块的交互
  - 关键流程三：拼图筛选
  - 定期维护
  - 错误与回退
  - 开发调试入口
  - 设计约束
  - 小结
