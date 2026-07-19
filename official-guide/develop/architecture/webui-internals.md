
# WebUI 内部机制

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/architecture/webui-internals.md](https://docs.mai-mai.org/develop/architecture/webui-internals.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot WebUI 是基于 FastAPI 的 Web 管理后端，提供插件管理、配置编辑、认证鉴权、WebSocket 通信等功能。本文详述其架构、安全机制和通信协议。
源码位置：`src/webui/app.py`
`create_app()` 创建 FastAPI 实例并配置中间件和路由：
只允许 localhost 来源（开发端口 + 服务端口）：
`_resolve_safe_static_file_path()` 通过 `resolve()` + `relative_to()` 双重检查防止路径穿越。
源码位置：`src/webui/core/security.py`
`TokenManager` 管理 WebUI 的访问令牌：
* `_create_new_token()` — 生成 64 位十六进制 Token（`secrets.token_hex(32)`）
* `get_token()` — 获取当前有效 Token
* `verify_token(token)` — 验证 Token（`secrets.compare_digest` 防时序攻击）
* `update_token(new_token)

## 快速要点
- `_create_new_token()` — 生成 64 位十六进制 Token（`secrets.token_hex(32)`）
- `get_token()` — 获取当前有效 Token
- `verify_token(token)` — 验证 Token（`secrets.compare_digest` 防时序攻击）
- `update_token(new_token)` — 更新 Token（需 ≥10 位，含大小写和特殊符号）
- `regenerate_token()` — 重新生成随机 Token
- `is_first_setup()` — 检查是否首次配置
- `mark_setup_completed()` — 标记配置完成
- **Cookie 名称** `maibot_session`

## 标题树
- WebUI 内部机制
  - 整体架构
  - FastAPI 应用工厂
    - CORS 配置
    - 静态文件安全
  - 认证与安全
    - Token 管理器
    - Cookie 认证
    - 限流器
    - 反爬虫中间件
  - WebSocket 通信
    - 统一 WebSocket
    - WebSocket 认证
    - 订阅域
  - 插件管理 IPC
    - 插件运行时架构
    - IPC 协议
    - 握手流程
    - 传输层
    - 编解码
  - 配置热重载
    - WebUI 热重载
    - 插件运行时热重载
  - 路由总览
    - 认证端点
  - 依赖注入
  - SSRF 防护
  - Hook 体系与 WebUI 的交互
  - 安全审计要点
    - 缓解建议


---
*来源: https://docs.mai-mai.org/develop/architecture/webui-internals.md*
