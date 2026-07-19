---
id: P063
type: source-page
title: "表达学习架构"
source: "https://docs.mai-mai.org/develop/architecture/expression-learning.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 表达学习架构

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/expression-learning.md](https://docs.mai-mai.org/develop/architecture/expression-learning.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
MaiBot 的 `learners/` 学习模块是一个自主进化子系统，旨在让机器人通过观察用户对话，自动习得特定的表达习惯、行为模式和社群文化。它不依赖于预定义的规则集，而是通过“观察 $\rightarrow$ 分析 $\rightarrow$ 存储 $\rightarrow$ 影响”的闭环，实现从“通用智能体”到“社群成员”的身份转变。
学习模块由四类专门的学习器协作完成：行为学习器（BehaviorLearner）、表情学习器（ExpressionLearner）、俚语挖掘器（JargonMiner）和场景聚类器（SceneClusterer）。
学习模块在消息管线中处于异步分析位置。它不直接阻塞消息的实时回复，而是在消息流经管线时触发分析任务，并将结果持久化，从而在后续的推理循环中影响回复质量。
行为学习器负责捕捉用户与 Bot 交互的深层模式。它不关注具体的词汇，而关注“在什么场景下，采取什么行为，会得到什么结果”。
**核心机制**：通过 LLM 解析聊天历史，生成“场景-行为-结果”三元组。如果某种行为模式（如：在用户沮丧时使用幽默化解）获得了正向反馈，该模式的权重将增

## 快速要点
- 本页以说明性内容为主，详见标题树和来源。

## 标题树
- 表达学习架构
  - 学习流转架构
  - 学习器详解
    - BehaviorLearner（行为学习器）
    - ExpressionLearner（表情学习器）
    - JargonMiner（俚语挖掘器）
    - SceneClusterer（场景聚类器）
  - 学习配置示例
  - 核心处理流程
  - 与其它模块的交互
    - Maisaka 推理引擎
    - 表情包系统
    - 聊天系统
  - Hook 扩展点
