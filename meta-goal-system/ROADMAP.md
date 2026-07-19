STATUS: ACTIVE
ROUND: 5
MODE: FULL_AUTO
PAUSE: 0
COMPLETE: 0
MAX_ROUNDS_PER_RUN: 8
STALL_LIMIT: 2
STALL_COUNT: 0
RISK_TIER: BOLD
# ===== 控制说明（自治执行器每轮先读这里）=====
# PAUSE:1 或 COMPLETE:1 → 立即停止
# MODE: FULL_AUTO=单次触发内批量连续推进多轮 / SEMI_AUTO=每次只一轮
# MAX_ROUNDS_PER_RUN=单次触发最多连续推进轮数（软上限，防烧穿 token）
# STALL_LIMIT=连续无实质进展 N 轮 → 自动 PAUSE 并记录（停滞熔断）
# STALL_COUNT=当前连续无进展计数（执行器自动增减）
# RISK_TIER: BOLD=允许大步试错(带回滚+备份) / SAFE=仅小步探针
# 触发器：每小时一次；FULL_AUTO 下每次会连续跑多轮 → 近似不停

# 元方法论·目标模式自治系统 — ROADMAP（活状态文件）

> 这是跨轮持久化的权威状态。自动化每轮读这里的 `NEXT_ROUND`，做一件事，追加报告，轮次 +1。
> 第二大脑 `/api/goal` 为 best-effort 的辅助持久化，本文件才是真相源。

## Bootstrap 想法（用户原话提炼）

构建一个像 Codex `/goal` 那样的自治系统：我提一个想法，你用**元方法论**把它映射一遍
（我知道我说了的 + 我知道但我没说的 + 我不知道但我看得懂的 + 我不知道且我看不懂的），
整合成一套映射关系的技能；出系统蓝图，联网找改进/联动/学术论文/机构量化等高质量文章
深度学习，定制方案；按清单一步步完成；每步可运行/可测试/可复盘/可扩展；没做完标清楚，
**不许假装完成**；**最重要：无需人工干预，能持续不断自己跑**。

---

## 四象限知识映射（核心产出）

### Q1 已知·已说（用户明确陈述）
- 想要 Codex 那样的 goal mode（提想法→持续自治推进到完成）
- 用元方法论映射想法
- 四象限：已知已说 / 已知未说 / 未知可懂 / 未知不懂，全部整合进一套映射技能
- 上网找改进 / 联动 / 学术论文 / 机构量化 / 周刊等高质量文章，深度学习
- 出系统蓝图 → 按清单一步步完成
- 每步 9 点报告（目标/文件/原因/运行/测试/完成/未完成/风险/下一轮）
- 最小闭环，能运行/能测试/能复盘/能扩展
- 没做完标清楚，不许假装完成
- **最重要：无需人工干预，持续自治跑（类 Codex 目标模式）**

### Q2 已知·未说（隐含假设 / 环境 / 已有资产 — 我推断的，请核验）
- 你**已有第二大脑**（localhost:8766）内建 goal / evolve / agent 原语 → 应复用，不是新建
- 你**已有 `pragmatic-blueprint` 技能**（2-cell 映射）→ 新系统是它的 2x2 扩展
- 你**已有 136 个技能 + tdx/westock 等 MCP** → 新系统应调度而非替代
- 你偏好：直接、有主见、不废话；单文件 HTML；深色顶栏+白画布+浅灰网格；IMAX 胶片质感
- 你厌恶：假装完成、模糊估算、频繁干预、复杂化
- 闭环学习原则：被纠正后扫描所有受影响产物并修复（可泛化迁移，不堆静态规则）
- WorkBuddy 自动化可做定时触发器 → 是实现"持续跑"的关键外壳

### Q3 未知·可懂（不知但能研究掌握 — 已联网深度学习，见 BLUEPRINT 第 1 节）
- Codex `/goal` 四层实现：持久化(Rust+DB) / continuation.md 注入 / 完成审计 / Token 预算软停止
- Ralph Loop：bash 循环 + 外部状态 + 可验证停止条件
- Reflexion（反思入记忆）/ Voyager（技能库沉淀）/ Self-Refine
- Cynefin 五域：Clear/Complicated/Complex/Chaotic/Confused → 决定各象限处理动作
- Agentic Harness 五层：Instructions/Tools/Retrieval/Orchestration/Evaluators
- TDAG 动态任务分解：子任务 3–10 最优；静态分解易 error propagation
- MAPE-K（Monitor-Analyze-Plan-Execute-Knowledge）→ 你第二大脑 evolve 已是此模式
- Frontier-Eng / 自进化 agent 评测基准

