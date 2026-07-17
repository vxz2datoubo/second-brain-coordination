
# API 组件

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/api-components.md](https://docs.mai-mai.org/develop/plugin-dev/api-components.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
`@API` 装饰器用于声明插件间通信的 API 接口。其他插件可以通过 `ctx.api.call()` 调用这些 API，实现插件间的功能互操作。
API 的唯一标识名称。同一插件内不能有重复名称的 API。其他插件通过 `插件 ID + API 名称` 来定位和调用。
* **`False`**（默认） — 仅插件内部可见，其他插件无法调用
* **`True`** — 公开 API，其他插件可通过 `ctx.api.call()` 调用
API 版本号，默认为 `"1"`。用于 API 版本管理，当需要不兼容更新时可以递增版本号。
通过 `@API` 装饰器在插件类上直接声明 API：
除了使用 `@API` 装饰器静态声明外，还可以在运行时动态注册和注销 API。动态 API 适合需要根据配置或运行时条件决定是否暴露 API 的场景。
* `self.register_dynamic_api(name, handler, *, description, version, public, handler_name, **metadata)` — 注册动态 API
* `self.unregister_dynamic_

## 快速要点
- **`False`**（默认） — 仅插件内部可见，其他插件无法调用
- **`True`** — 公开 API，其他插件可通过 `ctx.api.call()` 调用
- `self.register_dynamic_api(name, handler, *, description, version, public, handler_name, **metadata)` — 注册动态 API
- `self.unregister_dynamic_api(name, *, version="1")` — 注销动态 API
- `self.clear_dynamic_apis()` — 清空所有动态 API
- `await self.sync_dynamic_apis(*, offline_reason="动态 API 已下线")` — 将动态 API 同步到主程序
- `await self.ctx.api.call(api_name, *, version="", **kwargs)` — 调用其他插件的 API
- `await self.ctx.api.get(api_name, *, version="")` — 获取 API 信息

## 标题树
- API 组件
  - 装饰器签名
  - 参数说明
    - name
    - public
    - version
  - 静态 API 示例
  - 动态 API 注册
    - 动态 API 方法
    - 动态注册示例
    - 动态注销示例
  - 调用其他插件的 API
    - ctx.api 方法
    - 调用示例
    - 查询 API 信息
- 获取特定 API 的详细信息
  - API 设计建议
    - 命名规范
    - 版本管理
    - 参数设计
  - 静态 API 与动态 API 对比


---
*来源: https://docs.mai-mai.org/develop/plugin-dev/api-components.md*
