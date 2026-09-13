# 洛雪 WB 桥（luoxue-wb-bridge）

> 让 MaiBot 的洛雪用 WorkBuddy 引擎思考、用 MCP 伸手、接入第二大脑智慧体的项目。
> **项目主页 = 本目录**（second-brain-coordination/apps/luoxue-wb-bridge）。
> 开一个新 WorkBuddy 窗口时，指到本目录即可继续此项目的工作。

## 源码与运行时的关系（重要）

```
本仓库（源码真源 Source of Truth）
  apps/luoxue-wb-bridge/wb_llm_bridge.py   ← 改代码永远改这里
        │  deploy.ps1 同步（单向）
        ▼
F:\aipengyou\wb_bridge\wb_llm_bridge.py   ← 部署运行时（MaiBot 本地基础设施）
```

**MaiBot 本体不迁入本仓库**——它是第三方应用的部署运行时（venv/模型/数据库共 6GB+，路径被全系统引用），
物理迁移零收益、高风险。集成靠 **API 松耦合**（8900 桥 / 8766 SuperBrain），不靠物理共址。
改桥代码的流程：改本仓库 → 跑 `deploy.ps1` → 重启桥。

## 目标架构

洛雪（MaiBot 1.2.4 桌宠）全 AI 能力接入 WorkBuddy 引擎 + 第二大脑，逐步退役 SiliconFlow：

| 能力 | 引擎 | 状态 |
|---|---|---|
| 聊天/规划/记忆总结（8 个 LLM 任务） | WB 桥 → codebuddy CLI（glm/flash） | ✅ 2026-09-12 上线 |
| 识图（vlm：表情包识别/图片描述） | WB 桥 CLI 看图分支（wb-vlm） | ✅ 2026-09-12 上线（端到端实测 18s） |
| 记忆向量（embedding） | SiliconFlow Qwen3-Embedding-8B（4096 维） | ✅ 保留（¥0.29/M ≈ ¥5/年，检索质量 MTEB 榜第一，不值得省） |
| 语音合成（TTS） | Fish Audio 在线 API | ✅ 现状（插件自管理） |
| 语音识别（STT） | SenseVoice 本地（894MB fp32） | ✅ 2026-09-12 落地（0.2s/次） |
| 控制电脑 | MCP servers（MaiBot 原生客户端） | ⏳ Phase B 待做 |
| 接入第二大脑智慧体 | SuperBrain 8766 API | ⏳ Phase C 待做 |

## 三阶段路线图

### Phase A ✅ 大脑换引擎（已完成）
LLM 桥：聊天/规划/识图走 codebuddy CLI，SF 留 embedding 兜底降级链。

### Phase B ⏳ 装上手（下一步）
MCP servers（bot_config.toml `[mcp]` 段，MaiBot 原生 MCP 客户端）：
- `filesystem` server → 洛雪读写文件
- 桌面控制 server → 洛雪操作电脑
- 工具直接进 planner 决策流，无需写插件

### Phase C ⏳ 接入第二大脑智慧体（本仓库的核心愿景）
洛雪通过 SuperBrain API（localhost:8766）成为第二大脑的"人格化前端"：
- **知识检索**：`GET /api/retrieve/search?q=...` → 洛雪能回答"我们之前讨论过 XX 吗"
- **知识摄入**：`POST /api/digest/text` → 洛雪把对话中的新知识自动存入第二大脑
- **日程感知**：`/api/events/upcoming` + `/api/events/conflicts` → 洛雪主动提醒日程冲突
- **决策上下文**：`second_brain_decision_context` → 洛雪给建议前先查历史教训
- 实现载体：MaiBot 插件（HTTP 调用）或桥内新增 `/v1/tools/*` 端点，二选一待定

## 文件地图

| 文件 | 位置 | 说明 |
|---|---|---|
| 桥源码（真源） | 本目录 `wb_llm_bridge.py` | 纯标准库 OpenAI 兼容代理，端口 8900 |
| 部署脚本 | 本目录 `deploy.ps1` | 同步源码 → F:\aipengyou\wb_bridge\ |
| MaiBot 模型配置 | `F:\aipengyou\config\model_config.toml` | provider WorkBuddy(8900) + wb-flash/wb-glm/wb-vlm + 任务路由 |
| 启动集成 | `F:\aipengyou\yi_jian_qi_dong.ps1` | [WBBR] 段自动拉起桥（8900 已占用自动跳过） |
| 运行文档（18 页精读笔记） | `F:\aipengyou\docs\maibot-dev-docs\_LEARNINGS.md` | MaiBot 开发文档精华，读这个就够 |
| 台账 | `F:\aipengyou\麦麦工程-公告栏与台账.md` | 升级/修复历史 |
| 工作日志 | `F:\SecondBrainWorkspace\.workbuddy\memory\2026-09-12.md` | 每日详细过程 |

## 硬规则（踩坑换来，勿犯）

1. **CLI 必带独立 `SERVER__PORT`**（默认 8694 与 WorkBuddy 应用 prewarm 冲突→静默死锁）。桥内 18701 起轮换
2. **prompt 必走 stdin**（argv 经 cmd 转发截断换行 + 32K 上限）
3. **长驻服务脱离会话启动**：`schtasks /create + /run`（Start-Process 撞 Path/PATH 环境冲突；挂 WorkBuddy 后台任务会被会话回收）
4. **改 MaiBot 配置必须停进程后串行改**（并行 Edit 写竞争 + 运行中改被热重载覆盖）
5. **桥并发 ≤3** 不放开（机器资源 + 账号通道双保险）
6. `ELECTRON_RUN_AS_NODE=1` 会从 WorkBuddy 会话继承，测桌宠/CLI 前必须清
7. **改桥代码只在仓库改，deploy.ps1 同步**（禁止直接改运行时副本造成双真源漂移）

## 待办

- [ ] planner 走桥的 tool_calls 实测（桥回纯文本，MaiBot 有 XML 兜底，需验证）
- [ ] MCP servers 配置（Phase B）
- [ ] SuperBrain 接入插件/PoC（Phase C，先做"洛雪查第二大脑"单点）
- [ ] 记忆数据库定期备份到 GitHub（守护"记忆跟随很久很久"）
- [ ] wb-flash 映射改回 deepseek-v4.1-flash（额度恢复后）
- [ ] 观察 CLI 延迟，体验差则聊天退 SF、低频任务留桥
- [ ] （可选升级）Ollama 本地 embedding，彻底零 API 依赖

## 运维速查

```powershell
# 启动全家桶（含桥自动拉起）
F:\aipengyou\yi_jian_qi_dong.ps1
# 单独拉桥（脱离会话）
schtasks /create /tn wbbr_t /tr "F:\aipengyou\.venv\Scripts\python.exe F:\aipengyou\wb_bridge\wb_llm_bridge.py" /sc once /st 23:57 /f; schtasks /run /tn wbbr_t; schtasks /delete /tn wbbr_t /f
# 验证
curl http://127.0.0.1:8900/v1/models
# 日志
tail F:\aipengyou\logs\wb_bridge.log
```