### Q4 未知·不懂（看不懂的盲点 — 必须标 TODO/Interface/Mock，禁止假装完成）
- 第二大脑 `evolve_mode` 的 OpMode 枚举（safety/observation/diagnostic/advisory/semi_auto/full_auto）如何与自动化联动 → `Interface`
- 多 Agent Orchestrator 权重自更新内部机制 → `Interface`
- 第二大脑 goal 系统的存储后端（SQLite? 文件?）与 create 路由确切签名 → `TODO`（本轮尝试接入）
- 如何让 WorkBuddy 自动化"无限循环"而不烧爆 token / 不跑飞 → `Future Roadmap`（需预算/熔断实测）
- MCP(tdx/westock) 在自动化上下文是否可用、是否需授权 → `Future Roadmap`
- 元方法论在 Q4 的递归处理："承认无知"→主动探针协议 → ✅ 已定义（见下"自治运行策略 v2 · Q4 探针协议"，执行器已按此运行）

---

## 自治运行策略 v2（连续 + 试错 + 熔断）— 2026-07-11 用户授权

用户决策：①要连续工作、尽量不停；②授予最大权限，小步/大步试错均可。据此升级：

### 连续性（近似不停）
- 触发器每小时一次（自动化系统最密的无人干预粒度）。
- 单次触发进入 FULL_AUTO 批量循环，连续推进多轮（软上限 `MAX_ROUNDS_PER_RUN=8`）。
  每小时 × 多轮 ≈ 持续工作。停止仅由 COMPLETE / PAUSE / 停滞熔断触发。

### Q4 探针协议（把"看不懂"从被动降级变主动撬开）
1. 小步探针：对一个 Q4 盲点提出可证伪假设 → 设计最小实验 → 跑 → 记录结果（成/败/回滚）。
2. 大步扩展：探针证明方向对 → 允许大步实现。
3. 每个探针的假设 + 结果必须写进 Iteration Log；失败即回滚，不留半成品。
→ 这落地了原先标 `Future Roadmap` 的"Q4 递归承认无知协议"。

### 三道刹车（最大权限的必要对冲）
1. **停滞熔断**：连续 `STALL_LIMIT`(=2) 轮无实质进展（validate FAIL / 无可验证产出）→ 自动 PAUSE + 记录原因。
2. **破坏性护栏**：写操作默认限 `meta-goal-system/` + 第二大脑 API。越界写或破坏性操作（删文件 / 改核心 server.py / git push / 对外发布）须先记录"试错 + 回滚方式"并备份，无记录不得破坏。硬禁：rm -rf / 清空目录 / 动个人文件夹 / 泄露密钥。
3. **完成即停**：COMPLETE:1 或成功标准全达成 → 停。

### 可调旋钮（都在 ROADMAP 顶部）
- 想更省：`MODE→SEMI_AUTO` 或调低 `MAX_ROUNDS_PER_RUN`。
- 想更稳：`RISK_TIER→SAFE`（仅小步探针）。
- 想全停：`PAUSE:1`。想收工：`COMPLETE:1`。

---

## 研究综述（已做，详见 BLUEPRINT.md 第 1 节）
- Codex /goal 四层架构（Tencent Cloud / CSDN / OpenAI 官方）
- Ralph Loop & Loop Engineering（CSDN 综述）
- Reflexion / Voyager / Self-Refine（juejin / diors.tech / yudesk.dev）
- Agentic Harness 五层 + Airbnb Data Flywheel（subagentic.ai）
- Cynefin 决策框架（Snowden 1999）
- TDAG 动态任务分解 / ItineraryBench（ScienceDirect 2025）
- Frontier-Eng 自进化评测基准（机器之心 / arXiv 2604.12290）

---

## Iteration Log

### Round 1（2026-07-11，本轮回合）

#### 1. 本轮目标
建立元方法论目标模式系统的**最小可运行闭环种子**：技能定义 + 系统蓝图 + 四象限映射 + 闭环验证器 + 测试 + 自治自动化，并对此 bootstrap 想法完成第 1 轮真实映射与报告。

#### 2. 修改文件
- 新建 `C:/Users/Administrator/.workbuddy/skills/meta-method-goal-mode/SKILL.md`（技能定义）
- 新建 `F:/aidanao/meta-goal-system/BLUEPRINT.md`（系统蓝图 + 研究综述）
- 新建 `F:/aidanao/meta-goal-system/meta_goal.py`（闭环验证器/脚手架）
- 新建 `F:/aidanao/meta-goal-system/test_meta_goal.py`（测试）
- 新建 `F:/aidanao/meta-goal-system/ROADMAP.md`（本文件，活状态 + 四象限 + 第 1 轮报告）

