---
id: MB-0009
type: concept-atom
title: "记忆系统与 A_Memorix"
snapshot: "2026-06-22"
tags: [记忆, A_Memorix, Embedding]
---

# 记忆系统与 A_Memorix

## 原子结论
MaiBot 的记忆能力面向“长期了解用户和聊天环境”，A_Memorix 是新记忆系统相关配置和实现区域。记忆通常依赖 Embedding，用于语义检索、关联和持久化。

## 关键事实
- 用户侧关注机器人如何记住你、如何管理记忆。
- 配置侧关注 A_Memorix 的启用、参数和行为开关。
- 架构侧关注记忆写入、检索、维护和调用链路。

## 项目约束
任何涉及 `src/A_memorix` 的实现改动，必须先阅读 `src/A_memorix/MODIFICATION_POLICY.md` 并遵守归属约束。

## 来源页
- [https://docs.mai-mai.org/manual/features/memory-system.md](https://docs.mai-mai.org/manual/features/memory-system.md)
- [https://docs.mai-mai.org/manual/configuration/amemorix-config.md](https://docs.mai-mai.org/manual/configuration/amemorix-config.md)
- [https://docs.mai-mai.org/develop/architecture/memory-system.md](https://docs.mai-mai.org/develop/architecture/memory-system.md)

## 本地来源笔记
- [[P019-manual-features-memory-system.md|MaiBot 怎么记住你 🧠]]
- [[P004-manual-configuration-amemorix-config.md|A\_Memorix 记忆系统配置]]
- [[P064-develop-architecture-memory-system.md|记忆系统（A-Memorix）]]
