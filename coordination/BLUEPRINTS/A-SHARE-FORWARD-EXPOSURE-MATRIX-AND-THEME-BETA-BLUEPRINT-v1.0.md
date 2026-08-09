# A股前视暴露矩阵与主题Beta/个股Alpha蓝图 v1.0

> blueprint_id: `A-SHARE-FORWARD-EXPOSURE-MATRIX-THEME-BETA-0001`
>
> status: `REGISTERED_CANDIDATE / IMPLEMENTATION_ISSUES_OPEN`
>
> boundary: `research_only / NO_TRADE`
>
> parent_workstream: `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-0015 / W5`
>
> initial_targets: `300418.SZ 昆仑万维`, `300058.SZ 蓝色光标`
>
> parent_issue: `#199`
>
> kunlun_issues: `#211 #212 #213 #214`

## 0. Mission

建立一套可点时回放、可版本化、可回测的“公司前视暴露矩阵”，解决传统行业分类和历史财报权重滞后于股票市场预期的问题。系统必须回答：

1. 公司当前经济价值来自哪些应用/业务；
2. 哪些技术能力正在改变未来2~3年的增长与利润结构；
3. 二级市场当前实际交易哪些题材/叙事；
4. 某行业/题材启动后，目标股跟随概率、领先/滞后、持续性如何；
5. 当日涨跌中多少来自宽基、行业、主题，多少来自个股自身Alpha；
6. 利好是否已提前交易，板块强而个股弱是否构成负面信息。

不得把静态财报占比直接当股票交易权重，不得把技术底座和商业应用平铺进同一100%饼图重复计权。

## 1. 三层图谱

### A. Application / Monetization 经营变现层

互斥，必须归一化100%。只表示未来经济价值池，不表示技术能力。FFW只在本层归一化。

### B. Technology / Option 技术能力与期权层

非互斥，不要求合计100%。技术节点通过版本化 `technology_to_application_matrix` 赋能一个或多个应用节点；不得与Application层直接相加。

### C. Market / Style 市场交易控制层

宽基、行业、主题和跨市场代理，不属于经营100%。用于估计Market Beta、Industry Beta、Theme Beta及事件传导。

## 2. 五类对象必须物理分离

- `financial_rearview`：历史财务后视镜；
- `ffw_application`：Forward Fundamental Weight，未来2~3年经营价值权重；
- `tech_option_exposure`：技术能力/期权暴露；
- `mtw_market_narrative`：Market Trading Weight，当前股价交易叙事；
- `short_term_overlay`：事件/情绪/资金快变量。

每个对象必须拥有 `version / effective_at / source_cutoff / method_id / confidence`，禁止互相覆盖。

## 3. FFW：经营前瞻权重

基础解释框架：

`score_i = f(B_i, G_i, T_i, S_i)`

其中：
- `B` Current Base：收入、毛利、ARR/流水、现金贡献、MAU/客户数；
- `G` Realized Growth：收入/ARR/MAU/使用量/ROAS/毛利率/API或产品采用；
- `T` Future Opportunity：行业CAGR、TAM可变现性、渗透阶段、成本曲线、竞争地位、监管；
- `S` Strategic Commitment：战略级别、研发/算力/组织投入、迭代频率、API开放、产品协同，建议限制0.85~1.15。

工程实现优先采用 `prior + evidence shrinkage`，而不是每次重新线性洗牌：

`posterior_logit_weight_i = prior_logit_weight_i + evidence_strength_i`

随后softmax/归一化。证据不足时向prior收缩；正式财报、ARR、MAU、ROAS、重大战略才允许升级base version。极端增长必须winsorize/log/rank处理，不得把数百%同比线性放大。

## 4. MTW：市场交易权重

MTW回答“当前股价在交易哪条故事”。`M`不得由新闻热度拍脑袋，应主要由：

- rolling orthogonal theme beta；
- 事件AR/CAR；
- 1/3/5/20D相对残差；
- 量价、换手、CVD/资金流（可用时）；
- 方向一致率、持续性、领先/滞后；
- regime-conditioned OOS表现。

采用prior+evidence收缩，并设置single-update max step、freshness decay、overlay half-life、reason codes。

期限融合原则：
- 1~5D：MTW主导；
- 20~60D：MTW/FFW近均衡；
- 6~18M：FFW主导。