#### 3. 设计原因
- **复用而非重建**：第二大脑已有 goal/evolve/agent 原语，pragmatic-blueprint 已有 2-cell 映射，136 技能已是能力层。新系统只贡献 3 处新价值（2x2 四象限 / 自治外壳 / 9 点报告），其余全复用 → 符合"不要大规模重构""引入新模块须说明如何接入现有数据流"。
- **2x2 四象限**精确化用户的"知识映射"诉求（多出"已说/未说"与"可懂/不懂"两轴），并用 Q4 作为"反假装完成"硬锚点。
- **自动化外壳**复刻 Codex /goal 的持久化+续跑+审计三要点，实现"无需人工干预持续跑"。
- **meta_goal.py 验证器**即轻量 Evaluator 层，保证每轮可测试、可复盘。

#### 4. 运行方法
```
cd F:/aidanao/meta-goal-system
python meta_goal.py status
python meta_goal.py scaffold 2
python meta_goal.py validate ROADMAP.md
```

#### 5. 测试方法
```
python test_meta_goal.py
# 期望: 4 个测试全过（合法报告 PASS / 破损报告 FAIL / status 可跑 / scaffold 可追加并清理）
```

#### 6. 已完成内容
- 技能定义 SKILL.md（四象限 + 9 点协议 + 联动表 + 禁止事项 + 触发词）
- 系统蓝图 BLUEPRINT.md（研究综述 + 架构分层 + 数据流向 + 范围表 + 风险 + 下一步）
- bootstrap 想法的完整四象限映射（Q1–Q4）
- 闭环验证器 meta_goal.py（status/scaffold/validate）
- 测试 test_meta_goal.py
- 第 1 轮 9 点报告（本回合）
- 第二大脑 `/api/goal/create` 接入**已验证成功**（goal id: `goal_85449be5441c43`，状态 `dreaming`）
- WorkBuddy 自动化创建（rrule 定时触发续跑）

#### 7. 未完成内容（标 TODO / Interface / Mock）
- `Interface`: L6 每轮 milestone 自动写入的脚本接线（create 路由已验证：`POST /api/goal/create`，goal_type∈daily/weekly/monthly/quarterly/yearly/life；待写自动化调用）
- `Interface`: L7 `/api/evolve/cycle` 每轮后自动调用（端点已知，未接线）
- `Interface`: L8 `/api/agent/orchestrate` 重大决策审计（端点已知，未接线）
- `TODO`: 把四象限节点自动写入 `/api/knowledge-graph`（未做）
- `Future Roadmap`: 无限自治的 token 预算/熔断细化（依赖 L6/L7 实测）
- `Future Roadmap`: MCP(tdx/westock) 在自动化上下文可用性验证
- `Future Roadmap`: Q4 递归"承认无知"协议（策略层设计，未落地）
- `DONE✅`: L6 goal 创建已实测通过（不再 Mock）；剩余为 milestone 自动写入接线（见上）

#### 8. 风险
- 自动化频繁跑可能烧 token → 已用 ROADMAP 顶部 PAUSE/COMPLETE 标志 + 轮次上限对冲；evolve/mode 联动熔断为 Future Roadmap。
- 第二大脑未运行 → L6 接入失败 → ROADMAP.md 为权威副本，best-effort 不阻塞。
- 假装完成风险 → 已用 TODO/Interface/Mock 标注 + validator 检查 9 点+四象限。
- MCP 工具在自动化上下文可能不可用 → 本轮不依赖，列 Future Roadmap。

#### 9. 下一轮建议
**Round 2 = 只做一件事**：写一段脚本把每轮进展自动写入第二大脑 milestone（`POST /api/goal/milestone`，goal id 已知），并让自动化首跑验证 `meta_goal.py status` 解析正确 + milestone 真正落库。不要扩到其他层。

---

## Round 2（2026-07-11，跨窗口多实例化）

#### 1. 本轮目标
把技能从"单一 bootstrap 项目"升级为**任何对话窗口都可调用的多实例目标算子**：窗口把任务交给它 → 2x2 分解 → 清单 → 全局自动化持续执行到完成。核心改动 = 引擎多实例化（registry + spawn/list/next/guard）+ 重写 SKILL.md 为跨窗口算子 + 自动化改为注册表轮询。

#### 2. 修改文件
- 重写 `F:/aidanao/meta-goal-system/meta_goal.py`（加 registry / spawn / list / next / guard / 实例感知 status·validate）
- 重写 `C:/Users/Administrator/.workbuddy/skills/meta-method-goal-mode/SKILL.md`（跨窗口使用协议 + 命令速查）
- 重写 `F:/aidanao/meta-goal-system/test_meta_goal.py`（增 spawn/list/guard/实例validate 测试）
- 更新自动化 `automation-1783781472384` 的 prompt（注册表轮询驱动）

