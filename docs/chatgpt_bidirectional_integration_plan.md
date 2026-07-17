# ChatGPT ↔ 第二大脑 双向对接 · 系统化实施任务清单

> 目标：让 ChatGPT 能直接连入本系统（第二大脑 / localhost:8766），同时 ChatGPT 产出的文本也能回流进本系统。
> 约束：① 本机可正常使用 ChatGPT（浏览器已登录）；② 无 ChatGPT 官方 API Key。
> 文档定位：可执行的工程任务分解（拆到"下一步该敲什么命令/写哪个文件"的粒度）。

---

## 0. 核心架构（先建立心智模型）

把系统想成**三层 + 一条双向管道**：

```
┌──────────────────────────────────────────────────────────────┐
│  A 层：ChatGPT 端（本机浏览器，已登录账号，无 API Key）          │
│     Chrome 扩展 content.js  ↔  chatgpt.com DOM                  │
└───────────────┬───────────────────────────┬──────────────────┘
                │ WebSocket (localhost:8799)│
┌───────────────▼───────────────────────────▼──────────────────┐
│  B 层：桥接中间件 chatgpt_bridge（新建，localhost:8799）         │
│     WS 服务(连扩展)  +  提示词队列  +  HTTP 客户端(调本系统)      │
└───────────────┬───────────────────────────┬──────────────────┘
                │ HTTP POST (server-to-server, 无 CORS 问题)      │
┌───────────────▼───────────────────────────▼──────────────────┐
│  C 层：第二大脑 server.py（localhost:8766，已存在）              │
│     入站摄入: POST /api/digest/text  {"text","title","source"}   │
│     检索:     POST /api/retrieve/search                        │
└──────────────────────────────────────────────────────────────┘
```

**两条数据流：**
- **系统 → ChatGPT（出站）**：触发提示词 → B 层入队 → 经 WS 推给扩展 → 扩展把文本注入 chatgpt.com 对话框并发送 → 捕获回复 → 经 B 层 POST 回 C 层 `/api/digest/text`。
- **ChatGPT → 系统（入站）**：用户在 ChatGPT 正常聊天 → 扩展用 MutationObserver 侦测到新助手消息完成 → 经 B 层 POST 到 C 层 `/api/digest/text`（source 标记为 `chatgpt`）。

> 关键设计点：**浏览器扩展只跟本机 B 层（WS）通信，B 层（Python 服务端）再跟 C 层 HTTP 通信**。这样完全绕开浏览器的 CORS 限制——C 层 `do_POST` 不会回 `Access-Control-Allow-Origin`，但 server-to-server 调用不受 CORS 约束。

---

## 1. 无 API Key 的三条技术路径（决策输入）

| 路径 | 原理 | 双向支持 | 健壮性 | 维护成本 | 风险 |
|------|------|---------|--------|---------|------|
| **A. Chrome 扩展 + 桥接中间件（推荐）** | 在已登录的浏览器里注入 content script，原生读取/注入 ChatGPT DOM；通过 WS 与本地桥通信 | ✅ 出站+入站都能做 | 高（跑在真实会话里） | 中（需维护 DOM 选择器） | 低（不碰 token，不违规） |
| **B. Playwright 控制已登录浏览器配置（出站兜底）** | 用 Python + Playwright 加载一个已登录 ChatGPT 的持久化 Chromium profile，程序化输入/读取 | ⚠️ 出站强；入站需轮询 | 中（UI 一变就挂） | 高（要处理反爬/等待） | 中（自动化特征可能被限流） |
| **C. 反向代理 / access token 模拟（不推荐）** | 用抓包拿到的 `access_token` 调未公开的 Web API（如 Pandora/一众逆向库） | ✅ | 低（token 频过期） | 极高 | 高（违反 ToS、随时失效） |

**推荐结论**：以 **路径 A 为主干**（同时覆盖双向），**路径 B 作为出站方向的纯脚本兜底**（当你不想装扩展、只想在 Python 里调一句 ChatGPT 时）。路径 C 仅作知识储备，不建议落地。

---

## 2. 阶段化任务清单

