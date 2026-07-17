
# Discord 适配器

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters/discord.md](https://docs.mai-mai.org/manual/adapters/discord.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
MaiBot 的 Discord 平台适配器插件，通过 Discord Gateway WebSocket 将 Discord Bot 与 MaiBot 无缝桥接，支持 Guild 频道、DM 私聊、Thread 子区、Reaction 及语音功能。
Discord 适配器源码：[litroenade/MaiBot-Discord-Adapter](https://github.com/litroenade/MaiBot-Discord-Adapter)
在使用适配器之前，你需要先在 Discord 上创建一个 Bot 并获取 Token。
1. 访问 [Discord Developer Portal](https://discord.com/developers/applications)
2. 点击右上角 **New Application**，输入应用名称并创建
3. 在左侧导航栏点击 **Bot**
4. 点击 **Reset Token**（或 **Add Bot**），复制 Bot Token 并妥善保存
在 Bot 页面向下滚动到 **Privileged Gateway Intents** 区域，启用以下

## 快速要点
- 访问 [Discord Developer Portal](https://discord.com/developers/applications)
- 点击右上角 **New Application**，输入应用名称并创建
- 在左侧导航栏点击 **Bot**
- 点击 **Reset Token**（或 **Add Bot**），复制 Bot Token 并妥善保存
- **Message Content Intent**（必须）— 不启用则无法读取消息内容
- **Presence Intent**（可选）— 需要监听用户在线状态时启用
- **Server Members Intent**（可选）— 需要获取完整成员列表时启用
- 在左侧导航栏点击 **OAuth2**

## 标题树
- Discord 适配器
  - 适配器仓库
  - 创建 Discord Bot
    - 第一步：创建应用和 Bot
    - 第二步：启用 Privileged Gateway Intents
    - 第三步：邀请 Bot 到服务器
    - 第四步：获取服务器/频道 ID
  - 安装
    - 依赖
  - 配置
    - 启用适配器
      - 方式一：编辑配置文件
      - 方式二：通过 WebUI 启用
    - 聊天过滤说明
  - 配置参考
    - `[plugin]` — 插件设置
    - `[connection]` — Discord 连接
    - `[chat]` — 聊天过滤
    - `[platform]` — 平台设置
    - `[filters]` — 消息过滤
    - `[voice]` — 语音功能
    - `[siliconflow_tts]` — SiliconFlow TTS
    - `[gptsovits_tts]` — GPT-SoVITS TTS
    - `[minimax_tts]` — MiniMax TTS
    - `[siliconflow_stt]` — SiliconFlow STT
    - `[aliyun_stt]` — 阿里云语音识别
    - `[tencent_stt]` — 腾讯云语音识别
  - 当前能力
    - 入站消息（Discord -> MaiBot）
    - 出站消息（MaiBot -> Discord）
    - 运行时能力
  - 验证连接
    - 常见问题


---
*来源: https://docs.mai-mai.org/manual/adapters/discord.md*