#### 3. 设计原因
- **用户的纠正**：技能应是"别的窗口在做事时，它能拆解成清单并持续执行"的通用算子，而非 aidanao 内的一个写死项目。原引擎把路径硬编码为单一 ROADMAP，与诉求冲突。
- **最小改动实现跨窗口**：用 `goals/registry.json` 管理多个目标实例，任何窗口调 `spawn` 即新建独立实例；全局自动化 `next` 轮询逐个推进。这是加法，不破坏既有 bootstrap 实例（仍注册为 `bootstrap`）。
- **代码级刹车 `guard`**：把"停滞熔断"从文本约定升级为可执行判定（读 PAUSE/COMPLETE/STALL_COUNT），回应用户此前关于"内部 vs 外部裁判"的疑虑——先有可靠的内部判定，外部看门狗列为 Future。
- **诚实边界写进 SKILL**：明确"技能无法隔空读另一窗口实时内容，须由用户在该窗口显式交任务"，避免假装完成。

#### 4. 运行方法
```
cd F:/aidanao/meta-goal-system
python meta_goal.py list                         # 看所有实例
python meta_goal.py spawn "任务名" --task "描述" # 任何窗口新建实例
python meta_goal.py next                          # 挑下一个可推进实例
python meta_goal.py guard <id>                    # 代码级刹车判定
python meta_goal.py validate <id路径>             # 校验 9 点 + 四象限
```

#### 5. 测试方法
```
python test_meta_goal.py
# 期望: 9 个测试全过（原 4 + spawn 建实例 / 鲜实例 validate 必 FAIL / guard 逻辑 / list·next 可跑）
```
实测：9 测试全过 ✅；bootstrap validate PASS ✅；live demo spawn 建实例 + 第二大脑 goal（`goal_9eee2371d5654c`）+ list/guard/status 均正常，清理后注册表回 1 ✅。

#### 6. 已完成内容
- 多实例引擎（registry + spawn/list/next/guard + 实例感知 status/validate），向后兼容旧命令
- SKILL.md 重写为跨窗口通用算子（调用协议 + 诚实边界 + 命令速查）
- 自动化改为注册表轮询、FULL_AUTO 批量、多实例逐个拾取
- 测试扩展至 9 个，全过；端到端 live demo 通过
- 第二大脑 goal 创建已并入 spawn（best-effort）

#### 7. 未完成内容（标 TODO / Interface / Mock）
- `Interface`: L6 每实例 milestone 自动写入（`POST /api/goal/milestone`，各实例的 sb_goal_id 已在注册表）→ Round 3 接线
- `Interface`: L7 `/api/evolve/cycle` 每轮后自动调用（端点已知，未接）
- `Interface`: L8 `/api/agent/orchestrate` 重大决策审计（未接）
- `TODO`: 四象限节点自动写入 `/api/knowledge-graph`（未做）
- `Future Roadmap`: 外部看门狗（独立脚本）对 guard 结果做二次裁判，防执行器自我判断偏乐观
- `Future Roadmap`: spawn 时第二大脑 goal 的清理/回收（目前 demo 清理只删本地实例，第二大脑 goal 留 orphan，无害）
- `Future Roadmap`: MCP(tdx/westock) 在自动化上下文可用性验证；Q4 承认无知协议落地为探针模板

#### 8. 风险
- 多实例并发：全局自动化串行处理，多个窗口同时 spawn 仅追加注册表，无写冲突（各实例独立目录）。
- 第二大脑未运行 → spawn 的 goal 创建失败（已 best-effort 不阻塞）；本地 ROADMAP 为权威。
- 自动化每小时触发 + FULL_AUTO 批量，多实例会拉长单次耗时 → 全局软上限 12 轮/次 兜底。
- 鲜实例（ROUND:0）在分解前 validate 必 FAIL，自动化须先分解再校验（prompt 已规定 B 分支）。

#### 9. 下一轮建议
**Round 3 = 只做一件**：把 L6 milestone 自动写入接进 spawn/每轮流程——自动化每推进一轮，用该实例注册表的 `sb_goal_id` 调 `POST /api/goal/milestone` 落库；并在测试里加一个 mock 端点验证调用逻辑。不扩其他层。

---

## Round 3（2026-07-11，每窗口独立并行执行模型）

#### 1. 本轮目标
按用户最终定位，把执行模型从"单全局自动化串行轮询"改为**每实例专属独立自动化**：每个窗口的任务 = 自己的循环，独立、并行、无限执行直到完成，互不阻塞、互不排队。技能本身即一个自包含自动化技能。

