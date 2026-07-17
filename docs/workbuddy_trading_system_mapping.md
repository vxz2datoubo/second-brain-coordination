# WorkBuddy 交易系统 -> 第二大脑母系统 保留映射与覆盖表

更新时间：2026-07-14
状态：进行中
作用：把 WorkBuddy 当前交易系统作为 A 股交易域权威源，明确哪些能力已接入母系统、哪些只是部分接入、哪些尚未接入、哪些必须覆盖当前旧逻辑。

## 0. 权威顺序

1. `C:\Users\Administrator\.workbuddy\skills\...` 中当前 WorkBuddy 交易技能体系
2. [D:\LiblibAI-workspace\comfyui-deploy-win\ComfyUI\output\SYSTEM_REPLICATION_FOR_CODEX.md](D:/LiblibAI-workspace/comfyui-deploy-win/ComfyUI/output/SYSTEM_REPLICATION_FOR_CODEX.md)
3. [F:\aidanao\docs\SYSTEM_REPLICATION_FOR_CODEX.md](F:/aidanao/docs/SYSTEM_REPLICATION_FOR_CODEX.md)
4. 当前 `brain_core/trading_domain.py` 中的旧代理逻辑、SMA / Breakout / VWAP Proxy ResearchQueue

说明：

- 如有不同，以 WorkBuddy 当前现状为准；除非用户后续明确指定新的最终版权威。
- 如果 WorkBuddy 当前技能定义与旧交易逻辑冲突，以 WorkBuddy 为准。
- 当前 `brain_core` 的职责不是替代 WorkBuddy 技能体系，而是作为母系统协议层、治理层、审计层和记录层。
- 任何尚未真正执行的技能，都必须保持 `Interface`、`Mock`、`Experimental`、`TODO` 或 `Not Implemented Yet` 标记。

## 1. 母系统绑定车道

| 车道 | 绑定对象 |
|---|---|
| `ContextLane` | `SourceRecord` + `EvidenceItem` + `KnowledgeAtom` + `SkillRegistryEntry` + `ModuleStatusRecord` + `BulletinStateRecord` |
| `ConstraintLane` | `KnowledgeAtom` + `ValidationReport` + `StrategyDefinition` + `DecisionRecord` |
| `FeatureLane` | `MarketDataRecord` + `PriceBar` + `FeatureSet` + `IndicatorDefinition` + `ValidationReport` |
| `ResearchLane` | `StrategyDefinition` + `BacktestConfig` + `BacktestResult` + `ValidationReport` + `StrategyReview` + `SelfEvolutionLog` |
| `DecisionLane` | `ForecastRecord` + `DecisionRecord` + `TradeJournal` + `SelfEvolutionLog` |
| `GraphLane` | `KnowledgeAtom` + `RelationEdge` |

## 2. WorkBuddy 顶层控制/数据组件

| 组件 | 当前状态 | 当前仓库证据 | 母系统绑定车道 | 覆盖/冲突说明 | 下一步 |
|---|---|---|---|---|---|
| `a-stock-data` | 部分接入 | `brain_core/trading_domain.py` 已登记 TDX / 腾讯 / WorkBuddy / WeStock / Tushare 路线 | `ContextLane` + `FeatureLane` | 已有数据源注册，但还不是 WorkBuddy 原生多源拉取编排 | 先做统一 source mapping，再补真实拉取 |
| `a-stock-analysis` | 未接入 | WorkBuddy skill 存在；仓库未见同名运行器 | `DecisionLane` + `ContextLane` | 当前无直接承载，不能用旧 `trading_replay` 冒充 | 后续做 read-only analysis bridge |
| `probability-fusion` | 冲突覆盖 | `trading_domain.py` / tests 明确写着 `implementation_status=Interface`、`not_enforced` | `DecisionLane` + `ResearchLane` | 当前策略选择逻辑不能替代多技能概率融合 | 作为最高优先级覆盖当前直接策略选优 |
| `triple-decision-trees` | 冲突覆盖 | WorkBuddy skill 存在；仓库无同名运行链 | `DecisionLane` + `ResearchLane` | 当前 `SMA/Breakout/VWAP` 直接从 replay 跳到治理，缺少主力/游资/散户分枝约束 | 在 `probability-fusion` 后补决策树层 |
| `workbuddy_neodata_market_context` | 已接入 | `trading_a_share_workbuddy_context_snapshot` 已实现，`service.py` 已暴露入口 | `ContextLane` | 当前是 `payload_injected_sample`，不是实时完整链路 | 保持 Experimental，后续切 live |

