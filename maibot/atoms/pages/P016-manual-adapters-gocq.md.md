---
id: P016
type: source-page
title: "MaiBot GoCQ Adapter 文档"
source: "https://docs.mai-mai.org/manual/adapters/gocq.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# MaiBot GoCQ Adapter 文档

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/adapters/gocq.md](https://docs.mai-mai.org/manual/adapters/gocq.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
比较老的框架，部分账号可能在这个框架上拥有更低的风控概率
首先，你需要安装 GoCQ 本身，以下列出了一些不同的GoCQ版本：
[AstralGocq](https://github.com/ProtocolScience/AstralGocq)
[gocq-http(New)](https://github.com/LagrangeDev/go-cqhttp)
在这些项目中的release页面下载对应的版本，这里只提供Windows版本的安装教程。
下载完成后，将可执行文件解压到一个文件夹中。
双击打开GoCQ本体，会弹出一个提示框，要求你生成安全启动脚本，点"确认"生成启动脚本。
关闭GoCQ本体，使用安全启动脚本启动GoCQ，此时会要求选择连接方式，选择 `反向WebSocket`。待生成config.yml配置后，关闭窗口。
打开 `config.yml`，修改以下配置：
使用启动脚本启动GoCQ，进行扫码登录。
如果要求验证，请使用浏览器打开提供的链接，然后按下F12，打开网络(或Network)选项卡，正常进行验证，验证完成后等待几秒，会弹出验证成功的消息，这时看到你的开发人员工具，点击最下面那个请求，打开响应，

## 快速要点
- ws-reverse:

## 标题树
- MaiBot GoCQ Adapter 文档
  - GoCQ 配置
    - 安装 GoCQ
    - 配置GoCQ
- 连接服务列表
  - GoCQ Adapter 配置
    - 安装 GoCQ Adapter
    - 配置 GoCQ Adapter
