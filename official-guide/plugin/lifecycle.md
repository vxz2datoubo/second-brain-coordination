
# 生命周期

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/lifecycle.md](https://docs.mai-mai.org/develop/plugin-dev/lifecycle.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 插件有三个生命周期方法：`on_load()`、`on_unload()` 和 `on_config_update()`。SDK 强制要求所有插件实现这三个方法，否则 Runner 会拒绝加载。
每个插件的 `plugin.py` 必须导出一个顶层 `create_plugin()` 函数，返回插件实例：
Runner 加载插件时：
1. 导入 `plugin.py` 模块
2. 调用 `create_plugin()` 获取插件实例
3. 注入 `PluginContext`（此时 `self.ctx` 可用）
4. 调用 `on_load()`
插件加载完成后的回调。Runner 在注入 `PluginContext` 并完成 capability bootstrap **之后**才调用此方法，因此可以在 `on_load()` 中直接使用 `self.ctx` 的所有能力代理。
**典型用途：**
* 初始化插件内部状态
* 调用 `self.ctx.gateway.update_state()` 上报消息网关状态
* 调用 `self.register_dynamic_api()` 注册动态 API 并

## 快速要点
- 导入 `plugin.py` 模块
- 调用 `create_plugin()` 获取插件实例
- 注入 `PluginContext`（此时 `self.ctx` 可用）
- 调用 `on_load()`
- 初始化插件内部状态
- 调用 `self.ctx.gateway.update_state()` 上报消息网关状态
- 调用 `self.register_dynamic_api()` 注册动态 API 并 `await self.sync_dynamic_apis()`
- 读取配置并初始化资源

## 标题树
- 生命周期
  - create\_plugin() 工厂函数
  - on\_load()
  - on\_unload()
  - on\_config\_update()
    - scope 取值
    - 示例
  - config\_reload\_subscriptions
  - 完整生命周期示例
  - 生命周期时序


---
*来源: https://docs.mai-mai.org/develop/plugin-dev/lifecycle.md*