#### 2. 修改文件
- 重写 `F:/aidanao/meta-goal-system/meta_goal.py`：spawn 现在打印**每实例专属自动化 prompt 模板**（含 `{ID}` 已填 / `{AUTO_ID}` 待回填）；新增 `register_automation` / `get_automation`；`list` 显示各实例绑定的自动化 id
- 重写 `C:/Users/Administrator/.workbuddy/skills/meta-method-goal-mode/SKILL.md`：定位为自包含自动化技能；调用协议 = 捕获→spawn→建专属自动化→首轮即时执行→交棒；明确"每窗口独立并行、无单全局排队"
- 扩展 `F:/aidanao/meta-goal-system/test_meta_goal.py`：增 `register_automation` 往返测试 + `spawn` 打印自动化 prompt 测试（现 11 测试全过）
- 停用旧全局串行轮询自动化 `automation-1783781472384`（status=PAUSED），避免与每实例自动化双重执行

#### 3. 设计原因
- **用户明确选择 Fork B（每窗口独立并行）**：早前我给的选项里用户没选，本轮直接拍板"每个窗口独立跑"。这彻底否定了 Round 2 的"单全局注册表轮询"模型——那个模型会让多任务串行排队，与诉求冲突。
- **每实例专属自动化 = 真·并行**：spawn 时即用其打印的 prompt 创建一个只服务该实例的自动化（rrule 每小时、FULL_AUTO），多个任务各自一个循环同时跑、互不读对方状态。
- **自我停止**：prompt 注入自动化自身 id（`{AUTO_ID}`），实例 COMPLETE 后调 `automation_update` 把自己 `PAUSED`，不空转。
- **诚实边界不变**：仍写清"技能无法隔空读另一窗口实时内容，须在该窗口显式交任务"。

#### 4. 运行方法
```
cd F:/aidanao/meta-goal-system
python meta_goal.py spawn "任务名" --task "描述"   # 任何窗口新建独立实例（打印专属自动化 prompt）
# 然后用打印的 prompt 调 automation_update create（{ID} 已填）→ 拿到 auto_id → update 回填 {AUTO_ID}
python meta_goal.py list                          # 看各实例及其绑定自动化
python meta_goal.py guard <id>                     # 代码级刹车判定
```

#### 5. 测试方法
```
python test_meta_goal.py
# 期望: 11 测试全过（原 9 + register_automation 往返 + spawn 打印自动化 prompt）
```
实测：11 测试全过 ✅；live demo 真实创建一个专属自动化 `automation-1783783450678` 绑定实例 `g_20260711232352`、`list` 正确显示、`guard` 正常，清理后注册表回 1、全局轮询已 PAUSED ✅。

#### 6. 已完成内容
- 执行模型改为每实例独立并行自动化（取代单全局串行轮询）
- `spawn` 输出专属自动化 prompt 模板 + 引擎支持注册/查询自动化 id
- SKILL.md 重写为自包含自动化技能，含完整调用协议与诚实边界
- 旧全局轮询自动化已 PAUSED（防双重执行）
- 测试扩至 11 个，全过；端到端 live demo（真实建/绑/删自动化）通过

#### 7. 未完成内容（标 TODO / Interface / Mock）
- `Interface`: L6 每实例 milestone 自动写入（`POST /api/goal/milestone`，各实例 sb_goal_id 已在注册表）→ Round 5 接线
- `Interface`: L7 `/api/evolve/cycle` 每轮后自动调用（端点已知，未接）
- `Interface`: L8 `/api/agent/orchestrate` 重大决策审计（未接）
- `TODO`: 四象限节点自动写入 `/api/knowledge-graph`（未做）
- `Future Roadmap`: 外部看门狗（独立脚本）对 guard 结果二次裁判，防执行器自我判进展偏乐观
- `Future Roadmap`: spawn 时第二大脑 goal 的回收（目前清理只删本地实例，SB goal 留 orphan，无害）
- `Future Roadmap`: MCP(tdx/westock) 在自动化上下文可用性验证；Q4 承认无知协议落地为探针模板
- `Future Roadmap`: 完成任务的实例自动化"自我 PAUSED"后，是否需要一个轻量清理把对应 SB goal 也关掉

#### 8. 风险
- 多自动化并行：每个任务一个自动化，N 个任务 = N 个每小时触发；token 消耗随任务数线性增长（用户已授权最大权限，接受）。
- 旧全局轮询已 PAUSED，但若未来误恢复会双重执行 → 已在其 prompt 失效，且每实例自动化独立 guard，即使双跑也只会重复追加报告（不破坏数据）。
- spawn 创建的 SB goal 与自动化 id 均由 `register_automation` 记录在注册表，可审计、可手动清理。
- 鲜实例（ROUND:0）自动化首跑须先 2x2 分解再校验（prompt B 分支已规定）。

