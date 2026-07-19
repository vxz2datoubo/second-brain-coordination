
# 🐳 Docker 部署指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/deployment/docker.md](https://docs.mai-mai.org/manual/deployment/docker.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
Docker 就像一个大盒子，把 MaiBot 和所有它需要的东西都打包好，一键就能跑起来！
需要安装：
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
第一次启动会自动生成配置文件，然后会停下来等你配置。
Docker 会同时启动几个服务，就像一个团队：
* **`core`** — MaiBot 核心，机器人的大脑 🧠
* **`napcat`** — QQ 连接器，让机器人能上 QQ 📱
* **`sqlite-web`** — 数据库工具，查看机器人记住的东西 📊
* **`TZ`** — 时区，例如 `Asia/Shanghai`
* **`EULA_AGREE`** — 跳过协议确认（高级用法，一般不用管）
* **`NAPCAT_UID`** — 用户 ID（一般用默认的）
* **`NAPCAT_GID`** — 用户组 ID（一般用默认的）
Docker 会把重要数据保存在你电脑的这些位置：
* **配置文件**：`./docker-con

## 快速要点
- **`core`** — MaiBot 核心，机器人的大脑 🧠
- **`napcat`** — QQ 连接器，让机器人能上 QQ 📱
- **`sqlite-web`** — 数据库工具，查看机器人记住的东西 📊
- **`TZ`** — 时区，例如 `Asia/Shanghai`
- **`EULA_AGREE`** — 跳过协议确认（高级用法，一般不用管）
- **`NAPCAT_UID`** — 用户 ID（一般用默认的）
- **`NAPCAT_GID`** — 用户组 ID（一般用默认的）
- **配置文件**：`./docker-config/mmc/`（机器人设置）

## 标题树
- 🐳 Docker 部署指南
  - 📋 准备工作
  - 🚀 5 分钟快速部署
    - 1. 下载 MaiBot
    - 2. 一键启动！
  - 📦 Docker 里都有啥？
  - ⚙️ 环境变量（高级用法）
    - 核心服务设置
    - QQ 服务设置
  - 💾 数据保存在哪里？
    - 机器人数据
    - QQ 数据
  - 🔌 端口说明
  - 🔗 连接 NapCat
    - 群聊收不到消息
  - 📋 完整步骤（一步一步来）
- 1. 下载
- 2. 首次启动（会生成配置文件）
- 3. 改配置（重要！）
- 打开 ./docker-config/mmc/bot_config.toml 填 QQ 号
- WebUI 配置也在 ./docker-config/mmc/bot_config.toml 的 [webui] 段
- 打开 ./docker-config/mmc/model_config.toml 填 API 密钥
- 打开 http://localhost:6099 登录 NapCat，并启用正向 WebSocket
- 启用 NapCat 适配器，并把适配器的 napcat_server.host 设为 napcat
- 群聊要把群号加入 NapCat 适配器的 group_list，或关闭聊天名单过滤
- 4. 重启让配置生效
- 5. 看日志
  - 🔧 常见问题
    - 容器启动就退出？
    - 内存不够？
    - 想停止机器人？
    - 想重新启动？


---
*来源: https://docs.mai-mai.org/manual/deployment/docker.md*
