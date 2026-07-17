
# 架构设计

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture.md](https://docs.mai-mai.org/develop/architecture.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写，作为架构文档的导航中心。它把 MaiBot 的架构拆成 12 篇专题文档，并用 Runner/Worker 进程模型与 MainSystem 初始化流程串起主入口。
**消息处理管线** ：从平台消息入站到出站发送的完整链路，详见 [消息管线](architecture/message-pipeline.md)。
**插件运行时架构** ：插件生命周期、Host/Runner 双进程通信、组件注册和 Hook 分发，详见 [插件开发文档](./plugin-dev/)、[生命周期](./plugin-dev/lifecycle.md)、[工具](./plugin-dev/tools.md)、[Hook](./plugin-dev/hooks.md)。
**Platform IO 架构** ：MaiBot 与适配器之间的发送、接收、路由、去重和出站跟踪，详见 [PlatformIO 驱动开发](./adapter-dev/platform-io.md)。
**事件总线（EventBus）** ：事件总线（EventBus）是 MaiBot 全系统通信中枢，提供发布/订阅模型，支持拦截型（同

## 快速要点
- **Runner 进程**：守护进程，负责启动、监控 Worker 子进程。当 Worker 以退出码 42 退出时，Runner 会自动重新启动 Worker（热重启机制）。当 Runner 收到 Ctrl+C 信号时，会优雅终止 Worker。
- **Worker 进程**：实际执行业务逻辑的进程。设置环境变量 `MAIBOT_WORKER_PROCESS=1` 后进入 Worker 模式，执行 `MainSystem` 的初始化和任务调度。
- 启动配置文件热重载监视器
- 注册 A\_memorix 配置重载回调（`register_config_reload_callback()`）
- 加载 Prompt 模板
- 注册定时任务（在线时间统计、统计输出、遥测心跳）
- 启动插件运行时（`PluginRuntimeManager.start()`），建立双子进程（内置插件 + 第三方插件）
- 启动 A\_memorix 长期记忆服务

## 标题树
- 架构设计
  - 快速入口
  - Runner/Worker 进程模型
  - MainSystem 初始化流程
  - 新增架构入口
  - 消息处理管线
  - 插件运行时架构
  - Platform IO 架构
  - 本节文档索引


---
*来源: https://docs.mai-mai.org/develop/architecture.md*
