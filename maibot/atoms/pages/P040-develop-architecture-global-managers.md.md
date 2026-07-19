---
id: P040
type: source-page
title: "全局管理器"
source: "https://docs.mai-mai.org/develop/architecture/global-managers.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# 全局管理器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/global-managers.md](https://docs.mai-mai.org/develop/architecture/global-managers.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文基于 code-map 快照编写
全局管理器模块（`src.manager`）负责提供应用级的单例服务，用于协调系统底层的通用基础能力。该模块设计轻量，不包含业务逻辑，仅作为纯粹的工具型服务，确保在整个应用生命周期内，基础任务调度和持久化存储拥有统一的入口和状态管理。
该模块不依赖其他 MaiBot 内部模块，仅使用 Python 标准库中的 `asyncio`、`json`、`os` 等基础包。两个核心管理器（AsyncTaskManager 和 LocalStorageManager）互不依赖，各自独立运行。这种设计确保了管理器模块可以作为系统的基础设施层，被 MainSystem、各适配器以及插件按需引用，而不会引入循环依赖。
异步任务管理器负责管理后台异步任务的生命周期。它允许系统在不阻塞主逻辑的前提下，运行定时心跳、数据统计等循环任务。
AsyncTaskManager
职责：管理任务的注册、启动、取消和优雅停止。
关键组件：
AsyncTask：任务基类。定义了 `wait_before_start`（启动延迟）和 `run_interval`（运行间隔），支持一次性任务或循环任务。
abort\_flag：

## 快速要点
- 若 `wait_before_start > 0`，先执行 `asyncio.sleep(wait_before_start)` 实现延迟启动。
- 主循环条件为 `while not self.abort_flag`，持续检测全局中止标志。
- 每轮循环中调用 `run()` 执行业务逻辑，`run()` 内的异常会被 `try/except` 捕获并记录，防止单个任务崩溃影响整个管理器。
- `run()` 返回后，若 `run_interval > 0`，通过 `asyncio.sleep(run_interval)` 休眠指定间隔，实现周期执行；否则任务仅执行一次后退出。
- 若 `wait_before_start > 0`，先执行 `asyncio.sleep(wait_before_start)`，实现延迟启动，避免系统启动阶段的任务竞争。
- 进入 `while not self.abort_flag` 循环，只要 `abort_flag` 未被设置，就持续执行 `run()`。
- 每次 `run()` 返回后，若 `run_interval > 0`，通过 `asyncio.sleep(run_interval)` 休眠指定间隔，实现固定周期的循环执行。
- 若 `run_interval <= 0`，任务在完成一次 `run()` 后自动退出，适用于一次性任务。

## 标题树
- 全局管理器
  - 概述
  - 架构图
  - 核心概念
    - AsyncTaskManager
    - LocalStorageManager
  - 关键流程
    - 定时任务执行流程
    - 本地存储读写流程
  - 与 MainSystem 的交互
  - Hook/扩展点
