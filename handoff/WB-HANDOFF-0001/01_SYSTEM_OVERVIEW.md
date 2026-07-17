# 01_SYSTEM_OVERVIEW — WorkBuddy 运行环境概况

> 生成时间: 2026-07-16 02:45 (UTC+8)
> WorkBuddy 版本: 1.x (内置于 WorkBuddy Desktop)
> 时区: (UTC+08:00) 北京，重庆，香港特别行政区，乌鲁木齐

## 操作系统

| 项目 | 值 |
|------|-----|
| OS | Microsoft Windows 11 专业版 |
| 版本 | 10.0.22631 Build 22631 |

## 硬件

| 项目 | 值 |
|------|-----|
| CPU | Intel Core i7-6700 @ 3.40GHz |
| 核心数 | 4 物理核心 / 8 逻辑核心 |
| 内存 | 32 GB |
| F: 盘总容量 | 22323 GB (~21.8 TB) |
| F: 盘可用 | 4336 GB (~4.2 TB) |
| GPU | 未在本次审计中检测（ComfyUI/liblibAI 环境使用 GPU） |

## 运行时

| 运行时 | 路径 | 版本 |
|--------|------|------|
| Python (managed, preferred) | `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe` | **3.13.14** |
| Python (system, fallback) | `D:\LiblibAI-workspace\comfyui-deploy-win\python_embeded\python.exe` | 3.12.7 |
| Node.js (managed, preferred) | `C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\node.exe` | **v22.22.2** |
| Node.js (system, fallback) | `C:\Program Files\nodejs\node.exe` | (NODE_OPTIONS 冲突，无法查询) |
| Git | 系统 PATH | (全局安装) |

## Python 环境与核心库

**Managed Python 3.13.14 已安装的关键库**：

| 库 | 版本 | 用途 |
|----|------|------|
| pandas | 3.0.3 | 数据处理与分析 |
| numpy | 2.5.1 | 数值计算 |
| akshare | 1.18.64 | A股数据获取 |
| requests | 2.34.2 | HTTP 请求 |
| beautifulsoup4 | 4.15.0 | HTML 解析 |

> 注：此列表仅限于 managed Python。还有用于 MaiBot/SuperBrain 的独立 venv (`F:\aipengyou\.venv`，Python 3.12) 以及 ComfyUI 中的嵌入式 Python。

## 运行中的关键服务（当前快照）

| 端口 | 进程 | 用途 |
|------|------|------|
| 8766 | python (10916) | SuperBrain 后端 API |
| 8000-8001 | python (2596) | MaiBot WebUI |
| 8523 | python (13908) | MaiBot Deskpet WebSocket |
| 9881 | python (972) | TTS Bridge |
| 14571 | TdxW (14176) | 通达信客户端 |
| 9439 | node (5820) | Node.js 服务 |
| 5284 | QClaw (10184) | QClaw 算力引擎 |
| 14110,14122,19000 | QClaw (10184) | QClaw 额外端口 |
| 8003 | LiblibAI (13768) | LiblibAI 服务 |
| 8188 | python (14528) | 未知 Python 服务 |
| 9674-9676 | mihomo (8504) | 代理服务 |

## WorkBuddy 虚拟环境

- **Managed Python 默认 venv**：`C:\Users\Administrator\.workbuddy\binaries\python\envs\default`
- **Node.js 工作空间**：`C:\Users\Administrator\.workbuddy\binaries\node\workspace\node_modules`
- **项目工作目录**：`F:\aidanao`

## 安全声明

本文件不包含密码、Token、API Key、账号信息、券商凭据或私钥。