> 编号规则：阶段号.任务号（例如 `T2.3`）。依赖列写前置任务编号。顺序按编号从上到下即合理执行序。

### Phase 0 — 环境与依赖（无代码，纯准备）

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T0.1 | 确认本机 ChatGPT 浏览器与版本 | 打开 ChatGPT，确认登录态正常；记录用的是 Chrome/Edge 及版本 | 浏览器 | 确认可用 + 浏览器品牌 | — | 1 |
| T0.2 | 准备 Python 隔离环境 | 用托管 Python 建 venv：`C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe -m venv C:\Users\Administrator\.workbuddy\binaries\python\envs\chatgpt-bridge` | 托管 Python 3.13 | 独立 venv | T0.1 | 2 |
| T0.3 | 安装桥接依赖 | 在该 venv 装 `fastapi uvicorn websockets httpx` | pip + venv | 依赖就绪 | T0.2 | 3 |
| T0.4 | 确认 8799 端口空闲 | `netstat -ano | findstr 8799` 应为空；若被占改用 8798 | Bash | 端口可用 | — | 2 |

### Phase 1 — C 层（第二大脑）接口就绪确认

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T1.1 | 验证入站摄入端点 | `curl -X POST http://localhost:8766/api/digest/text -H "Content-Type: application/json" -d "{\"text\":\"__chatgpt_bridge_test__\",\"title\":\"桥接自测\",\"source\":\"chatgpt\"}"` 应返回 `{"success":true,...}` | curl + server.py(已在跑) | 端点可用，返回 node | T0.4 | 1 |
| T1.2 | 确认出站触发入口形态 | 决定"谁"触发提示词：① 人工脚本 `send_to_chatgpt.py`；② server.py 新增 `POST /api/chatgpt/prompt` 让本系统主动调。本期先实现 ①，预留 ② | server.py 源码 | 触发方式决策记录 | T1.1 | 2 |
| T1.3 | （可选）新增出站队列端点 | 在 server.py `get_routes()` 加 `'/api/chatgpt/prompt': lambda: self.chatgpt_prompt(self._last_data)` 并实现：把 text 推给 B 层 `/prompt`。**仅在选 ② 时做** | server.py | 新端点（可选） | T1.2 | 3 |

### Phase 2 — B 层：桥接中间件实现（核心）

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T2.1 | 建桥接项目骨架 | 新建 `F:/aidanao/chatgpt_bridge/` 目录，写 `bridge.py`（FastAPI 应用） | 文件系统 | 目录+入口文件 | T0.3 | 1 |
| T2.2 | 实现 WS 服务（连扩展） | 在 `bridge.py` 用 `websockets` 起 `/ws`；维护单扩展连接；提供 `send_to_extension(payload)` 与接收回调 | FastAPI + websockets | WS 端点可用 | T2.1 | 2 |
| T2.3 | 实现提示词队列 + 出站接口 | `POST /prompt {text}` → 入队 → 推扩展 → 等回包（超时 120s）→ 返回回复；同时异步 POST 回 C 层 `/api/digest/text` | FastAPI + httpx | 出站闭环 | T2.2 | 3 |
| T2.4 | 实现入站转发 | `POST /ingest {text,title}` → 直接 POST 到 C 层 `/api/digest/text`（source=chatgpt） | httpx | 入站闭环 | T2.2 | 3 |
| T2.5 | 实现本地客户端 `send_to_chatgpt.py` | 同 venv 下脚本：读命令行参数/ stdin → `POST localhost:8799/prompt` → 打印回复 | Python | CLI 工具 | T2.3 | 4 |
| T2.6 | 启动并守护 | `uvicorn bridge:app --host 127.0.0.1 --port 8799`；可选写 `start_bridge.bat` | uvicorn | 桥常驻 | T2.3,T2.4 | 5 |

