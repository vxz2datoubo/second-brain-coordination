---
id: MB-0016
type: concept-atom
title: "Prompt 模板需要多语言同步"
snapshot: "2026-06-22"
tags: [Prompt, 模板, 多语言]
---

# Prompt 模板需要多语言同步

## 原子结论
Prompt 模板系统控制 MaiBot 推理时喂给模型的文本结构。项目约定修改 prompt 模板时，需要同步修改中文、英文和日文文件，保持语义对齐。

## 关键事实
- Prompt 会影响回复风格、角色一致性、工具使用和上下文解释。
- Prompt 问题常与 Maisaka、模型配置、记忆检索和表达学习耦合。
- 多语言模板不同步会造成不同语言环境下行为不一致。

## 研究入口
调整回复风格、工具调用指导、系统角色约束时，先定位对应模板，再检查三语文件是否需要同步。

## 来源页
- [https://docs.mai-mai.org/develop/architecture/prompt-templates.md](https://docs.mai-mai.org/develop/architecture/prompt-templates.md)

## 本地来源笔记
- [[P029-develop-architecture-prompt-templates.md|Prompt 模板系统]]
