
# Hook 处理器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/hooks.md](https://docs.mai-mai.org/develop/plugin-dev/hooks.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@HookHandler` 是 MaiBot 插件系统中用于订阅**命名 Hook 点**的组件装饰器。主程序在关键执行点触发命名 Hook，所有订阅该 Hook 的插件处理器按固定规则调度执行，从而实现消息拦截、改写和观察。
SDK 2.0 中 `WorkflowStep` 已被 `@HookHandler` 取代。旧代码仍在使用 `WorkflowStep` 时会在运行时抛出 `RuntimeError`，这是一个不向后兼容的更改，必须迁移到 `@HookHandler`。
* 串行执行，**可以修改**传入的 `kwargs`
* 返回 `modified_kwargs` 可以更新后续处理器接收的参数
* 返回 `action: "abort"` 可以终止整个 Hook 调用链
* 适合需要拦截或改写消息的场景
* 后台并发执行，**只读**旁路观察
* 不参与主流程控制，返回的 `modified_kwargs` 和 `abort` 请求会被忽略
* 适合日志记录、数据分析等不影响主流程的场景
同一模式内的处理器按 `order` 排序执行：
* **`HookOrder.EARLY`** — 优先执行，适合前置拦

## 快速要点
- 串行执行，**可以修改**传入的 `kwargs`
- 返回 `modified_kwargs` 可以更新后续处理器接收的参数
- 返回 `action: "abort"` 可以终止整个 Hook 调用链
- 适合需要拦截或改写消息的场景
- 后台并发执行，**只读**旁路观察
- 不参与主流程控制，返回的 `modified_kwargs` 和 `abort` 请求会被忽略
- 适合日志记录、数据分析等不影响主流程的场景
- **`HookOrder.EARLY`** — 优先执行，适合前置拦截

## 标题树
- Hook 处理器
  - 装饰器签名
  - 处理模式
    - BLOCKING（阻塞模式）
    - OBSERVE（观察模式）
  - 顺序槽位
  - 异常处理策略
  - 调度顺序
  - 基本用法
    - 阻塞模式示例：拦截并修改消息
    - 观察模式示例：日志记录
    - 阻塞模式示例：修改发送参数
  - 内置 Hook 清单
    - 聊天消息链
    - 命令执行链
    - 表情包链
    - 黑话（Jargon）链
    - 表达方式（Expression）链
    - 发送服务链
    - Maisaka 规划器链
    - Maisaka 回复器链
      - 在 replyer 请求前切换模型或追加提示词
  - Host 校验规则
    - 表达方式选择链
  - 处理器返回值
  - Hook 分发流程
  - 迁移指南：WorkflowStep → HookHandler
- 旧代码（SDK 1.x）— 不再可用
- 新代码（SDK 2.0）


---
*来源: https://docs.mai-mai.org/develop/plugin-dev/hooks.md*
