---
id: P056
type: source-page
title: "消息网关"
source: "https://docs.mai-mai.org/develop/plugin-dev/message-gateway.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 消息网关

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/message-gateway.md](https://docs.mai-mai.org/develop/plugin-dev/message-gateway.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@MessageGateway` 装饰器用于声明消息网关组件，实现 MaiBot 与外部消息平台（如 QQ、Discord 等）的双向消息路由。消息网关是平台适配器的核心组件，负责出站消息发送和入站消息注入。
* **`"send"`** → `MessageGatewayRouteType.SEND` — 出站：Host → 插件 → 外部平台
* **`"receive"`** → `MessageGatewayRouteType.RECEIVE` — 入站：外部平台 → 插件 → Host
* **`"duplex"`** → `MessageGatewayRouteType.DUPLEX` — 双向：同时支持出站和入站
`route_type` 也接受 `"recv"` 和 `"recive"` 作为 `"receive"` 的别名。
* `await self.ctx.gateway.route_message(gateway_name, message_dict, route_metadata=None, ...)` — 注入入站消息到 Host
* `await self.ctx.gateway.update

## 快速要点
- **`"send"`** → `MessageGatewayRouteType.SEND` — 出站：Host → 插件 → 外部平台
- **`"receive"`** → `MessageGatewayRouteType.RECEIVE` — 入站：外部平台 → 插件 → Host
- **`"duplex"`** → `MessageGatewayRouteType.DUPLEX` — 双向：同时支持出站和入站
- `await self.ctx.gateway.route_message(gateway_name, message_dict, route_metadata=None, ...)` — 注入入站消息到 Host
- `await self.ctx.gateway.update_state(gateway_name, ready, platform="", account_id="", scope="", metadata=None)` — 上报网关状态
- 只有 `ready=True` 的网关才会被主程序选中进行消息路由
- `route_type="send"` 或 `"duplex"` 且 `ready=True` 的网关可被 Platform IO 选中处理出站消息
- `route_type="receive"` 或 `"duplex"` 且 `ready=True` 的网关可通过 `ctx.gateway.route_message()` 注入入站消息

## 标题树
- 消息网关
  - 装饰器签名
  - 路由类型
  - ctx.gateway 能力代理
    - 状态管理
  - 完整适配器示例
  - 仅入站网关示例
  - 网关处理器参数
  - 消息路由流程
    - 出站流程（Host → 外部平台）
    - 入站流程（外部平台 → Host）
  - 网关生命周期
  - 平台字段说明
