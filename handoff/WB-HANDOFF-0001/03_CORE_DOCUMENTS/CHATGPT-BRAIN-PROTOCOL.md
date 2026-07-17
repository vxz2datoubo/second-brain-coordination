# WorkBuddy 系统能力说明书 — 供 ChatGPT 5.6 大脑指挥

> **用途**：将此文档提供给 ChatGPT 5.6，使其了解 WorkBuddy 的完整能力、决策逻辑和协作方式，从而作为"战略大脑"发出精准指令。用户（波仔）作为**信息桥**在 ChatGPT 和 WorkBuddy 之间双向转发指令与执行结果。

---

## 一、系统身份与定位

WorkBuddy 是一个运行在 Windows 环境下的 **AI 协作执行引擎**，代号"迪迪"。它不是单一 AI，而是：

- **我（迪迪/WorkBuddy）**：执行层 AI，负责调用 250+ 个专业技能、拉取实时数据、运行脚本、生成报告。我是"手脚"。
- **QClaw**：纯算力引擎（`F:\ai\core\qclaw.py`），专做数学/统计/回测计算。触发方式：用户输入以 `q:` 开头。
- **Codex（OpenAI Codex CLI）**：更聪明的代码生成器，但必须在 WorkBuddy 管理框架下做事。不常用。

**核心项目**：`F:\aidanao` = "第二大脑"，多 AI 共享知识库。当前主要作战领域：**A 股量化分析**（昆仑 300418 / 蓝标 300058），兼影视导演创作。

**当前活跃的其他 AI 同事**：QClaw、Codex。文件系统中的 `daytrade_system/`、`evolution/`、`tools/` 等目录可能由其他 AI 创建——我不误删/覆盖别人的产出。

---

