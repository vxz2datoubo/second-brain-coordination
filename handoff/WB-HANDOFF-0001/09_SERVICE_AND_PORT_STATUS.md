# 09_SERVICE_AND_PORT_STATUS — 服务与端口当前状态

> 生成时间: 2026-07-16 02:45 (UTC+8)
> 数据来源: `Get-NetTCPConnection -State Listen` + `bulletin/SERVICE-REGISTRY.md`

## 当前监听端口快照

| 端口 | 进程 | PID | 用途（推断/已知） | 是否登记在 SERVICE-REGISTRY | 当前在线 |
|------|------|-----|-------------------|-----------------------------|----------|
| 8766 | python | 10916 | SuperBrain 后端 API | ✅ | ✅ YES |
| 8000 | python | 2596 | MaiBot WebUI 主端口 | ✅ | ✅ YES |
| 8001 | python | 2596 | MaiBot WebUI 备用 | ✅ | ✅ YES |
| 8523 | python | 13908 | MaiBot Deskpet WebSocket | ✅ | ✅ YES |
| 9881 | python | 972 | TTS Bridge (Fish Audio TTS) | ✅ | ✅ YES |
| 8799 | — | — | ChatGPT 桥 (WorkBuddy 保留) | ✅ | ❌ 未监听（按需启动） |
| 18530 | — | — | STT Bridge (语音转文字) | ✅ | ❌ 未启动 |
| 7999 | — | — | Dashboard 预留 | ✅ | ❌ 预留 |
| 5284 | QClaw | 10184 | QClaw 算力引擎主端口 | ❌ (QClaw 维护) | ✅ YES |
| 14110 | QClaw | 10184 | QClaw 额外端口 | ❌ | ✅ YES |
| 14122 | 青山X | 1452 | (非本系统) | ❌ | ✅ YES |
| 19000 | QClaw | 10184 | QClaw 额外端口 | ❌ | ✅ YES |
| 14571 | TdxW | 14176 | 通达信客户端 | ❌ | ✅ YES |
| 8003 | LiblibAI | 13768 | LiblibAI 服务 | ❌ | ✅ YES |
| 8188 | python | 14528 | 未知 Python 服务 | ❌ | ✅ YES |
| 9439 | node | 5820 | Node.js 服务 | ❌ | ✅ YES |
| 9674-9676 | mihomo | 8504 | 代理服务 | ❌ | ✅ YES |
| 38324 | 青山 | 1452 | (非本系统) | ❌ | ✅ YES |

## 登记但未运行的服务

| 端口 | 服务 | 状态 | 启动命令 |
|------|------|------|----------|
| 8799 | ChatGPT 桥 | ⏸️ 保留 (按需) | WorkBuddy 内部 |
| 18530 | STT Bridge | ❌ 待修复 | `F:\aipengyou\plugins\maibot_deskpet-plugin\stt-bridge.py` |
| 7999 | Dashboard | ❌ 预留 | 未实现 |

## 服务健康检查方式

| 服务 | 健康检查方式 |
|------|-------------|
| SuperBrain (8766) | `curl http://127.0.0.1:8766/api/memory/status` |
| MaiBot (8000/8001) | `curl http://127.0.0.1:8000/api/status` |
| TTS (9881) | `curl http://127.0.0.1:9881/health` |
| ChatGPT 桥 (8799) | `curl http://127.0.0.1:8799/health` |

## 已知冲突与注意事项

1. **8000 和 8001 共享同一进程**（PID 2596），实际上是 MaiBot 的两个监听端口
2. **QClaw (5284/14110/19000)** 使用了多个端口，不在 SERVICE-REGISTRY 中登记。这些是 QClaw 从 `~/.qclaw/qclaw.json` 读取的动态端口。
3. **14571 (通达信)** 是 TDX 客户端的通信端口。TDX MCP 通过此端口与客户端通信。如果 TDX 客户端关闭，实时行情将不可用。
4. **8188** 的 Python 进程用途未知，建议后续确认。
5. **非本系统端口**（青山X、青山、mihomo代理等）不在本系统管理范围内。

## 启动顺序（维修）

```
SuperBrain (8766)           ← 第一步，无依赖
    │
    ├─→ MaiBot (8001+8523)  ← 第二步，依赖 SuperBrain
    │
    ├─→ TTS (9881)          ← 第三步，独立
    └─→ STT (18530)         ← 第三步，独立（当前故障）
```