#### 9. 下一轮建议
**Round 4 = 只做一件**：把 L6 milestone 自动写入接进每实例自动化流程——自动化每推进一轮，用该实例注册表的 `sb_goal_id` 调 `POST /api/goal/milestone` 落库；并在测试里加一个 mock 端点验证调用逻辑。不扩其他层。

---

## 第二大脑关联（已验证接口）
- 目标系统：`POST /api/goal/create`（goal_type∈daily/weekly/monthly/quarterly/yearly/life）→ 已建 goal `goal_85449be5441c43`，状态 `dreaming`
- 里程碑：`POST /api/goal/milestone`（待 Round 5 接线）
- 自进化：`POST /api/evolve/cycle`、`GET /api/evolve/mode`（未接线）
- 多 Agent：`POST /api/agent/orchestrate`（未接线）
- 知识图谱：`/api/knowledge-graph`、`/api/verify/all`（未接线）

## Round 4（2026-07-11，并发上限=3 + 调度闸门）

#### 1. 本轮目标
实现全局并发上限=3：任何窗口 spawn 的任务实例，同时最多 3 个持有活跃自动化循环；超出自动排队，待槽位空出由【调度闸门】自动唤醒。把用户口头的"一般最多3个同时跑"变成代码可强制的硬上限。

#### 2. 修改文件
- `meta_goal.py`：
  - 新增常量 `MAX_CONCURRENT=3`（可用环境变量 `MG_MAX_CONCURRENT` 覆盖）
  - 新增 `count_running()`（统计非 bootstrap 的 active 实例数，用于上限判定）
  - 新增 `dispatch()`（调度闸门用：满槽→`NO_PROMOTION`，有空槽→逐行 `PROMOTE <id>`）
  - 新增 `activate()` / `deactivate()`（排队→active / 完成→释放槽位）
  - 新增 `automation_prompt()`（打印某实例专属自动化 prompt，供闸门建自动化）
  - 改造 `spawn()`：超上限则实例状态置 `queued` 且不打专属自动化 prompt；并修复 spawn id 用秒级时间戳导致快速连续 spawn 撞 id 的 bug（改为微秒精度 + 存在性重试）
  - `list` 底部增加 `活跃/上限/排队` 汇总
  - `main()` 增加 `dispatch` / `activate` / `deactivate` / `automation-prompt` 子命令
- `SKILL.md`：新增"并发上限=3"章节与调度闸门说明，补命令速查，修正"互不排队"表述为"超上限才排队"
- `test_meta_goal.py`：新增 `test_max_concurrent_default` + `test_concurrency_cap_and_dispatch`（受控注册表验证满槽排队/释放后 PROMOTE），共 13 测试
- 新建自动化 `automation-1783785810205`（元方法论·并发调度闸门，每 60 分钟触发，只开门不跑任务）
- 删除旧全局串行轮询自动化 `automation-1783781472384`（已停用，避免混淆）

#### 3. 设计原因
- 用户拍板"一般最多3个任务同时跑"——这是资源/消耗的硬约束，必须可执行，不能只靠口头约定。
- **闸门只开门、不跑任务**：调度逻辑集中在单个轻量自动化（每 60 分钟），它只负责"槽位空出→建专属自动化→activate"，不执行任何任务内容。这既维持了"每窗口独立并行"模型（每个任务仍各跑各的循环），又用最小新增代价实现了上限。
- **排队不丢失**：超上限的实例以 `queued` 状态留在注册表，槽位空出即被 `PROMOTE`，不会因瞬时超过 3 个而丢任务。
- **释放闭环**：实例完成时其自动化调 `deactivate <id> paused` 释放槽位 → 下一个排队项下一轮被闸门唤醒，形成可持续的并发池。
- 顺带修了 spawn id 碰撞 bug（秒级时间戳在同一秒内连续 spawn 会 `FileExistsError` 丢实例）——演示中暴露的真实缺陷。

#### 4. 运行方法
```
cd F:/aidanao/meta-goal-system
python meta_goal.py spawn "任务A" --task "..."   # 第1~3个 → active（打印专属自动化prompt）
python meta_goal.py spawn "任务D" --task "..."   # 第4个 → queued（不建自动化）
python meta_goal.py list                          # 看 活跃/上限/排队
python meta_goal.py dispatch                      # 闸门逻辑：满槽NO_PROMOTION / 有空槽PROMOTE
python meta_goal.py deactivate <id> paused        # 实例完成→释放槽位
# 真实唤醒由自动化 automation-1783785810205 每60分钟自动执行上述 dispatch→建自动化→activate
```