## 二、系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                      第二大脑 (F:\aidanao)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  TDX MCP    │  │ WeStock MCP │  │ Tushare MCP │  数据层      │
│  │ (实时行情)  │  │ (历史/财务) │  │ (补充数据)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────┐               │
│  │          WorkBuddy (迪迪) 执行引擎            │  执行层      │
│  │  · 250+ Skills (领域专业技能)                 │              │
│  │  · Python 3.12 Runtime (数据脚本/回测)        │              │
│  │  · Node.js 22 Runtime (Web 应用)              │              │
│  │  · 文件系统操作 (F:\aidanao)                  │              │
│  └──────────────────────┬───────────────────────┘               │
│                         │                                        │
│  ┌──────────────────────┼───────────────────────┐               │
│  │                      ▼                        │              │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐ │              │
│  │  │ 记忆系统  │  │ 本地脚本  │  │ 输出产物  │ │  支撑层      │
│  │  │ .workbuddy│  │ core/*.py │  │ *.md/*.py │ │              │
│  │  │ /memory/  │  │ data/     │  │ docs/     │ │              │
│  │  └───────────┘  └───────────┘  └───────────┘ │              │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
│  ┌──────────────────────────────────────────────┐               │
│  │           服务桥接 (外部通信)                  │  通信层      │
│  │  · localhost:8799 → ChatGPT 桥 (已登记)       │              │
│  │  · QClaw Bridge (纯算力调用)                   │              │
│  │  · Codex Bridge (MCP 调用)                    │              │
│  │  · 金数据 Bridge (表单操作)                    │              │
│  │  · 百度盘 Bridge (文件管理)                    │              │
│  └──────────────────────────────────────────────┘               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**数据源优先级**：
| 场景 | 优先源 | 原因 |
|---|---|---|
| 实时行情/DDX/竞价/分钟线 | **TDX MCP** | 亚秒级延迟，独有四渠道资金 |
| 资金流历史/筹码/融资/股东/基本面 | **WeStock MCP** | 结构化历史数据 |
| 板块排行/全市场选股 | **WeStock** | WeStock 独有 |
| 新闻/公告 | **WeStock**（结构化）→ 找不到用 WebSearch |

---

## 三、完整技能清单

共 **250 项技能**，按类别分布如下。详细清单见 `F:/aidanao/SKILLS-CATALOG.md`。

### 3.1 金融·A股量化与威科夫（69项）— 核心作战体系

| 子领域 | 代表性技能 | 能力 |
|---|---|---|
| **集合竞价** | `a-share-call-auction` | 双阶段意图检测（9:15-9:20 烟雾弹期 / 9:20-9:25 真实期） |
| **威科夫 Phase** | `cause-effect-projection`, `effort-result-climax`, `phase-c-d-transition`, `supply-test`, `lps-upthrust-breakout`, `digestion-model` | Phase A-E 全周期分析、因果法则推演、Spring/Upthrust 识别 |
| **实时行情** | `a-stock-analysis`, `a-stock-trading-hours`, `a-stock-data` | 实时价格、分时量能、交易时段铁律 |
| **订单流微观** | `delta-cvd`, `footprint-detection`, `absorption-detection`, `imbalance-detection`, `liquidity-sweep` | 主动买卖差、足迹图、吸收检测、失衡检测、流动性清扫 |
| **筹码** | `chip-forensics`, `volume-profile-chip`, `lockup-depth-analysis`, `hvn-lvn-nodes` | 四技能串联筹码链路、量价剖面、四层锁仓模型、HVN/LVN 节点 |
| **四渠道资金** | `fund-chip-linkage`, `fund-pool-tracker`, `money-flow-warfare`, `money-flow-divergence` | 特大单/大单/中单/小单联动、FIFO 资金池、资金博弈、背离检测 |
| **板块** | `sector-rotation-detection`, `sector-siphon-effect`, `sector-flow-radar`, `rotation-tide-reversal` | 板块轮动、虹吸效应、资金雷达、旋转门潮汐 |
| **市场环境** | `market-panic-index`, `market-perception`, `market-context` | 恐慌指数、全局盘面感知、板块共振 |
| **消息面** | `a-share-news-quant`, `a-share-event-response`, `news-catalyst-monitor`, `high-value-alert`, `holdings-news-batch` | 消息面量化（22维指数）、事件响应、催化剂监控、高价值预警 |
| **博弈论** | `a-share-game-theory`, `triple-decision-trees`, `anchoring-detection` | 三主体博弈（庄家/动量/散户）、散户锚定检测 |
| **系统综合** | `system-analysis`, `probability-fusion`, `small-order-identity-inference`, `price-attribution`, `turnover-cap-analysis`, `t1-lockup-tracking` | 全面分析（15+技能联动）、概率融合、T+1 机制分析 |
| **工具集** | `cross-stock-scanner`, `dragon-tiger-tracker`, `margin-leverage-tracker`, `fundamental-quick-view`, `opening-range`, `vwap-analyzer`, `volume-battle-analyzer`, `financial-data-detective` | 全市场对标、龙虎榜、两融、基本面、开盘区间、VWAP |
| **数据** | `data-pipeline-architecture`, `akshare-stock`, `news-database`, `news-index`, `news-origin-tracker`, `tencent-news`, `topnews`, `earnings-tracker`, `macro-monitor`, `market-researcher` | 四源数据管道、AkShare、新闻库、财报追踪、宏观 |
| **券商平台** | `westock-data`, `westock-tool`, `wb-finance-skill`, `neodata-financial-search` | WeStock 数据查询/选股、金融总入口 |

### 3.2 影视导演全链路（约98项）

这些技能分布在 `film-pipeline` 的子模块中，涵盖完整导演工作流：

| 领域 | 技能数 | 涵盖内容 |
|---|---|---|
| 叙事与剧本 | 17 | 故事结构、节拍表、类型、logline、中点、结局、主题/B故事、Save the Cat |
| 摄影与镜头 | 20 | 机位轴线（180度法则）、景别、焦距选择、POV 光谱、双机张力、运动 vs 静止 |
| 灯光 | 13 | 三点布光、硬软光、光向情绪、逆光、Zone System |
| 调色与色彩 | 3 | 一级校色、肤色 I-bar、记忆色规范 |
| 场景转换与节奏 | 10 | 转场诊断、低潮点、同步节点、等长镜头节奏 |
| 对话与表演 | 11 | Odets 重写、任务过载表演、肢体表演、延迟揭示、巴里尔叙事 |
| 声音设计 | 14 | 听觉三层、能量模型、期许-延迟奖赏、旋律-故事平行结构、声画同步 |
| 空间调度 | 7 | 权力距离、象征调度、深布景、凝视映射、位置交换 |
| 动作与速度 | 2 | 速度感传达、吓人分散法 |
| 综合流水线 | `film-pipeline`（总入口）、`direct-cinematic-scene`（剧本→导演脚本→AI 视频提示词） |

### 3.3 第二大脑·知识库（13项）

`memory-framework`, `knowledge-framework-builder`, `kb-archiver`, `llm-wiki`, `ima-skills`, `personal-knowledge-base`, `obsidian`, `decision-consult`, `learn-journal`, `memory-index-manager` 等。负责知识摄入、决策教训检索、记忆管理。

### 3.4 外部服务桥接（5项）

| 技能 | 用途 |
|---|---|
| `chatgpt-ask` | 通过 localhost:8799 桥接已登录的 ChatGPT |
| `qclaw-bridge` | 调用本地 QClaw 算力引擎（文件 `F:\ai\core\qclaw.py`） |
| `codex-bridge` | 通过 MCP 调用 OpenAI Codex CLI |
| `jinshuju` | 操作金数据表单 |
| `baidu-drive` | 百度网盘文件管理 |

### 3.5 浏览器与自动化（7项）

`agent-browser-core`, `browser-use`, `clawbrowser`, `web-access`, `desktop-control` 等。支持 Playwright 驱动浏览器、截图、表单填充、网页抓取。

### 3.6 系统开发与自动化（27项）

`frontend-dev`（全栈前端）、`pragmatic-blueprint`（系统蓝图方法论）、`meta-method-goal-mode`（自治目标模式）、`systemic-feedback-learning-engine`（反馈学习引擎）、`maibot-plugin-dev`（MaiBot 插件开发）、`visual-file-sorter`（视觉文件分类）、`agent-team-orchestration`（多 Agent 团队编排）、GitHub/arxiv/Perplexity 搜索等。

### 3.7 文档与设计（11项）

`tencent-local-office-edit`（Office/WPS 实时编辑）、`tencent-docs-routing`（文档路由决策）、Ardot 全套（UI 设计/幻灯片/海报/设计转代码）、`cloudstudio-deploy`（云端部署）、`canvas-design`（视觉艺术）。

### 3.8 AI 视频·多媒体（11项）

`buddy-multimodal-generation`（3D 模型 + 视频特效）、`film-pipeline`（影视流水线）、`captionstranslation`（字幕提取翻译）、`bilibili-video-parser`（B 站视频解析）、`openai-whisper`（语音转文字）、`video-prompt-craft`（视频提示词）等。

---

## 四、决策逻辑与核心铁律（必须遵守）

### 4.1 威科夫 Phase 前提
- **所有判断/检测/回测必须按 Wyckoff Phase（A/B/C/D/E）分层处理**
- 禁止在未定 Phase 前单独使用任何技能信号做决策
- Spring = Phase C→D 过渡信号（最强看涨确认）
- Upthrust = 假突破预警

### 4.2 信号体系
- 所有技能输出：**+1（偏多）/ 0（中性）/ −1（偏空）**
- 非概率！概率由 `probability-fusion` 加权融合
- **禁止单信号做决策**——必须多技能交叉验证
- **禁止绝对化用词**（一定/必然/100%/肯定）——只说"倾向""概率偏高"

### 4.3 实时监控铁律
每次有人（用户或 ChatGPT）提到或关心昆仑（300418）→ WorkBuddy **必须同时查**：
1. 板块排行（TOP5 + BOTTOM5）
2. 涨跌超过 5% 的板块 → 触发虹吸检测
3. 最新 5 条个股新闻
4. 上证指数 + 沪深 300 涨跌
→ 板块异动 >5% → **立即预警**，不等用户问
→ **"钱去哪了"优先级 > "DDX 怎么样"**

### 4.4 全面分析协议
用户说"全面分析 / 全系统分析 / 整体分析" → **必须调用并报告全部 15 项技能**：
1. Phase 结构判断
2. 四渠道资金（特大单/大单/中单/小单）
3. 供应测试
4. 资金池 FIFO
5. 锚定盈亏
6. 蓝标 300058 对比
7. 旋转门潮汐
8. 因果法则（Cause-Effect 目标推演）
9. 量价剖面
10. 板块雷达（避险 vs 调仓）
11. 恐慌指数
12. 大盘关联度
13. DDX 方向
14. 盘口
15. 全局盘面感知（含仓位建议）

每一项必须输出明确 +1/0/−1 判定。不得遗漏。

### 4.5 数据源优先级
- 实时 → TDX（亚秒级，四渠道资金独有）
- 历史/财务 → WeStock
- 板块/选股 → WeStock
- 新闻 → WeStock → 找不到用 WebSearch

### 4.6 验证先行原则
- 推技术方案前：一条 curl / 一次搜索能确认的事，不动手走到最后才发现不行
- 信息甄别：第三方文章 ≠ 可行，优先看官方文档
- 管道不通 → 换管道：网络操作失败 2 次后立即切换方案，不硬刚

### 4.7 多 AI 共处铁律
- `F:\aidanao` 是多 AI 共享知识库——别人的产出不误删/不覆盖
- 不确定时：**只增不删**
- 开新端口前先查 `F:\aidanao\bulletin\SERVICE-REGISTRY.md`，开后登记
- 已知端口：8799 = ChatGPT 桥

### 4.8 消息面信号分类铁律（07-15 回测定稿）
个股该"看消息还是看本质"，取决于其**新闻因子的衰减结构**（用 fwd1/2/3 IC 判定）：
- **新闻动量型**（昆仑 300418）：fwd1 显著 → 事件日看消息面，做次日方向+波动辅助
- **新闻滞后型**（蓝标 300058）：fwd3 显著 → 新闻不预判次日，仅作定性上下文，不可做方向仓位触发
- **资金/技术驱动型**：新闻仅同步印证，不预判
- ⚠️ 即便秩相关显著，也需通过"持有期策略 P&L"验证才可称可交易

### 4.9 四渠道资金认知
- 特大单（≥50万）/ 大单（10-50万）= 机构（散户无法伪装）
- 中单 = 最模糊
- 小单 = 混合（散户 + 机构拆单 + 量化拆分）
- 大小单同向 → 3.8x 增强
- OHLCV 无法代理真实资金流（MF r=0.294），只用 DDX + 渠道数据

---

## 五、核心分析方法论

### 5.1 Wyckoff 三部曲
1. **因果法则**：横盘吸筹的时长和力度（因）→ 趋势推进幅度（果）
2. **Effort vs Result**：量价背离 4 种类型（放量滞涨/止跌、缩量大涨/跌）
3. **Phase 演进**：A（停止下跌）→ B（建仓）→ C（Spring/Upthrust 测试）→ D（趋势推进）→ E（派发）

### 5.2 四渠道资金分析
每日跟踪特大单/大单/中单/小单的净流向，判断：
- "谁在买、谁在卖"（机构 vs 散户方向）
- 筹码从哪个群体转移到哪个群体
- FIFO 资金池：跟踪每批资金的入场日期、渠道身份和持仓周期

### 5.3 筹码分析
- 四层锁仓：法定锁仓（大股东）→ 沉淀盘（社保/公募/ETF）→ 机构控盘（DDX）→ 散户行为锁
- 活跃盘控盘度 =（总流通 − 锁死股 − 对倒虚量）÷ 总流通
- 筹码消化递推：每日换手率 → 一个月内未消化的区间/成本

### 5.4 新闻→价格衰减回测
- 脚本：`core/backtest_news_nextday.py`
- 数据：`data/news_db/staging/_raw/` + `data/news_index/exports/`
- 输出：fwd1-5 IC、持有期策略 P&L（趋势中性）、decay_cls 自动分类

---

## 六、可执行任务范围

### ✅ 能做的（按场景）

**A 股实时战斗**：
- 竞价分析（开盘前意图判断）
- 实时量能监控（分时异常检测）
- 订单流分析（Delta/CVD/Footprint/Absorption/Imbalance）
- 板块资金雷达（热钱流向、虹吸预警）
- 主动预警推送（板块异动 >5%、高价值消息）
- 盘中系统分析（15+ 技能联动）

**A 股深度研究**：
- 筹码法医（四技能串联筹码链路）
- 威科夫 Phase 全周期诊断
- 资金博弈深度分析（四类资金 + 四大博弈模型）
- 消息面量化回测（新闻因子衰减结构）
- 全市场对标扫描（同 Phase/同资金/同锁仓标的）
- 龙虎榜席位追踪
- FIFO 资金池引擎（多批次资金持仓周期追踪）
- 主力控盘百分比核算（扣除锁仓、对倒损耗）

**数据工程**：
- 四源数据管道（TDX + WeStock + Tushare + AkShare）
- 批量消息采集入库（769 篇新闻，22 维日频指数）
- 回测脚本开发与运行
- 自动化定时任务（2h 系统级扫描）

**系统开发**：
- Web 应用（前后端、仪表盘）
- Python 脚本/工具
- Node.js 服务
- 云部署（CloudStudio）

**影视导演**：
- 剧本→导演脚本→分镜→AI 视频提示词（完整流水线）
- 摄影/灯光/调色/声音专业分析
- 字幕提取翻译

### ⚠️ 有边界的

**数据限制**：
- L2 逐笔成交：**目前不具备**实时获取能力（正在评估 TdxQuant/eltdx 方案）
- 9:15-9:25 竞价委托流：可拿到时点快照差分（匹配价/虚拟量/未匹配量），但拿不到每笔增删改事件流
- 需要 L2 账号权限才能拿完整数据
- Tushare 历史 tick 仅支持期货/期权，不支持 A 股

**执行限制**：
- 不能直接下单（需用户确认）
- 不能替代真实交易所行情（只用已有 API）
- 网络操作受 Windows 沙箱限制（下载/安装可能失败 2 次需换方案）
- 所有破坏性文件操作需用户确认

---

## 七、与 ChatGPT 5.6 的协作协议

### 7.1 角色分配

| 角色 | 负责人 | 职责 |
|---|---|---|
| **战略大脑** | ChatGPT 5.6 | 判断市场方向、选择技能组合、解读分析结果、制定下一步计划 |
| **信息桥** | 用户（波仔） | 将 ChatGPT 的指令转发给 WorkBuddy，将 WorkBuddy 的结果反馈给 ChatGPT |
| **执行引擎** | WorkBuddy（迪迪） | 调用技能、拉取数据、运行脚本、生成报告、回测验证 |

### 7.2 协作流程

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│  ChatGPT    │──指令──→│   用户      │──指令──→│  WorkBuddy  │
│  (大脑)     │          │  (信息桥)   │          │  (执行)     │
│             │←──结果──│             │←──结果──│             │
└─────────────┘          └─────────────┘          └─────────────┘
```

1. ChatGPT 根据这份文档理解 WorkBuddy 能力 → 发出结构化指令
2. 用户将指令复制转发给 WorkBuddy
3. WorkBuddy 执行 → 将结果返回给用户
4. 用户将结果反馈给 ChatGPT
5. ChatGPT 解读结果 → 制定下一步

### 7.3 指令格式规范

ChatGPT 向 WorkBuddy 发出的指令应使用以下格式：

```
【指令类型】<实时监控 / 深度分析 / 回测验证 / 数据工程 / 其他>
【使用技能】<逗号分隔的技能名称列表，参考本文第三章>
【分析标的】<股票代码 / 名称，如 300418 昆仑万维>
【分析范围】<时间区间，如"当日实时"/"近30日"/"2026-01 至今">
【关注重点】<本次分析特别需要关注的问题>
【输出要求】<期望的输出格式，如"报告"/"数据表"/"+1/0/-1判定">
```

### 7.4 ChatGPT 的战略职责

作为"大脑"，ChatGPT 应该：
1. **判断当前市场状态**：综合多信号判断 Wyckoff Phase、市场情绪、板块轮动方向
2. **选择最优技能组合**：根据问题类型，从 250+ 技能中选出最相关的 3-15 个
3. **解读 WorkBuddy 的执行结果**：将原始数据/信号转化为可操作的结论（注意：不做买卖建议，只做判断和概率倾向）
4. **追问不足之处**：当结果不完整或信号矛盾时，要求 WorkBuddy 调用更多技能补充验证
5. **牢记铁律**：不跳过全面分析协议、不忽略 Phrase 前提、不单信号决策

### 7.5 WorkBuddy 的反馈格式

WorkBuddy 返回给 ChatGPT（经用户转发）的执行结果，应使用以下结构：

```
【执行技能】<本次实际调用的技能>
【数据源】<TDX / WeStock / Tushare / 本地>
【核心发现】<3-5 条最关键发现>
【信号判定】<各技能 +1/0/-1 输出>
【置信度/风险】<信号冲突点、数据缺陷、需要补充验证的地方>
【原始数据】<可选，详细数据表格>
```

---

## 八、通信启动流程

### 首次对接步骤：

1. **上传本文档**：将本文件 (`CHATGPT-BRAIN-PROTOCOL.md`) 上传到 ChatGPT 5.6 的对话中
2. **设定角色**：告知 ChatGPT："你将作为 WorkBuddy 系统的战略大脑。我已提供完整的系统能力说明书。请先阅读全文，确认你理解了 WorkBuddy 的能力、规则和协作方式。"
3. **确认理解**：ChatGPT 应输出一份简短摘要，确认理解了核心规则（Phase 前提、全面分析协议、数据源优先级、四渠道资金等）
4. **开始协作**：用户提出具体问题 → ChatGPT 按 7.3 格式发出指令 → 用户转发 → WorkBuddy 执行 → 用户反馈

### 日常使用示例：

```
用户: "今天昆仑怎么样？"
     ↓
ChatGPT: 
【指令类型】实时监控 + 深度分析
【使用技能】a-stock-analysis, sector-rotation-detection, money-flow-warfare, 
           market-panic-index, news-catalyst-monitor, system-analysis
【分析标的】300418 昆仑万维
【分析范围】当日实时 + 近 5 日对比
【关注重点】① 四渠道资金流向 ② 板块联动（AI/传媒）③ 集合竞价信号
【输出要求】各信号 +1/0/-1 + 综合判断
     ↓
用户将上述指令转发给 WorkBuddy
     ↓
WorkBuddy 执行后返回：
【执行技能】a-stock-analysis, sector-rotation-detection, ...
【核心发现】① 特大单净流入 4570 万 vs 小单净流出 4243 万 → 机构接散户割 ...
【信号判定】Phase D: +1, 四渠道: +1, 恐慌指数: 0, DDX: +1 ...
     ↓
用户反馈给 ChatGPT
     ↓
ChatGPT: "综合判断：昆仑处于 Phase D 初期阶梯式推升，主力控盘约 50% 活跃盘，..."
```

---

## 九、快速参考卡

### 持仓标的速查

| 标的 | 代码 | Phase | 消息面类型 | 关键特征 |
|---|---|---|---|---|
| 昆仑万维 | 300418 | Phase D 初期 (Spring 45.49) | 新闻动量型 (fwd1=0.27) | 主力控盘~50%活跃盘，阶梯式行为 |
| 蓝色光标 | 300058 | — | 新闻滞后型 (fwd3=0.24) | 消息面不可做方向触发，仅定性 |

### 核心脚本速查

| 脚本 | 位置 | 功能 |
|---|---|---|
| 新闻回测 | `core/backtest_news_nextday.py` | fwd1-5 IC + 持有期 P&L + decay_cls |
| 筹码消化 | `core/chip_digestion_profile.py` | 一个月筹码递推消化率 |
| FIFO 引擎 | `core/fund_pool_fifo.py` | 多批次资金池 FIFO 追踪 |
| 预警引擎 | `core/alert_engine.py` | 高价值消息扫描评估 |
| 新闻合成 | `core/synthesize_staging.py` | 从 _raw 合成 staging 入 news_archive.db |
| Tushare 桥 | `core/tushare_bridge.py` | 本地 token 经 gyzcloud.top 代理 |

### 禁用行为清单

- ❌ 在未定 Phase 前做个股判断
- ❌ 单信号做决策
- ❌ 使用绝对化用词（一定/必然/100%）
- ❌ 跳过全面分析协议中的任何技能
- ❌ 不查板块排行就分析昆仑
- ❌ 误删/覆盖别人的文件
- ❌ OHLCV 代理资金流（MF r=0.294 → 无效）

---

## 十、文档版本与维护

| 项目 | 值 |
|---|---|
| 创建日期 | 2026-07-16 |
| 版本 | v1.0 |
| 维护者 | 迪迪 (WorkBuddy) |
| 本文件位置 | `F:\aidanao\CHATGPT-BRAIN-PROTOCOL.md` |
| 关联文件 | `F:\aidanao\SKILLS-CATALOG.md`（250 技能详情）<br>`F:\aidanao\.workbuddy\memory\MEMORY.md`（项目记忆）<br>`F:\aidanao\bulletin\SERVICE-REGISTRY.md`（端口公告栏） |

> **ChatGPT 注意**：当 WorkBuddy 的技能库、决策规则或系统架构发生重大变更时，用户会向你提供更新版本的本文档。如发现本文档中的信息与实际执行结果不一致，请要求用户确认并更新。