## 3. WorkBuddy 25 技能映射表

| 技能 | 当前状态 | 当前仓库证据 | 母系统绑定车道 | 覆盖/冲突说明 | 下一步 |
|---|---|---|---|---|---|
| `a-stock-trading-hours` | 部分接入 | `trading_replay` 已写入 A 股竞价时段、T+1 语义与 authority snapshot | `ConstraintLane` + `GraphLane` | 有规则披露，但没有独立 skill runner | 拆出显式 session/time gate |
| `t1-lockup-tracking` | 部分接入 | 已有 `fresh_participation_proxy` / `seasoned_release_proxy` / `t1_lock_pressure_proxy` | `FeatureLane` + `ConstraintLane` + `DecisionLane` | 当前仅 OHLCV 行为代理，不是真 DDX/DDY 锁仓追踪 | 先保持 Experimental，再补真资金字段 |
| `turnover-cap-analysis` | 部分接入 | 权威快照与验证里已披露“锁仓决定校准模式” | `FeatureLane` + `ConstraintLane` | 还没有真实活跃盘/真换手运行器 | 接入 active float 计算和样本外验证 |
| `lockup-depth-analysis` | 部分接入 | 权威快照已纳入 `authority_constraints_snapshot` | `FeatureLane` + `ConstraintLane` | 无独立锁仓深度引擎 | 与 T+1/换手校准一起落地 |
| `supply-test` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` + `DecisionLane` | 当前没有可执行 Supply Test；不得把均线或 VWAP proxy 当成它 | 先进入 ResearchQueue |
| `phase-c-d-transition` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` + `DecisionLane` | 当前没有 Phase runner | 先做 Interface，再走 replay |
| `accumulation-detection` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前没有吸筹检测执行器 | 研究态接入 |
| `absorption-detection` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前没有订单流吸收检测 | 需真实盘口/成交明细后接 |
| `effort-result-climax` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前没有 Wyckoff 量价背离执行器 | 先 Interface |
| `money-flow-warfare` | 冲突覆盖 | 当前系统仍明确“真 DDX/DDY 未接通”；旧 OHLCV 资金代理被权威文档禁止 | `FeatureLane` + `DecisionLane` + `ResearchLane` | 旧代理逻辑不得冒充真实资金博弈 | 真实 DDX/DDY 接通前只保留 Interface |
| `a-share-game-theory` | 部分接入 | 已进 `diagnostic_skill_registry` 与权威快照；无独立 runner | `ConstraintLane` + `DecisionLane` + `GraphLane` | 目前只是知识约束，不是运行态结论 | 后续接入策略复盘/反操纵判断 |
| `anchoring-detection` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `DecisionLane` | 当前没有散户盈亏区间行为引擎 | 先做 Interface + ResearchQueue |
| `sector-rotation-detection` | 部分接入 | WorkBuddy context snapshot 已带 `sector_flow`、`peer_snapshot` | `ContextLane` + `DecisionLane` | 当前只有上下文快照，没有独立板块轮动技能 | 先从 context lane 拆出显式信号 |
| `opening-range` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 现阶段以日线 proxy 为主，无法当成开盘区间技能 | 待分钟线链路更稳定后接入 |
| `vwap-analyzer` | 部分接入 | 已有 `vwap_proxy_*` 特征与 `VWAP Research Slice v0.1` | `FeatureLane` + `ResearchLane` + `DecisionLane` | 当前只是 VWAP proxy，不等于 WorkBuddy VWAP skill 全实现 | 保持 Experimental，继续补一致性与真数据 |
| `volume-profile-chip` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前无 VP/筹码峰执行器 | Interface |
| `liquidity-sweep` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前无流动性扫单识别 | Interface |
| `delta-cvd` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 真实逐笔/订单流未接入 | Interface |
| `stock-catalyst-hunter` | 未接入 | 仅存在于权威技能清单与文档镜像 | `ContextLane` + `DecisionLane` | 当前没有新闻催化 skill runner | 后续接入公告/新闻源 |
| `a-share-call-auction` | 部分接入 | A 股竞价时段规则已进 replay 语义层 | `ConstraintLane` + `DecisionLane` | 仅有时段规则，没有竞价信号执行器 | 待真实竞价数据后接入 |
| `imbalance-detection` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前无盘口失衡执行器 | Interface |
| `footprint-detection` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前无 Footprint 数据链 | Interface |
| `hvn-lvn-nodes` | 未接入 | 仅存在于权威技能清单与文档镜像 | `FeatureLane` + `ResearchLane` | 当前无高低成交节点运行器 | Interface |
| `lps-upthrust-breakout` | 冲突覆盖 | 当前只有 generic `Breakout v0.1`，不等于 A 股 LPS/Upthrust/Wyckoff breakout | `ResearchLane` + `DecisionLane` | 名称相近但语义不同，禁止静默替代 | 后续单独建 skill，不复用 generic breakout 命名 |
| `market-context` | 部分接入 | WorkBuddy 上下文快照已入母系统 | `ContextLane` + `DecisionLane` | 当前有 context sample，但没有完整 market-context skill runner | 拆出明确 signal schema |
| `probability-fusion` | 冲突覆盖 | 见上方顶层组件；当前验证仍写明 `a_share_probability_fusion_not_enforced` | `DecisionLane` + `ResearchLane` | 当前所有 direct strategy ranking 都必须受它覆盖 | 作为交易域下一阶段最高优先级 |

