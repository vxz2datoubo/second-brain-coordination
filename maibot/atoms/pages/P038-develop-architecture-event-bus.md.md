---
id: P038
type: source-page
title: "事件总线架构"
source: "https://docs.mai-mai.org/develop/architecture/event-bus.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 事件总线架构

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/event-bus.md](https://docs.mai-mai.org/develop/architecture/event-bus.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写。
MaiBot 的 EventBus 是进程内通信中枢，负责把分散在启动流程、聊天入口、LLM 管线、发送管线和插件运行时之间的事件，统一收敛到发布/订阅模型中。它不直接定义业务动作，也不负责具体功能执行，而是提供事件注册、事件触发、handler 排序、消息隔离和跨运行时桥接这些基础能力。
EventBus 位于 `maibot/src/core/event_bus.py`，属于 `core` 基础设施层。它和 `maibot/src/core/types.py` 中的 `EventType`、`MaiMessages` 共同构成主程序内部事件系统的最小闭环。
**EventBus** ：全局事件总线实例，提供 `subscribe()`、`unsubscribe()`、`emit()` 和任务取消能力。
**EventHandler** ：源码中的 handler 签名，接收 `Optional[MaiMessages]`，返回 `(continue_flag, modified_message)`。
**EventInterceptor** ：文档概念中的拦截型 handler，源

## 快速要点
- 本页以说明性内容为主，详见标题树和来源。

## 标题树
- 事件总线架构
  - 概述
  - 架构图
  - 核心概念
    - 拦截型 handler
    - 非拦截型 handler
    - EventType 枚举分类
    - handler 注册模型
  - 关键流程
    - emit 到 handler 匹配
    - 拦截型顺序执行
    - 非拦截型并发执行
    - IPC 插件运行时桥接
  - 模块交互
    - 与 core#类型系统协作
    - 与 plugin\_runtime#Hook调度器协作
    - 与 chat#消息入口调度协作
  - 事件类型枚举
    - 事件分类说明
  - 扩展点/Hook
  - 设计边界
  - 实现细节
    - handler 存储结构
    - 消息隔离策略
    - 异常策略
    - 任务取消
  - 典型调用示例
    - 注册拦截型 handler
    - 注册非拦截型 handler
    - 触发事件并处理结果
  - 与旧 events\_manager 的关系
  - 审计要点
  - 结论