具体系数只允许walk-forward校准，禁止全样本过拟合。

## 5. 主题启动客观定义

不得事后凭感觉。至少结合：

- factor basket return z-score；
- breadth；
- relative volume/turnover；
- excess return vs broad market/industry；
- persistence。

阈值只在训练窗学习。高度相关因子先从主题篮子剥离broad market + industry，得到orthogonal theme residual，再估计目标股Beta。

## 6. 收益归因

每日/事件至少分解：

`target_return = market + industry + orthogonal_theme + company_event + unexplained_residual`

分类输出：
- `MARKET_BETA`
- `INDUSTRY_BETA`
- `THEME_BETA`
- `LEADER_EARLY_MOVE`
- `COMPANY_ALPHA`
- `NEGATIVE_IDIOSYNCRATIC`
- `UNRESOLVED_MIXED`

## 7. 回测

窗口：60D / 120D / 250D；方法至少比较OLS、Ridge、Elastic Net、Robust Regression。

事件研究：日线 `[-20,+20]`, `[-5,+10]`, `[-1,+5]`；有分钟数据时 `[-60m,+240m]`。

长期输出：
- `P(target up | theme start)`；
- `P(target alpha > threshold | theme start)`；
- same-day/T+1/3D/5D/10D；
- average/median excess return；
- false-follow rate；
- lag distribution；
- regime split；
- sample size + confidence interval。

必须有placebo、negative controls、label permutation、多重检验、overlapping-event处理、walk-forward/OOS。样本不足返回 `INSUFFICIENT_SAMPLE`，不得伪造精确概率。

## 8. 点时与防未来泄漏

继承W5现有本体：`announced_at / first_public_at / published_at / available_at / market_effective_at / knowledge_cutoff / source_version`。

硬规则：
- 盘后消息不得解释当日盘中；
- 后来确认的传闻不得回填为当时已知；
- 后来修订的财务数据不得替换首次已知值；
- 代理篮子必须有effective_from/effective_to，防幸存者偏差；
- 同日A股代理与隔夜港美股代理必须分别标记时间可用性，不能混用为预测变量。

## 9. Proxy质量四维评分

代理资产不得只用一个“纯度分”。至少拆：
- `business_purity`：业务机制相似度；
- `data_quality`：历史数据完整与稳定性；
- `timing_usability`：在目标市场开盘前是否已可观察；
- `redundancy_penalty`：与篮子内其他代理重复程度。

同日A股同行主要用于共振/归因；隔夜港美股代理更适合作前置传导因子。

## 10. 昆仑万维配置 v2.1

### Financial rearview
2025财务后视镜永久保留，不作为前视交易真值。

### Application FFW initial prior（回测起点，非统计真值）
- AI短剧/DramaWave/FreeReels：36%
- Opera广告/搜索/AI浏览器：28%
- Agent/生产力工具：12%
- AI音乐平台：8%
- AI社交：6%
- AI游戏：5%
- 传统游戏：3%
- 其他/投资：2%

合计100%。

### Technology option exposure（非互斥）
- SkyReels视频生成
- Mureka音乐音频底座
- R1V/UniPic视觉语言与统一多模态
- Matrix世界模型
- Text/Reasoning/Agentic底座
- Physical-AI/机器人期权（仅潜在外溢，未商业化前受成熟度闸门约束）

### Market controls / proxies
宽基至少：沪深300、创业板指、深证成指；行业至少：申万传媒、申万游戏II、中证人工智能主题。

主题代理包括：OPRA/Alphabet/Meta/Microsoft/Baidu；中文在线、快手-W、万兴科技、美图；科大讯飞、金山办公；Spotify、腾讯音乐；Google DeepMind世界模型/NVIDIA Physical AI等事件源。机器人行情不得机械映射昆仑。

## 11. 蓝色光标配置 v1.0

### Financial rearview（2025）
- 出海广告投放：82.25%
- 全案推广服务：12.60%
- 全案广告代理：5.15%

AI驱动收入37.25亿元、约占总收入5.42%，属于横跨多个业务线的“经营方式/技术驱动维度”，不得与上述三项直接相加。2025 AI驱动收入同比+210.42%；其中约20亿元来自出海业务，管理层披露该部分毛利率约为公司正常平均毛利率的5~10倍。出海收入564.96亿元，占总收入超82%。

