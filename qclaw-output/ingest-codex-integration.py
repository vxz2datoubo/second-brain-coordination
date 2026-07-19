"""Codex 集成方案 — 让 Codex 在 WorkBuddy 管理框架下做事

波仔要求:
1. Codex 比 QClaw 地位高 (更聪明)
2. 但必须在管理框架下做事 (不独立行动)
3. 沙箱安全 + 自动追溯 + 自动摄入第二大脑

实现: 3 层架构
  第 1 层: 决策前门 (decision_consult) — 任何"用 Codex"前先查教训
  第 2 层: Codex Bridge (codex_bridge.py) — Python API
  第 3 层: MCP 连接器 (mcp/codex_bridge.py + mcp.json) — WorkBuddy 内置工具

状态: 2026-06-16 落地, 已通过 doctor 验证 (14 ok / 4 warn / 2 fail).
"""
import urllib.request, json

text = r"""Codex 集成方案 (WorkBuddy 高级智能体层)

波仔要求: 让 WorkBuddy 调用 Codex 办事, Codex 比 QClaw 聪明, 但要受管理框架约束.

## 3 层架构

### 第 1 层: 决策前门 (decision_consult)
- 任何"用 Codex"决定前, 必须先调 before_decision("用 Codex 跑 XX")
- 命中"降级/未验证/未确认用户期望"等教训时, 弹警告

### 第 2 层: Codex Bridge (Python API)
- 路径: F:\ai\core\codex_bridge.py
- 入口: from core.codex_bridge import CodexBridge, quick_ask
- 能力: run / resume / review / doctor / ingest_to_brain
- 默认沙箱: workspace-write (允许改 F:/ai, 严禁默认 danger)

### 第 3 层: MCP 连接器 (WorkBuddy 内置工具)
- 注册: C:\Users\Administrator\.workbuddy\mcp.json (新增 codex-bridge)
- 桥接: F:\ai\mcp\codex_bridge.py (MCP stdio 协议)
- 暴露 4 个工具: codex_run / codex_resume / codex_review / codex_doctor

## 与 QClaw 的协同

| 任务 | 用谁 | 触发 |
|------|------|------|
| 单次分析/总结/翻译 | QClaw | 波仔消息以 q: 开头 |
| 复杂多步/改文件/跑命令 | Codex | "用 codex"/"重构"/"改这个文件" |
| 简单查询/闲聊 | WorkBuddy 自己 | 默认 |

## 关键约束 (波仔硬规则)

1. 沙箱默认 workspace-write, 严禁默认开 danger-full-access
2. 每个 Codex 任务自动摄入第二大脑 (留 session_id + output_file 可追溯)
3. Codex 失败/网络不通时, 明确告诉波仔, 不假装调通
4. Codex 地位高于 QClaw 但仍受 WorkBuddy 框架管, 不是独立 Agent

## 已知健康 (2026-06-16 doctor)

- 14 ok / 4 warn / 2 fail
- ⚠ websocket: Responses WebSocket 超时, HTTPS fallback 可用
- ✗ reachability: 部分 provider endpoint 不可达
- 结论: Codex 当前可能不稳定, 调用要带超时+重试, 失败立即报告

## 文件清单

- Python 桥接: F:\ai\core\codex_bridge.py
- MCP 桥接: F:\ai\mcp\codex_bridge.py
- MCP 注册: C:\Users\Administrator\.workbuddy\mcp.json
- 技能: C:\Users\Administrator\.workbuddy\skills\codex-bridge\SKILL.md
- 二进制: C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\codex.cmd
- 输出: F:\ai\qclaw-output\codex-runs\

## 触发词

- 「用 codex」/「调 codex」/「让 codex 干」 → 调 Codex
- 「代码生成」/「重构」/「改文件」/「修 bug」 → 默认 Codex
- 「分析」/「总结」/「翻译」/「提取要点」(无 q: 前缀) → WorkBuddy 自己做
- q: 前缀 → QClaw 算力
"""

data = json.dumps({
    'title': 'Codex集成方案-WorkBuddy高级智能体层',
    'text': text,
    'tags': 'Codex,智能体,MCP,WorkBuddy,QClaw,沙箱',
    'source': 'workbuddy-architecture',
    'category': 'tech-ai'
}).encode('utf-8')
req = urllib.request.Request('http://localhost:8766/api/digest/text', data=data, headers={'Content-Type': 'application/json'})
print(json.loads(urllib.request.urlopen(req, timeout=5).read()))
