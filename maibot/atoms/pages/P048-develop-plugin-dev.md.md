---
id: P048
type: source-page
title: "插件开发指南"
source: "https://docs.mai-mai.org/develop/plugin-dev.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 插件开发指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev.md](https://docs.mai-mai.org/develop/plugin-dev.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 的插件系统采用 Host/Runner IPC 架构，插件代码运行在独立的子进程中，通过 msgpack 编码的 RPC 协议与主进程通信。本节介绍插件系统的架构原理、开发流程和核心概念。
* **PluginRuntimeManager**：单例管理器，管理 Builtin 和 Third-party 两个 Supervisor
* **PluginSupervisor**：负责 Runner 子进程的启动、停止、健康检查和插件热重载
* **ComponentRegistry**：组件注册表，管理所有插件声明的 Tool、Command 等组件
* **HookDispatcher**：Hook 分发器，将命名 Hook 调用分发到对应 Supervisor
* 每种 Supervisor 各自管理一个独立的 Runner 子进程
* 通过 `PluginLoader` 发现和加载插件
* 通过 `RPCClient` 与 Host 通信
* 在插件加载后注入 `PluginContext`，再调用 `on_load()` 生命周期方法
* **编解码**：使用 msgpack 格式进行二进制序列化（`Ms

## 快速要点
- **PluginRuntimeManager**：单例管理器，管理 Builtin 和 Third-party 两个 Supervisor
- **PluginSupervisor**：负责 Runner 子进程的启动、停止、健康检查和插件热重载
- **ComponentRegistry**：组件注册表，管理所有插件声明的 Tool、Command 等组件
- **HookDispatcher**：Hook 分发器，将命名 Hook 调用分发到对应 Supervisor
- 每种 Supervisor 各自管理一个独立的 Runner 子进程
- 通过 `PluginLoader` 发现和加载插件
- 通过 `RPCClient` 与 Host 通信
- 在插件加载后注入 `PluginContext`，再调用 `on_load()` 生命周期方法

## 标题树
- 插件开发指南
  - 架构概览
    - Host（主进程侧）
    - Runner（子进程侧）
    - 通信协议
  - 快速开始
    - 1. 安装 SDK
    - 2. 创建插件目录
    - 3. 编写 Manifest
    - 4. 编写插件代码
    - 5. 安装与运行
  - 核心概念
    - 插件基类
    - 组件装饰器
    - 能力代理
- 上下文访问
- 能力代理
    - 配置模型
  - 目录结构约定
  - 内置插件与第三方插件
  - 下一步