### Phase 3 — A 层：Chrome 扩展（路径 A 主干）

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T3.1 | 写 manifest（MV3） | `manifest.json`：permissions `[activeTab, scripting, storage, host_permissions: https://chat.openai.com/*, http://localhost:8799/*]`；background service worker | 文本编辑器 | manifest.json | T2.2 | 1 |
| T3.2 | 写 background.js（WS 客户端） | 连接 `ws://localhost:8799/ws`；收到 `{type:"submit",text}` → 转给 content script；收到 content 的 `{type:"response",text}` → POST `/ingest` | JS | background.js | T3.1 | 2 |
| T3.3 | 写 content.js（DOM 操控） | 注入 chatgpt.com：① 找到输入框 `#prompt-textarea`，填值并派发 input 事件；② 点发送按钮（aria-label="Send prompt"）或模拟 Enter；③ MutationObserver 侦测最新助手消息完成（无"停止生成"按钮且文本稳定）→ 回传文本 | JS + ChatGPT DOM | content.js | T3.2 | 3 |
| T3.4 | 选择器稳健化 | 用 `data-testid`/`role` 组合定位（如 `div[role="presentation"]` 内的 article），避免只靠易变 class；加"等待流式结束"判定（轮询 1s×N，文本长度连续 2 次不变） | JS | 稳定选择器 | T3.3 | 4 |
| T3.5 | 加载扩展做联调 | Chrome → 扩展管理 → 加载已解压 → 选 `chatgpt_bridge/extension/`；打开 ChatGPT；确认 WS 连上（background 控制台无错） | 浏览器 | 扩展可用 | T3.1–T3.4 | 5 |

### Phase 4 — 双向数据流打通

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T4.1 | 出站联调 | 跑 `send_to_chatgpt.py "用一句话解释威科夫因果法则"`，观察 ChatGPT 自动输入并回复；确认回复被摄入 C 层（搜 `__` 无，搜关键词应在知识图谱出现） | send_to_chatgpt.py + C 层 | 出站成功 | T3.5,T2.6 | 1 |
| T4.2 | 入站联调 | 在 ChatGPT 手动发一条消息，等回复完成后，确认扩展自动 POST 到 `/ingest` 并进入 C 层（查 `/api/retrieve/search` 能搜到该内容） | 浏览器 + C 层 | 入站成功 | T3.5,T2.6 | 2 |
| T4.3 | 双向并发不串台 | 出站任务进行中再手动聊一条，确认两条流互不干扰（出站走队列+request_id，入站走 observer） | 上述全部 | 并发安全 | T4.1,T4.2 | 3 |

### Phase 5 — 测试与验证

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T5.1 | 端点冒烟 | 对 B 层 `/prompt`、`/ingest`、`/health` 各发一次请求，确认状态码与返回结构 | curl | 冒烟通过 | T4.3 | 1 |
| T5.2 | C 层摄入校验 | `POST /api/retrieve/search` 用出站/入站文本关键词检索，确认命中且 source=chatgpt | curl | 检索命中 | T5.1 | 2 |
| T5.3 | 失败注入测试 | 关掉 ChatGPT 标签页 → 调 `/prompt` → 应超时返回明确错误而非卡死；恢复后正常 | 手动 | 容错确认 | T5.1 | 3 |
| T5.4 | 端到端脚本 | 写 `e2e_test.py`：自动跑"出站一句+入站一句+检索验证"，输出 PASS/FAIL 报告 | Python | 自动化测试 | T5.1–T5.3 | 4 |

### Phase 6 — 健壮性 / 异常处理（上线前）

| ID | 目标 | 具体操作步骤 | 工具/资源 | 预期输出 | 依赖 | 顺序 |
|----|------|------------|----------|----------|------|------|
| T6.1 | 断线重连 | 扩展 WS 断开后每 5s 重连；B 层检测扩展掉线时 `/prompt` 立即报错而非挂起 | JS + Python | 自愈 | T4.3 | 1 |
| T6.2 | 超时与排队 | `/prompt` 超时（默认 120s）返回错误；多请求用 FIFO 队列 + request_id 配对 | Python | 不错乱 | T6.1 | 2 |
| T6.3 | 输出清洗 | 入站文本去 ChatGPT 的 UI 噪声（复制按钮、思考链标记），保留纯正文 | Python | 干净文本 | T4.2 | 3 |
| T6.4 | 常驻启动脚本 | 写 `start_all.bat`：先起 server.py（若未起），再起 bridge；加开机自启（可选任务计划） | bat | 一键起 | T2.6 | 4 |

