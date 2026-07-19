
# SnowLuma 适配器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters/snowluma.md](https://docs.mai-mai.org/manual/adapters/snowluma.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
SnowLuma 适配器让 MaiBot 通过 [SnowLuma](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter) 连接到 QQ 平台，收发消息、处理群聊和私聊。
SnowLuma 适配器目前处于测试阶段，功能基本可用，但可能存在未覆盖的边界情况。如遇问题欢迎在 [GitHub Issues](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter/issues) 反馈。
SnowLuma 适配器是一个 MaiBot 插件，通过 WebSocket 与 SnowLuma 进行双向通信。它的工作方式很简单：
* **入站**：SnowLuma 推送 QQ 消息到适配器，适配器转换后注入 MaiBot
* **出站**：MaiBot 生成的回复经适配器转换后，通过 SnowLuma 发送出去
与 NapCat 适配器不同，SnowLuma 适配器只有**插件模式**，不提供独立运行方式。适配器直接在 MaiBot 进程内运行，配置更少，部署更简单。
消息流转：**QQ → SnowLuma → 适配器插件（MaiB

## 快速要点
- **入站**：SnowLuma 推送 QQ 消息到适配器，适配器转换后注入 MaiBot
- **出站**：MaiBot 生成的回复经适配器转换后，通过 SnowLuma 发送出去
- 浏览器访问 `http://127.0.0.1:8001`，输入 Access Token 登录
- 点击左侧菜单 **"插件管理"**
- 找到 **"SnowLuma 适配器"**，点击启用开关
- 保存配置后重启 MaiBot（或等待插件热重载）
- **`enabled`** — 是否启用 SnowLuma 适配器。关闭时插件只注册消息网关，不会主动连接 SnowLuma。默认关闭
- **`config_version`** — 当前配置结构版本（自动管理，一般不需要手动修改）。默认 "1.0.0"

## 标题树
- SnowLuma 适配器
  - 简介
    - 适配器仓库
  - 安装
    - 第一步：获取适配器
- 进入 MaiBot 的 plugins 目录
- 克隆仓库
    - 第二步：配置 SnowLuma 连接
    - 第三步：配置 SnowLuma
    - 第四步：启动
    - 插件默认未启用
      - 方式一：编辑配置文件（推荐）
      - 方式二：通过 WebUI 启用
  - 配置参考
    - 插件设置 (`[plugin]`)
    - SnowLuma 连接 (`[luma_client]`)
    - 聊天过滤 (`[chat]`)
    - 消息过滤 (`[filters]`)
    - 完整配置示例
  - 验证与排查
    - 验证连接
    - 连不上怎么办？
    - 收不到消息？
    - 发不出消息？
    - 多实例部署


---
*来源: https://docs.mai-mai.org/manual/adapters/snowluma.md*
