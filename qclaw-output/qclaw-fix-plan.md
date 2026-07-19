# QClaw 输出 | 2026-06-17 14:29
> 模型: openclaw/default | 端口: 6362 | Token: 0

我先快速验证一下报告中的关键文件位置，以便给出精确的修复步骤。

代码库实际在 F:/ai/，让我读取关键文件来精确分析。

我已经验证了所有 12 个问题的具体位置和上下文。现在给出完整的修复方案。

# Super Jarvis 系统修复方案

**来源**: Codex 审查报告（已读取 12 个问题全清单）
**已验证**: 所有问题位置均已 grep 确认 ✅

---

## 📊 修复方案总表（按 P0 > P1 > P2 排序）

| # | 优先级 | 问题描述 | 修复步骤 | 执行者 | 前置条件 | 风险 |
|---|--------|----------|----------|--------|----------|------|
| 1 | **P0-1** | `server.py:118` `GET /api/events/record` 引用未定义变量 `data`，100% 触发 `NameError` | 1) 定位 lambda 行<br>2) 整行删除（POST 版已存在）<br>3) curl GET 验证 404（不是 500）<br>4) curl POST 验证仍可用 | **Codex** | 无 | 🟢极低 |
| 2 | **P1-2** | `core/graph.py:317 和 :358` 重复定义 `get_full_graph()`，后者覆盖前者 | 1) grep 全库确认调用方<br>2) 删除 :317 版本（保留 :358）<br>3) 启动 server 测 `/api/knowledge-graph` | **Codex** | 无 | 🟢极低 |
| 3 | **P1-3** | `_ping_qclaw()` 只读 `qclaw.json`，`_resolve_token()` 还会回退 `openclaw.json`，健康检查误判 | 1) 提取 `_get_token()` 公共函数，优先级：`openclaw.json.gateway.auth.token` → `qclaw.json.token` → FALLBACK<br>2) `_ping_qclaw()` 改用 `_get_token()`<br>3) 失败时打日志<br>4) 写单测覆盖 | **Codex** | 无 | 🟢低 |
| 4 | **P1-4** | `mcp/qclaw_bridge.py:9` 硬编码 `QCLAW_TOKEN` 与 `core.qclaw.QClawBridge` 分叉，QClaw 换 token 后 MCP 失联 | 1) 删硬编码<br>2) `from core.qclaw import QClawBridge`<br>3) `call_qclaw()` 改用 `QClawBridge.ask()`<br>4) WorkBuddy 调 `qclaw_ask` 验证 | **Codex** | P1-3 修完 | 🟡中 |
| 5 | **P1-5** | Codex 默认配置三处分叉：`core/codex_bridge.py`(read-only, gpt-5.5) / `mcp/codex_bridge.py`(workspace-write, gpt-5.5) / `CODEBUDDY.md`(workspace-write, **gpt-5-codex** ❌) | 1) **WorkBuddy 拍板**统一标准（建议 `workspace-write + gpt-5.5`）<br>2) Codex 改 `core/codex_bridge.py` 默认值<br>3) Codex 改 `CODEBUDDY.md` 的 `gpt-5-codex` → `gpt-5.5`<br>4) 新建 `config/codex_defaults.json` 统一读取<br>5) `codex_doctor` 验证 | **WorkBuddy**(决策)+ **Codex**(改) | WorkBuddy 先拍板 | 🟡中 |
| 6 | **P1-7** | `mcp/fs_tools.py search_brain()` 用 **GET** `/api/retrieve/search`，但 server.py 只在 **POST** 中注册该端点 → 必 404 | 1) 方案 A 推荐：在 `do_GET` 加路由 `"/api/retrieve/search": lambda: self.search({"query": params.get("q",[""])[0], "top_k": int(params.get("top_k",["10"])[0])})`<br>2) MCP 调 `brain_search("测试")` 验证 | **Codex** | 无 | 🟢低 |
| 7 | **P1-6** | 决策咨询 POST 传 `category`，但 `server.py:241 search()` 只读 `query` 和 `top_k`，category 被静默丢弃 | 1) 读 `core/tfidf.py` 确认 search 接口<br>2) `search()` 加 `cat = data.get("category")` 分支<br>3) 若 `SearchEngine.search` 不支持 category，同步扩展<br>4) 测 `category="investment"` 只返回该类 | **Codex** | 需先读 tfidf.py | 🟢低 |
| 8 | **P1-8** | `qclaw-output/codex-runs/test-mcp.json` 是中文 Markdown 内容但扩展名是 .json，其他工具按 JSON 解析必报错 | 1) `mv test-mcp.json test-mcp.md`<br>2) 扫描 `qclaw-output/` 全部 .json 验证可解析<br>3) `core/codex_bridge.py` 加规范：摘要→.md，指标→.json | **Codex** | 无 | 🟢极低 |
| 9 | **P1-1** | 知识图谱 11 个 `category=inbox` 残留 + 23 个孤立节点 + 12 条 `cross_category:...` 非标准 relation | 1) **备份** `cp knowledge-graph.json ...backup-pre-cleanup.json`<br>2) 写 `tools/cleanup_kg.py`：<br>&nbsp;&nbsp;a) inbox 节点跑 `auto_link()`，未匹配的存 `data/pending/` 等 review<br>&nbsp;&nbsp;b) 孤立节点降阈值 `auto_link(0.15)` 补救<br>&nbsp;&nbsp;c) `cross_category:xxx` 映射到 `references/related_to/derived_from`<br>3) 跑脚本输出 `cleanup_report.json`<br>4) WorkBuddy 在 `/app/graph.html` 可视化 review 11 个 inbox 归类 | **Codex**(脚本)+ **WorkBuddy**(review) | P0 修完 | 🟡中 |
| 10 | **P2-3** | `server.py:201 stats()` 直接 `mem["meta"]["total_interactions"]` 下标访问，memory-index 损坏即 500 | 1) 改 `.get()` 链：`mem.get("meta", {}).get("total_interactions", 0)`<br>2) 同样兜底 `sync` 字段<br>3) 临时挪走 memory-index.json 测返回默认值 | **Codex** | 无 | 🟢极低 |
| 11 | **P2-1** | schema 偏宽松：缺 `additionalProperties` 策略、缺 `user_request/output/task` 三个 .schema.json | 1) 新建 `schemas/user_request.schema.json`<br>2) 新建 `schemas/output.schema.json`<br>3) 新建 `schemas/task.schema.json`（补 `started_at/completed_at/output_path/error`）<br>4) `data/schema.md` 加 `"additionalProperties": false`<br>5) server.py 启动时 `jsonschema.validate()` | **Codex** | 无 | 🟡中 |
| 12 | **P2-2** | MCP 协议实现最小化：缺标准 JSON-RPC 错误响应、通知处理、`initialized` 握手 | 1) 新建 `mcp/base_mcp_server.py` 抽象基类，统一错误码/通知/握手<br>2) 三个 bridge 改继承基类<br>3) 写 `tests/test_mcp_protocol.py` 集成测试 | **Codex** | 无 | 🟢低 |

---

## 🎯 执行分工小结

- **Codex 独自执行**: 11 个（P0-1, P1-2/3/4/6/7/8, P1-1脚本部分, P2-1/2/3）
- **WorkBuddy 必须参与**: 2 个
  - **P1-5 决策**（拍板统一默认 sandbox + model）
  - **P1-1 review**（11 个 inbox 节点人工归类）
- **总工时**: 约 3-4 小时

## ⚡ 建议执行顺序

```
Phase 1 (10分钟) → P0-1 立竿见影
Phase 2 (1.5h)  → P1-2 → P1-3 → P1-4 → P1-5(等决策) → P1-7
Phase 3 (1h)    → P1-6 → P1-8 → P1-1(脚本+review)
Phase 4 (1h)    → P2-3 → P2-1 → P2-2
```

详细方案、验收命令、代码 diff 片段已写入 `F:/ai/super-jarvis/outputs/qclaw/fix_plan_20260617.md`（12KB）。

[SAVE: super_jarvis_fix_plan_20260617.md]