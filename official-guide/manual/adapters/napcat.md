
# 使用NapCat和适配器连接麦麦

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters/napcat.md](https://docs.mai-mai.org/manual/adapters/napcat.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
你可以通过 **NapCat** 来获取QQ的消息和信息
然后通过 **适配器**将这些消息翻译并发送给MaiBot
NapCat 适配器的源码：[Mai-with-u/MaiBot-Napcat-Adapter](https://github.com/Mai-with-u/MaiBot-Napcat-Adapter)
你可以在WebUI的插件商店直接找到NapCat Adapter适配器，直接安装即可
⚠️安装后需要手动进行**启用**，你可以在webui的插件管理看到哪些插件被启用了
**将适配器目录放入 MaiBot 的 `plugins/` 文件夹中**
1. 打开 NapCat 的网页界面
2. 找到 "正向 WebSocket" 或 "WebSocket 服务器" 设置
3. 启用正向 WebSocket 服务器，监听端口需要和 NapCat Adapter插件中的 `端口` 一致 （`plugins/MaiBot-Napcat-Adapter/config.toml` 中 `napcat_server.port` ）
4. 如果你设置的WebSocket连接有访问Token，将这个Token复制并填写到**Ad

## 快速要点
- 打开 NapCat 的网页界面
- 找到 "正向 WebSocket" 或 "WebSocket 服务器" 设置
- 启用正向 WebSocket 服务器，监听端口需要和 NapCat Adapter插件中的 `端口` 一致 （`plugins/MaiBot-Napcat-Adapter/config.toml` 中 `napcat_server.port` ）
- 如果你设置的WebSocket连接有访问Token，将这个Token复制并填写到**Adapter插件配置**的**访问令牌**配置项中。（注意不是napcat webui的token也不是maibot webui的token！！！）
- **`ws_server_host`** — 服务器地址，本地用 `127.0.0.1`，服务器用实际 IP
- **`ws_server_port`** — 端口号，默认 `8000`，改了就记住这个数字
- **`auth_token`** — 密码验证，空着就行，不用管
- 打开 NapCat 的网页界面

## 标题树
- 使用NapCat和适配器连接麦麦
  - 适配器仓库
  - 安装适配器
- 克隆插件
  - 配置 NapCat
  - 启动
      - 群聊白名单
  - 独立模式使用指南 🔧
- 克隆 main 分支（默认）
- 或者如果已克隆，确保在 main 分支
    - 配置 MaiBot
    - 安装 NapCat
    - 设置 NapCat 连接
    - 登录 QQ
    - 连接步骤
- Docker 一键启动（推荐）
- 手动启动
- 终端 1：启动 NapCat
- 终端 2：启动适配器 (进入适配器目录运行)
- 终端 3：uv run python bot.py
  - 一些问题 ✅
    - 连不上怎么办？
    - 收不到消息？


---
*来源: https://docs.mai-mai.org/manual/adapters/napcat.md*
