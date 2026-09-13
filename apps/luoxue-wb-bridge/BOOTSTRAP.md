# 🚀 新窗口点火提示词（BOOTSTRAP）

> **用法**：开新 WorkBuddy 窗口，指向 `F:\SecondBrainWorkspace\second-brain-coordination`，
> 把下面整段贴进对话即可无缝接手。改完任何代码/配置记得回来更新本文档的"当前状态"。

---

```
接手"洛雪 WB 桥"项目（luoxue-wb-bridge）。

【第一步：按顺序读完再动手】
1. apps/luoxue-wb-bridge/README.md —— 项目宪章：架构/三阶段路线图/7条硬规则/待办
2. F:\aipengyou\麦麦工程-公告栏与台账.md —— 运行时台账（升级/修复历史）
3. F:\aipengyou\docs\maibot-dev-docs\_LEARNINGS.md —— MaiBot 开发文档 18 页精读精华

【环境事实（勿重新探索）】
- 洛雪运行时 = F:\aipengyou（MaiBot 1.2.4，不迁移）；桥源码真源 = 本仓库
  apps/luoxue-wb-bridge/，改代码流程：改仓库 → deploy.ps1 同步 → 重启桥
- 桥 = 127.0.0.1:8900，OpenAI 兼容代理，MaiBot 全部 LLM 任务走它调 codebuddy CLI
- 下一阶段：Phase B（bot_config.toml [mcp] 给洛雪装 MCP 工具手）
  → Phase C（SuperBrain 8766 API：洛雪查/存第二大脑、日程感知）

【当前状态（2026-09-12 晚）】
- Phase A 完成：聊天/规划/识图走桥，embedding 留 SF（8B，¥5/年）
- 遗留：①wb-flash 映射临时指向 glm-5.3-flash，额度恢复后改回
  deepseek-v4.1-flash（wb_llm_bridge.py MODEL_MAP 有标记）
  ②planner 走桥的 tool_calls 待实测（桥回纯文本，MaiBot 有 XML 兜底）
  ③记忆库定期备份 GitHub 待做

【开工动作】
先报全家桶端口体检：8000/8001/8766/8900/9881/18530/18531 哪些活哪些死，
死了的按 README 运维速查拉起，再问我今天做什么。

【红线】
README 的 7 条硬规则必须遵守（8694 端口冲突/stdin 传prompt/
schtasks 脱离会话启动/停进程改配置/并发≤3/清 ELECTRON_RUN_AS_NODE/单真源）。
```

---

## 为什么这样设计（给波仔的说明）

| 你的问题 | 答案 |
|---|---|
| 聊天记录在新项目里吗？ | WorkBuddy 聊天记录**按窗口目录隔离**。新目录 = 新上下文，旧的不会自动带过去 |
| 在原窗口继续行不行？ | 行，而且**这两天的收尾建议就在原窗口**（F:\SecondBrainWorkspace 下的窗口共享同一份项目记忆） |
| 什么时候需要新窗口？ | 专门推进洛雪项目、或当前窗口上下文太长变笨时 → 指到治理仓根目录 + 贴本提示词 |
| 为什么不直接指 apps/luoxue-wb-bridge 子目录？ | 目录太深会割裂项目记忆，且治理仓的 AGENTS.md 在根目录生效。指根目录即可 |

## 持久上下文层（跨窗口真正的记忆）

提示词只是"点火器"，真正的记忆靠这四份文件（都有明确路径，任何窗口都能读到）：
1. 本项目 README.md（宪章 + 路线图 + 待办）
2. F:\aipengyou\麦麦工程-公告栏与台账.md（运行时历史）
3. F:\aipengyou\docs\maibot-dev-docs\_LEARNINGS.md（领域知识）
4. F:\SecondBrainWorkspace\.workbuddy\memory\YYYY-MM-DD.md（每日详细过程）

**每次会话收尾，把新进展写回这四份，提示词就不用改。**
