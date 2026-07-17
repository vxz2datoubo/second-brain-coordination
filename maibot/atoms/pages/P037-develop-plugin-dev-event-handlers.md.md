---
id: P037
type: source-page
title: "事件处理器"
source: "https://docs.mai-mai.org/develop/plugin-dev/event-handlers.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 事件处理器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/event-handlers.md](https://docs.mai-mai.org/develop/plugin-dev/event-handlers.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@EventHandler` 是用于订阅消息和工作流事件的组件装饰器。与 `@HookHandler` 的命名 Hook 点机制不同，`@EventHandler` 基于固定的 `EventType` 枚举值订阅事件，适合在消息处理流程的特定阶段进行拦截或观察。
* **`UNKNOWN`** — 未知事件
* **`ON_START`** — 插件启动
* **`ON_STOP`** — 插件停止
* **`ON_MESSAGE_PRE_PROCESS`** — 消息预处理阶段（过滤、拦截的最佳时机）
* **`ON_MESSAGE`** — 消息处理阶段
* **`ON_PLAN`** — 规划阶段
* **`POST_LLM`** — LLM 调用后（响应已生成）
* **`AFTER_LLM`** — LLM 调用完成后
* **`POST_SEND_PRE_PROCESS`** — 发送预处理阶段
* **`POST_SEND`** — 消息发送后
* **`AFTER_SEND`** — 消息发送完成后
`intercept_message` 控制 EventHandler 是否以阻塞方式参与消息处理链：
*

## 快速要点
- **`UNKNOWN`** — 未知事件
- **`ON_START`** — 插件启动
- **`ON_STOP`** — 插件停止
- **`ON_MESSAGE_PRE_PROCESS`** — 消息预处理阶段（过滤、拦截的最佳时机）
- **`ON_MESSAGE`** — 消息处理阶段
- **`ON_PLAN`** — 规划阶段
- **`POST_LLM`** — LLM 调用后（响应已生成）
- **`AFTER_LLM`** — LLM 调用完成后

## 标题树
- 事件处理器
  - 装饰器签名
  - EventType 事件类型
  - intercept\_message 参数
  - weight 权重
  - 基本用法
    - ON\_START：插件初始化
    - ON\_MESSAGE\_PRE\_PROCESS：消息过滤
    - ON\_MESSAGE：消息观察
    - AFTER\_LLM：LLM 响应后处理
    - POST\_SEND：发送后回调
  - 与 HookHandler 的区别
  - 事件处理流程