#### 5. 测试方法
```
python test_meta_goal.py
# 期望: 13 测试全过（含 test_concurrency_cap_and_dispatch）
```
实测：13 测试全过 ✅；live demo 真实 spawn 4 个 → list 显示 3 active + 1 queued；满槽 dispatch=NO_PROMOTION；deactivate 1 个→dispatch=PROMOTE 第4个；清理后注册表回 1、validate PASS ✅。

#### 6. 已完成内容
- 并发硬上限=3 落地（spawn 排队 + 闸门唤醒闭环）
- 调度闸门自动化创建并 ACTIVE；旧全局轮询已删
- spawn id 碰撞 bug 修复
- 测试扩至 13 个并全过

#### 7. 未完成内容（标 TODO / Interface / Mock）
- `Interface`: L6 每实例 milestone 自动写入（`POST /api/goal/milestone`）→ 顺延至 **Round 5**
- `Interface`: L7 `/api/evolve/cycle` 每轮后自动调用（未接）
- `Interface`: L8 `/api/agent/orchestrate` 重大决策审计（未接）
- `TODO`: 四象限节点自动写入 `/api/knowledge-graph`（未做）
- `Future Roadmap`: 外部看门狗（独立脚本）对 guard 二次裁判，防执行器自我判进展偏乐观
- `Future Roadmap`: spawn 时第二大脑 goal 回收（目前清理只删本地实例，SB goal 留 orphan，无害）
- `Future Roadmap`: MCP(tdx/westock) 在自动化上下文可用性验证；Q4 承认无知协议落地为探针模板
- `Future Roadmap`: 完成实例自动化自我 PAUSED 后是否需要轻量清理关闭对应 SB goal

#### 8. 风险
- 闸门每 60 分钟检查一次：槽位空出后排队任务最多等 1 小时才被唤醒（可接受；如需更快可改 rrule 为更密）。
- 闸门本身是独立自动化，若其被误删，排队实例不会被唤醒 → 已记录其 id（automation-1783785810205），可重建。
- 并发=3 是用户当前拍板；若日后想调，改 `MAX_CONCURRENT` 或环境变量即可，无需改逻辑。

#### 9. 下一轮建议
**Round 5 = 只做一件**：把 L6 milestone 自动写入接进每实例自动化流程——自动化每推进一轮，用该实例注册表的 `sb_goal_id` 调 `POST /api/goal/milestone` 落库；并在测试里加一个 mock 端点验证调用逻辑。不扩其他层。

---

## Round 5（2026-07-12）— 完成事件即时触发（事件驱动调度）

> 用户决策：1) 完成事件就触发，全程不要停；2) 你抓主意。故本轮把"排队唤醒"从定时(60min)升级为事件驱动(完成即触发)，并修一处会令调度失灵的 CLI 缺口。

### 1. 本轮目标
把并发调度从"定时闸门轮询"升级为"完成事件即时触发"：任一实例完成/暂停释放槽位时，立即唤醒下一个排队实例，不等 60 分钟。

### 2. 修改文件
- `meta_goal.py`：① 重写 `AUTOMATION_PROMPT_TEMPLATE` 自我停止段，加入"完成事件即时触发 dispatch"指令；② 修复 `register-automation` 无 CLI 子命令的缺口；③ 修正 spawn 队留言("15分钟"→事件驱动+60min兜底)。
- `SKILL.md`：同步"完成事件即时触发(主)+调度闸门兜底(次)"模型 + 命令速查补 `register-automation`。
- `test_meta_goal.py`：+2 测试（事件驱动指令在模板中 / register-automation CLI）。

### 3. 设计原因
- 用户要"全程不要停"：定时闸门最密 60min，槽位空出后排队项最多等 1 小时——违背"不停"。事件驱动让完成即唤醒，等待≈0。
- **抓主意之决**：闸门自愈(脚本重建自动化)不做——事件驱动是自触发，每个实例完成时自己唤醒下一个，无单点故障；闸门仅作廉价兜底，比脆弱的自重建更稳。
- **修 CLI 缺口是必需**：Round 4 闸门 prompt 引用了 `register-automation` 子命令，但 `main()` 从未注册它 → 真实运行会"未知子命令"。事件驱动也用它，不修则唤醒链路断。

### 4. 运行方法
```
python meta_goal.py list
python meta_goal.py dispatch                       # 手动模拟完成事件触发
python meta_goal.py register-automation <id> <auto_id>
```

