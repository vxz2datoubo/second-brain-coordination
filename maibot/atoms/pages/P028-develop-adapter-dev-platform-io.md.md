---
id: P028
type: source-page
title: "PlatformIO 驱动"
source: "https://docs.mai-mai.org/develop/adapter-dev/platform-io.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# PlatformIO 驱动

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/adapter-dev/platform-io.md](https://docs.mai-mai.org/develop/adapter-dev/platform-io.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
PlatformIO 驱动是 MaiBot 平台 IO 层的核心抽象。本文档详细介绍驱动的接口定义、核心类型，以及如何实现和注册一个自定义驱动。
`PlatformIODriver`（定义在 `src/platform_io/drivers/base.py`）是所有平台 IO 驱动必须继承的抽象基类：
* **`send_message(message, route_key, metadata)`** — 通过具体驱动发送消息，返回 `DeliveryReceipt`。这是唯一必须实现的抽象方法
* **`start()`** — 启动驱动生命周期（默认空实现）
* **`stop()`** — 停止驱动生命周期（默认空实现）
驱动收到外部平台消息后，需构造 `InboundMessageEnvelope` 并调用 `emit_inbound()` 上报：
`emit_inbound` 返回 `True` 表示消息被 Broker 接受并继续转发，`False` 表示被拒绝（未配置入站回调或消息被去重过滤）。
`RouteKey` 是路由决策的唯一键，采用三层结构：
路由解析遵循**从最具体到最宽泛**的回退顺序：`plat

## 快速要点
- **`send_message(message, route_key, metadata)`** — 通过具体驱动发送消息，返回 `DeliveryReceipt`。这是唯一必须实现的抽象方法
- **`start()`** — 启动驱动生命周期（默认空实现）
- **`stop()`** — 停止驱动生命周期（默认空实现）
- **`PENDING`** — 待发送
- **`SENT`** — 已发送
- **`FAILED`** — 发送失败
- **`DROPPED`** — 已丢弃

## 标题树
- PlatformIO 驱动
  - PlatformIODriver 基类
    - 必须实现的方法
    - 可选覆盖的钩子
    - 入站消息上报
  - 核心类型
    - RouteKey — 路由键
- → [RouteKey("qq", "123", "group_456"), RouteKey("qq", "123", None), RouteKey("qq", None, "group_456"), RouteKey("qq", None, None)]
    - InboundMessageEnvelope — 入站消息封装
    - DeliveryReceipt — 出站回执
    - DriverDescriptor — 驱动描述
  - 实现并注册驱动
    - 完整示例
    - 注册与路由绑定
- 描述符
- 注册
- 绑定发送路由
- 绑定接收路由
