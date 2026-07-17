
# 适配器开发指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/adapter-dev.md](https://docs.mai-mai.org/develop/adapter-dev.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 的适配器（Adapter）是指连接外部消息平台（如 QQ、Discord、Telegram 等）与 MaiBot 核心的桥接组件。本文档介绍 Platform IO 架构以及如何开发新的平台适配器。
MaiBot 的平台 IO 层（`src/platform_io/`）采用**驱动抽象 + 路由表 + Broker 管理器**的三层架构：
核心组件：
* **PlatformIODriver**：驱动抽象基类，定义收发消息的契约
* **PlatformIOManager**：Broker 管理器，统一协调路由、去重与状态跟踪
* **RouteTable**：路由绑定表，维护 RouteKey 到驱动的映射
* **DriverRegistry**：驱动注册表，管理已注册的驱动实例
MaiBot 提供两种适配器开发方式：
**@MessageGateway（插件式）**
: 通过 `@MessageGateway` 组件装饰器注册，以插件形式运行在插件运行时（Plugin Runtime）中
: 适用场景：独立部署的适配器插件、需要跨平台复用、不需要修改 MaiBot 源码
: import: `from m

## 快速要点
- **PlatformIODriver**：驱动抽象基类，定义收发消息的契约
- **PlatformIOManager**：Broker 管理器，统一协调路由、去重与状态跟踪
- **RouteTable**：路由绑定表，维护 RouteKey 到驱动的映射
- **DriverRegistry**：驱动注册表，管理已注册的驱动实例

## 标题树
- 适配器开发指南
  - 架构概览
  - 选择适配器开发模式
  - maim-message 集成
    - 消息段（Seg）
- 文本消息段
- 图片消息段
    - Legacy 驱动
  - 如何创建新适配器
    - 1. 继承 PlatformIODriver
    - 2. 实现 start/stop 生命周期
    - 3. 上报入站消息
    - 4. 注册驱动
- 创建驱动描述
- 创建驱动实例并注册
- 绑定路由
  - 插件消息网关驱动


---
*来源: https://docs.mai-mai.org/develop/adapter-dev.md*