### 5. 测试方法
```
python test_meta_goal.py
# 期望: 15 测试全过（新增 test_event_driven_in_prompt_template / test_register_automation_cli）
```
实测：15 测试全过 ✅；live demo spawn 4 → 3 active + 1 queued；队留言含事件驱动措辞；满槽 dispatch=NO_PROMOTION；清理回 1、validate PASS ✅。

### 6. 已完成内容
- 事件驱动唤醒链路落地（模板指令 + 修复 CLI 缺口）
- 调度闸门角色从"主"降为"兜底"（仍 ACTIVE，每 60min 防漏）
- 文档与代码一致
- 测试 13 → 15 全过

### 7. 未完成内容（标 TODO / Interface / Mock）
- `Interface`: L6 每实例 milestone 自动写入（`POST /api/goal/milestone`）→ 顺延 **Round 6**
- `Interface`: L7 `/api/evolve/cycle` 未接
- `Interface`: L8 `/api/agent/orchestrate` 未接
- `TODO`: 四象限节点入库 `/api/knowledge-graph`
- `Future`: 外部看门狗二次裁判 guard
- `Future`: SB goal 回收 / MCP 自动化可用性 / Q4 探针模板
- `已知局限(Mock)`: 平台自动化最密为每小时触发一次，故"事件驱动唤醒"指**创建+激活自动化即时**，但被唤醒实例的**首轮执行**仍按其每小时调度运行（非秒级即时跑）。这是 WorkBuddy 自动化机制的物理下限，非本系统缺陷。

### 8. 风险
- 事件驱动依赖完成实例的自动化"老实执行" self-stop 段里的 dispatch 步骤；若某次运行在 dispatch 前崩溃，60min 闸门兜底仍会唤醒（双保险）。
- 平台下限：被唤醒实例首轮执行仍按 hourly 调度，最坏等 ~1h 才真正开跑（仅执行节奏，非调度延迟）。
- 闸门若被误删：事件驱动路径仍独立工作（不依赖闸门），故不影响核心能力；仅失去兜底。

### 9. 下一轮建议
**Round 6 = 只做一件**：L6 milestone 自动写入——每实例自动化每推一轮，用注册表 `sb_goal_id` 调 `POST /api/goal/milestone` 落库；加 mock 端点测试。不扩其他层。

四象限映射（本轮回合）:
- 已知·已说: 完成事件就触发、全程不要停、你抓主意
- 已知·未说: 平台自动化最密=每小时(执行节奏有下限)；每实例独立自动化是既有模型；用户接受最多3并发
- 未知·可懂: 事件驱动调度的工程实现(自触发 dispatch + 修复 CLI 缺口)—已落地
- 未知·不懂: 被唤醒实例能否"即时执行首轮"受平台限制(已降级为 Mock/已知局限，非缺陷)

---

## NEXT_ROUND
Round 6（只做一件）：L6 milestone 自动写入——每实例自动化每轮用注册表 sb_goal_id 调 POST /api/goal/milestone 落库 + 加 mock 测试。不扩其他层。
Round 7 备选：外部看门狗——独立读各实例 guard 结果做二次裁判（Future Roadmap 落地）。

---

## 变更记录（用户指令驱动，非自治 Round）

### 2026-07-12 用户指令：移除独立"并发调度闸门"每小时自动化
- **动作**：删除 `automation-1783785810205`（原每 60 分钟调 dispatch 的兜底闸门）。
- **能力迁移**：原闸门的兜底职责（唤醒排队项 PROMOTE + 补建孤儿 START）迁移到：
  ① 每个实例专属自动化 **self-stop 段**当场跑 `dispatch`（完成事件即时触发，原已存在）；
  ② 每个实例专属自动化 **每轮动作开头**（新增第 0 条）跑 `dispatch` 兜底。
- **结果**：本系统**不再有任何独立定时触发器**。"持续不断"完全由"完成事件即时触发 + 各活跃实例每轮自带 dispatch 兜底"承载；排队项/孤儿仍会被及时唤醒，不假死。
- **并发模型不变**：上限=3、超出排队、槽位空出由活跃实例每轮 dispatch 唤醒，逻辑经测试验证完好。
- **验证**：`test_meta_goal.py` 16 项全过（含 `test_per_round_dispatch_fallback_in_prompt` 断言模板不再含"调度闸门"字样）；spawn 4→3active+1queued、满槽 NO_PROMOTION、释放槽位 PROMOTE 实测通过。
- **Round 4/5 历史报告**中关于"调度闸门"的描述保留为审计痕迹，不代表当前架构。


---


---


---


---


---


---


---


---


---


---


---


---