客户行业后视维度：游戏42.82%、电商23.87%、互联网及应用23.61%、其他约9.70%；互联网及应用2025同比+71.75%，其中大模型、AI短剧等客户投放增加是重要驱动。

### Application FFW initial prior（回测起点，非统计真值）
- 全球效果广告/媒体采购基本盘（非AI基础部分）：31%
- AI原生自动投放/Agentic Marketing：24%
- AI内容/视频/多模态创意生产：12%
- 全球化2.0海外本地整合营销：12%
- 国内全案/品牌整合营销：7%
- AI达人/社交/GEO/数字员工等AI营销服务：6%
- Blue X / Blue Turbo / 自建流量与AdTech平台：6%
- 战略AI投资与其他：2%

合计100%。

### Technology option exposure（非互斥）
- Blue AI自动投放与A2A Agent协同
- AI视频/多模态创意生产（含与外部视频模型生态协同）
- AI达人/社交智能
- GEO/生成式搜索优化
- 数据/Token/营销知识基础设施
- 自建程序化/流量平台Blue X、Blue Turbo
- AI Native战略投资期权（PixVerse爱诗科技、AhaCreator、OpenHex、PureblueAI、Pepr AI、AGI House等，需按持股/商业协同/流动性单独限权）

### Market Trading Narrative initial prior（回测起点）
- AI营销/Agentic AdTech：31%
- 出海数字广告/全球化：24%
- AI视频/内容/短剧营销：17%
- Meta/Google/TikTok等全球媒体景气：10%
- AI应用客户预算/互联网应用广告需求：7%
- 跨境电商营销：5%
- 国内广告营销：3%
- AI投资期权：3%

合计100%。

### BlueFocus market controls / proxies
宽基优先：创业板指、创业板50、中证500（若点时成分确认）、深证成指；行业：申万传媒、申万广告营销/营销代理；主题：AI应用、AI营销、数字广告、出海营销、AI视频、短剧、跨境电商。

高优先级海外前置代理：Meta、Alphabet、TikTok/ByteDance事件、AppLovin、Moloco、The Trade Desk、Amazon Ads及广告/电商平台财报；同日A股共振代理：易点天下、引力传媒、浙文互联、省广集团、因赛集团等需经purity与点时成分筛选。AI视频/短剧客户需求代理需与“蓝标自身AI视频生产能力”分开建因子，避免需求端与供给端重复解释。

## 12. 蓝标特殊机制

蓝标与昆仑不同：蓝标不是以自有模型能力为核心估值，而是“全球流量代理能力 + 客户预算 + AI自动化提升毛利 + 自建平台减少对头部媒体依赖”的组合。

因此蓝标的主要未来重估条件不是单纯AI模型SOTA，而是：
1. AI驱动收入占比继续提升；
2. AI驱动业务高毛利优势可持续；
3. Blue AI自动投放的人力替代与ROAS改善真实兑现；
4. 互联网/AI应用/短剧客户广告预算持续高增；
5. 532利润结构从目标变成真实毛利/收入结构；
6. Blue X/Blue Turbo及腰部媒体提高利润贡献，降低Google/Meta/TikTok集中度；
7. 全球化2.0海外本地办公室从扩张转向规模盈利。

## 13. 数据与资源政策

第一阶段日线+分钟线，不因本蓝图提前购买逐笔/L2。只有日/分钟层证明盘口变量有稳定增量后，复用#199的 `DATA_PURCHASE_READY` 门禁。

本机资源约束沿用现有LOCAL_RESOURCE协议：禁止无上限多进程、禁止nested parallelism、批次完成清理任务所属子进程，避免Python进程泄漏影响用户交互。

## 14. Implementation sequence

1. 昆仑：#212 -> #213 -> #214；
2. 蓝标：建立对应A/B/C实施Issue，优先复用同一引擎与schema，仅配置不同company registry；
3. 形成共享engine + company-specific config，禁止复制两套回测代码；
4. 每日报告消费统一contract，但必须分别输出昆仑和蓝标的FFW/MTW/tech exposure/attribution；
5. 回测完成前，所有百分比均标记 `PRIOR / NOT STATISTICAL TRUTH`。
