---
id: MB-0002
type: concept-atom
title: "MaiBot 部署路径"
snapshot: "2026-06-22"
tags: [部署, 安装, 运行]
---

# MaiBot 部署路径

## 原子结论
MaiBot 官方文档把部署路径分为源码安装、一键包部署和 Docker 部署。源码安装适合希望直接开发或调试的人；一键包适合快速使用；Docker 适合偏服务化和隔离部署的人。

## 关键事实
- WebUI 默认地址是 `http://127.0.0.1:8001`。
- QQ 场景通常需要 NapCat 和适配器；插件版 NapCat 适配器是当前更推荐的接入方式。
- 常见启动问题集中在 Python 版本、配置文件、端口占用、API Key 和网络连通性。

## 实操提醒
优先使用 WebUI 完成基础配置；排查时先看日志，再分别确认模型服务、适配器连接、平台权限和端口占用。

## 来源页
- [https://docs.mai-mai.org/manual/deployment.md](https://docs.mai-mai.org/manual/deployment.md)
- [https://docs.mai-mai.org/manual/deployment/installation.md](https://docs.mai-mai.org/manual/deployment/installation.md)
- [https://docs.mai-mai.org/manual/deployment/docker.md](https://docs.mai-mai.org/manual/deployment/docker.md)
- [https://docs.mai-mai.org/manual/deployment/one_key.md](https://docs.mai-mai.org/manual/deployment/one_key.md)

## 本地来源笔记
- [[P068-manual-deployment.md|MaiBot 简介]]
- [[P044-manual-deployment-installation.md|📦 MaiBot 安装指南]]
- [[P012-manual-deployment-docker.md|🐳 Docker 部署指南]]
- [[P036-manual-deployment-onekey.md|一键包部署教程]]
