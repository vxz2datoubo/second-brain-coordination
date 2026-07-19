---
id: P034
type: source-page
title: "Vibe Coding 插件开发指南"
source: "https://docs.mai-mai.org/develop/plugin-dev/vibe-coding.md"
snapshot: "2026-06-22"
tags: [maibot, 官方文档, 来源页]
---

# Vibe Coding 插件开发指南

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/develop/plugin-dev/vibe-coding.md](https://docs.mai-mai.org/develop/plugin-dev/vibe-coding.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
本文面向使用 AI 辅助编写 MaiBot 插件的开发者。目标是把插件需求拆成 AI 容易理解、容易验证、不会误改主程序的工作单元。
把下面这段作为给 AI 的首段上下文，再补充你的具体需求：
* 插件目录固定为 `plugins/<plugin-name>/`；如果插件需要自己的忽略规则，在插件目录内新增 `.gitignore`，不要修改仓库根目录 `.gitignore`。
* 插件入口固定为 `plugin.py`，工厂函数固定为 `create_plugin()`。
* 插件元信息固定为 `_manifest.json`，运行配置放在 `config.toml`。
* 新插件不要修改 `src/`、`dashboard/`、`config/` 等主程序目录；确实需要主程序能力时，先说明原因、影响面和替代方案，再请求许可。
* 不要把本地实验数据、日志、临时脚本、个人密钥、token、cookie、数据库文件提交进插件。
* 依赖以 `_manifest.json` 的 `dependencies` 为准；只有在维护 MaiBot 主程序依赖时才同步 `pyproject.toml` 和 `requirements.

## 快速要点
- 插件目录固定为 `plugins/<plugin-name>/`；如果插件需要自己的忽略规则，在插件目录内新增 `.gitignore`，不要修改仓库根目录 `.gitignore`。
- 插件入口固定为 `plugin.py`，工厂函数固定为 `create_plugin()`。
- 插件元信息固定为 `_manifest.json`，运行配置放在 `config.toml`。
- 新插件不要修改 `src/`、`dashboard/`、`config/` 等主程序目录；确实需要主程序能力时，先说明原因、影响面和替代方案，再请求许可。
- 不要把本地实验数据、日志、临时脚本、个人密钥、token、cookie、数据库文件提交进插件。
- 依赖以 `_manifest.json` 的 `dependencies` 为准；只有在维护 MaiBot 主程序依赖时才同步 `pyproject.toml` 和 `requirements.txt`。
- `manifest_version` 当前固定为 `2`。
- `id` 使用小写反向域名或作者前缀，例如 `com.example.my-plugin`。

## 标题树
- Vibe Coding 插件开发指南
  - AI 任务简报
  - 开发边界
  - 最小目录结构
  - Manifest 要点
  - 代码骨架
  - 组件选择
  - Tool 编写要点
  - 发送消息要点
  - 配置要点
  - AI 生成代码检查清单
  - 推荐提示词
    - 生成新插件
    - 修改已有插件
    - 排查插件问题
  - 测试建议
  - 发布前检查
