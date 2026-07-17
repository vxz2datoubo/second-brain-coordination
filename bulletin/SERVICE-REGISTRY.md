# 🔌 第二大脑后台服务注册表

> ⚠️ **强制规则**：任何 AI 工具（QClaw、WorkBuddy、Codex 等）在启动新服务前，**必须先查这个表**，避免端口冲突。
>
> 最后更新：2026-07-13 00:25 — TTS Bridge 改由 MaiBot Deskpet 插件自动管理（on_load 启动 / on_unload 终止），不再需要手动启动或 yi_jian_qi_dong.ps1 接管
> 文件位置：`F:\aidanao\bulletin\SERVICE-REGISTRY.md`

---

## 快速查找

```
端口       服务名称              状态      进程/脚本
───────   ──────────────────    ────     ────────────────────────────
 8000     备用（已弃用）          ❌       旧 MaiBot WebUI（已搬家到 8001）
 8001     MaiBot WebUI          ✅       bot.py (F:\aipengyou)
 8523     MaiBot Deskpet WS     ✅       bot.py → deskpet plugin
 8766     SuperBrain 后端       ✅       server.py (F:\aidanao)
 8799     ChatGPT 桥            ⏸️       chatgpt-bridge (WorkBuddy, 按需启动)
 9881     TTS Bridge            ✅       deskpet plugin on_load 自动拉起
18530     STT Bridge            ✅       stt-bridge.py
 7999     Dashboard（备用）      ❌       未使用
```

---

## 详细详情

### 8766 — SuperBrain 后端

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aidanao` |
| **启动命令** | `F:\aipengyou\.venv\Scripts\python.exe server.py` |
| **工作目录** | `F:\aidanao` |
| **协议** | HTTP REST API |
| **端点前缀** | `/api/memory`, `/api/conflict`, `/api/emotion`, `/api/goal`, `/api/task`, `/api/agent`, `/api/evolve` |
| **依赖** | 无（独立启动，其他服务依赖它） |
| **窗口** | 后台 Hidden |
| **启动顺序** | 第 1 个 |
| **MaiBot 插件** | superbrain_bridge v0.4.0（通过 http://127.0.0.1:8766 调用） |
| **状态** | ✅ 运行中（2026-07-12） |

### 8001 — MaiBot WebUI

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aipengyou` |
| **启动命令** | `F:\aipengyou\.venv\Scripts\python.exe bot.py` |
| **工作目录** | `F:\aipengyou` |
| **协议** | HTTP + WebSocket |
| **窗口** | 独立终端（yi_jian_qi_dong.ps1 的主窗口） |
| **启动顺序** | 第 2 个（依赖 SuperBrain 已启动） |
| **状态** | ✅ 运行中（2026-07-12） |

### 8523 — MaiBot Deskpet WebSocket

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aipengyou` |
| **启动方式** | MaiBot 内置 deskpet-plugin 自动监听 |
| **协议** | WebSocket（Live2D 桌宠通信） |
| **说明** | 随 MaiBot 一起启动，无需单独管理 |
| **启动顺序** | 随 MaiBot（第 2 个） |
| **状态** | ✅ 运行中（2026-07-12） |

### 9881 — TTS Bridge (Fish Audio + Piper + 浏览器回退)

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aipengyou` |
| **启动命令** | `F:\aipengyou\.venv\Scripts\python.exe plugins\maibot_deskpet-plugin\gpt-sovits-bridge.py` |
| **工作目录** | `F:\aipengyou` |
| **协议** | HTTP API |
| **功能** | 文字转语音（桌宠说话） |
| **后端链路** | Fish Audio TTS → Piper 本地 → 浏览器 SpeechSynthesis |
| **启动顺序** | 第 3 个（独立，可与 STT 并行） |
| **状态** | ✅ 运行中（2026-07-12） |

### 18530 — STT Bridge (语音转文字)

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aipengyou` |
| **启动命令** | `F:\aipengyou\.venv\Scripts\python.exe plugins\maibot_deskpet-plugin\stt-bridge.py` |
| **工作目录** | `F:\aipengyou` |
| **协议** | HTTP API |
| **功能** | 语音转文字（用户跟桌宠说话） |
| **启动顺序** | 第 3 个（独立，可与 TTS 并行） |
| **状态** | ❌ 未启动（2026-07-12，待修复） |

### 7999 — Dashboard（预留）

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aipengyou\dashboard` |
| **说明** | 监控仪表盘，暂未启用 |
| **状态** | ❌ 预留 |

### 8799 — ChatGPT 桥（WorkBuddy）

| 字段 | 值 |
|------|-----|
| **项目目录** | `F:\aidanao`（ChatGPT bridge extension/本机桥） |
| **协议** | HTTP（localhost 本机桥，复用浏览器登录态调 ChatGPT） |
| **功能** | WorkBuddy 通过本机桥向已登录 ChatGPT 提问并取回答，结果摄入第二大脑 |
| **登记者** | WorkBuddy |
| **说明** | 按需启动，非常驻；此端口为 WorkBuddy 保留，勿占用 |
| **状态** | ⏸️ 保留（当前未监听，用到时启动） |

---

## ⚠️ 端口占用规则

### 已占用区间（禁止新服务使用）

| 范围 | 用途 |
|------|------|
| 8000-8010 | MaiBot 及其变体 |
| 8520-8530 | WebSocket（桌宠/通信） |
| 8760-8770 | SuperBrain / 脑桥服务 |
| 9880-9890 | TTS / 语音 |
| 18500-18600 | STT / 语音输入 |
| 7990-8010 | Dashboard / 监控 |

### 分配规则

1. **新增服务**：选端口号时，不能与上表任何已用端口或区间冲突
2. **新增区间**：如果要占用一个区间（如 9000-9010），必须在这个文件里登记
3. **端口释放**：服务下线后，不要把端口号直接删掉——改成 `❌ 已释放 — 可回收`，至少保留 7 天
4. **冲突检查**：启动脚本里加 `Get-NetTCPConnection -LocalPort <port>` 检测

---

## 📋 启动顺序（依赖链）

```
SuperBrain (8766)           ← 第一步，无依赖
    │
    ├─→ MaiBot (8001+8523)  ← 第二步，依赖 8766
    │
    └─→ TTS (9881)          ← 第三步，独立并行
    └─→ STT (18530)         ← 第三步，独立并行
```

### 启动脚本

| 脚本 | 路径 | 说明 |
|------|------|------|
| 一键启动 | `F:\aipengyou\yi_jian_qi_dong.ps1` | 含清理+启动全部服务 |
| SuperBrain 单独 | `F:\aidanao\server.py` | | 
| TTS 单独 | `F:\aipengyou\plugins\maibot_deskpet-plugin\gpt-sovits-bridge.py` | |
| STT 单独 | `F:\aipengyou\plugins\maibot_deskpet-plugin\stt-bridge.py` | |

---

## 🔧 给 AI 工具的指令

读到这个文件的 AI 工具（QClaw / WorkBuddy / Codex 等）请遵守：

1. **启动新服务前** → 先 grep 这个文件确认端口没冲突
2. **服务启动后** → 在这个文件里登记（端口/名称/目录/启动命令/依赖）
3. **服务下线** → 改状态为 `❌ 已释放 (YYYY-MM-DD)`，不要删行
4. **启动时** → 先 `Get-NetTCPConnection` 检测端口，被占用就换端口或报告冲突