## 4. 当前与 WorkBuddy 明确冲突的旧逻辑

| 当前旧逻辑 | 冲突点 | WorkBuddy 覆盖结论 |
|---|---|---|
| `SMA Trend v0.1` 直接参与主 replay 选优 | 不符合 WorkBuddy 多技能概率融合 + 决策树约束 | 保留为 `Experimental / ResearchQueue`，不得代表主交易决策 |
| `Breakout v0.1` | 不能等同于 `lps-upthrust-breakout` | 保留 generic breakout 身份，后续单独实现 A 股 LPS skill |
| `VWAP Proxy Research v0.1` | 只是 VWAP proxy，不等于 WorkBuddy `vwap-analyzer` 全实现 | 保留 `Proxy Research` 命名，继续受一致性和真数据守门 |
| OHLCV 行为代理对资金流/锁仓的推断 | WorkBuddy 明确要求真 DDX/DDY 优先，OHLCV 不得冒充真资金 | 只能维持 `Experimental`，并在 ValidationReport 中持续披露 |

## 5. 立即执行顺序

1. 先把本表作为母系统治理资产登记。
2. 公告栏记录：WorkBuddy 映射与覆盖表已建立。
3. 交易域后续开发以本表为准，优先实现：
   - `probability-fusion`
   - `triple-decision-trees`
   - `t1-lockup-tracking`
   - `turnover-cap-analysis`
   - `vwap-analyzer`
4. 当前 `SMA / Breakout / VWAP Proxy` 仍保留，但全部留在 `Experimental / ResearchQueue / no_trade` 轨道。

## 6. 当前结论

- WorkBuddy 交易系统可以并入母系统。
- 但并入方式不是“拷一份 md 就算完成”，而是“以 WorkBuddy 为交易权威层，母系统负责协议、治理、审计、复盘、公告栏和进化记录”。
- 从当前真实状态看，`workbuddy_neodata_market_context` 已接入，`a-stock-trading-hours / t1-lockup-tracking / turnover-cap-analysis / vwap-analyzer / market-context` 处于部分接入，`probability-fusion / triple-decision-trees / money-flow-warfare / lps-upthrust-breakout` 是下一阶段必须覆盖当前旧逻辑的关键点。