---

## 3. 依赖关系与时序

```
T0.1→T0.2→T0.3→T0.4
                    └→T1.1→T1.2→(T1.3?)
T0.4→T2.1→T2.2→{T2.3,T2.4}→T2.5→T2.6
T2.2→T3.1→T3.2→T3.3→T3.4→T3.5
T3.5+T2.6 → T4.1 → T4.2 → T4.3 → T5.* → T6.*
```

**关键路径（最长链）**：T0.1 → T0.2 → T0.3 → T0.4 → T2.1 → T2.2 → T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T4.1/T4.2 → T5.4。
**可并行**：T1.* 与 T2.* 早期可并行（都只依赖 T0.4）；T2.3 与 T2.4 可并行；T3 系列必须串行（DOM 选择器层层依赖）。

---

## 4. 无 API Key 限制的替代方案详述

### 4.1 路径 A（主干）为什么能绕开 Key
- 不调用 `api.openai.com`，而是复用**你已经登录的浏览器会话**。扩展运行在真实登录态的页面上下文里，等于"用代码代替你的手"在 chatgpt.com 上操作。
- 因为操作发生在你本人的浏览器 + 你本人的账号，不涉及任何逆向 token，**不触碰 OpenAI ToS 的 API 条款**。

### 4.2 路径 B（出站纯脚本兜底）
当不想装扩展、只想在 Python 里直接问一句 ChatGPT 时：
1. 用你日常登录 ChatGPT 的 Chrome，导出/复用其 **用户 Data 目录** 作为 Playwright 的 `user_data_dir`。
2. `playwright` 启动持久化 Chromium → 打开 chatgpt.com（自动带登录态）→ 选 `#prompt-textarea` 输入 → 发送 → 轮询最后一条 assistant `article` 直到文本稳定 → 返回。
3. 这套逻辑可封装进 `send_to_chatgpt.py` 的 `--headless` 模式，与扩展模式互斥。

### 4.3 路径 C（仅知识储备，不落地）
- 抓包拿 `__Secure-next-auth` 等 cookie / `access_token`，调未公开 endpoint。
- 缺点：token 数小时过期、OpenAI 频繁改接口、明确违反 ToS、易封号。**仅在 A/B 都不可用时作为最后手段**，且只用于非生产探索。

---

## 5. 验收标准（Done 的定义）

- [ ] 本机跑 `send_to_chatgpt.py "测试问题"`，ChatGPT 自动回复且文本进入 C 层知识图谱（可检索到）。
- [ ] 在 ChatGPT 手动聊天，回复自动流入 C 层（source=chatgpt，无人工复制粘贴）。
- [ ] 扩展 WS 断开/ ChatGPT 关页后，`/prompt` 明确报错不卡死；恢复后自动重连。
- [ ] `e2e_test.py` 全绿。
- [ ] 一键 `start_all.bat` 可拉起整条链路。

---

## 6. 风险与回退

| 风险 | 触发 | 回退动作 |
|------|------|---------|
| ChatGPT 改 DOM 结构 | content.js 选择器失效 | 回 T3.4 更新选择器；加"找不到元素即报错"而非静默失败 |
| 扩展 WS 不稳 | 浏览器休眠 | T6.1 重连；必要时切路径 B |
| 登录态过期 | 浏览器清 cookie | 重新登录 ChatGPT 即可，无需改代码 |
| 并发串台 | 出站/入站同时 | T4.3 + T6.2 用 request_id 配对 |

---

### 下一步建议
这份清单已经拆到"可执行"粒度。真正动手前，有两个岔路需要你拍板，这会直接决定我先从哪一块写起：

1. **出站触发方式**：是只要一个 `send_to_chatgpt.py` CLI（最小可用），还是也要让 server.py 能主动调 ChatGPT（即做可选的 T1.3）？前者今天就能跑，后者更"系统级"。
2. **连接端选 A 还是 A+B 双轨**？我建议先只做路径 A（扩展），它同时覆盖双向且最稳；路径 B 等你需要"纯 Python 无扩展"场景时再加。

你定个方向，我就按上面的编号直接开始写 `chatgpt_bridge/` 和扩展代码。
