# 一手资料、工程映射与反证账本

agent_id: CODEX | 检索日期 2026-09-04 | 公开资料定向研究，不是穷尽综述

## 已读取的一手来源

| 来源 | 支持的结论 | 如何接入 | 不支持什么/复核触发 |
|---|---|---|---|
| [OpenAI GitHub 连接说明](https://help.openai.com/en/articles/11145903) | 仓库读取依产品面/权限；普通 GitHub app 的读与 Codex 写能力不同 | G3 分开做读、执行、写探针 | 不证明用户某会话能执行；产品/权限变化重查 |
| [Codex cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment) | 云任务可检出指定分支/SHA，在容器执行命令 | G2/G3 绑定 commit 和依赖 | 容器不天然能接本地行情客户端 |
| [GitHub workflow 故障说明](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows) | 定时任务可能延迟 | CI 用于验证/异步研究；实时路径本地调度 | 不提供实时 SLA |
| [GitHub 安全用法](https://docs.github.com/en/actions/reference/security/secure-use) | Action 依赖和 runner 权限需受控 | 新验证用完整 Action SHA、contents:read、隔离云 runner | 不把公开 PR 接到持有本地交易访问权的 runner |
| [迅投 XtData 官方模块](https://dict.thinktrader.net/nativeApi/xtdata.html) | 有行情接口、订阅和数据功能 | WB 候选 adapter 评估 | 文档存在不证明本机版本、账号许可或可转发数据 |
| [上交所 2026 交易规则发布通知](https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml) | 2026-07-06 生效，并有暂缓实施条款 | rule package 带生效区间和例外清单 | 不能只凭通知填全部交易规则/券商适配 |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | 可参考量化研究的数据、模型、评估工作流 | 借鉴研究工厂合同和基线，不替换已有 P2 | 不证明本项目策略有效，也不自动接 A股本地终端 |
| [R&D-Agent-Quant 论文](https://arxiv.org/abs/2505.15155) | 研究因素/模型协同优化与自动研发 | 用作离线实验建议器候选 | 多 Agent 自动搜索更需记录试验族；作者结果不外推本项目 |
| [LEAN reality modeling](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts) | 撮合、滑点、费用等现实模型需显式建模 | 完善现有模拟器验证清单 | 不能把一般框架默认值当 A 股板块/券商规则 |
| [Bailey / López de Prado，Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) | 选择偏差、非正态会夸大表现 | DS-10 记录所有试验再做校正 | 不是凭单一 DSR 门限认证盈利 |
| [Bailey 等，Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | 模型选择过拟合值得显式量化 | 研究验证计划与失败账本 | 有前提，不能替代时间样本外和真实成本 |

以上是阅读与架构映射；本轮没有复现 Qlib、RD-Agent、DSR/PBO 论文实验，没有声称机器学习训练或私人机构策略掌握。

## 检索到但不能当已完整核验

- [深交所 2026 规则通知](https://www.szse.cn/lawrules/rule/trade/current/t20260424_620190.html)：检索有结果，正文抓取超时；正式规则包需重取原文和附件。
- DSR 的 SSRN 正文入口抓取失败，改读作者网站 PDF，保留这次失败。
- 程序化交易监管：已发现交易所相关官方细则；本轮不构造生产合规结论，实盘仍禁止。
- 用户描述的 WorkBuddy 模型名与性价比：本次没有读取其实际运行环境与账单，保留 UNKNOWN，不用相似型号代替。

## 创造性改进：用已有能力组合，而非堆系统

1. **证据随运行一起交付**：原 P2 已有结果 manifest；薄包装增加真实 commit、输入源码锁、子进程回执和跨机比较。改动小，直接堵住“只在聊天里跑”的问题。
2. **模型可换，验收不可悄悄换**：GPT/Codex/WB 都交相同证据包。经济指标改为每个通过验收任务总成本，把失败、重试和人工修正算进去。
3. **两条反馈分开**：工程失败反馈进入测试和发布；金融失败反馈进入假设、数据和策略。避免“软件跑通”被解释成“策略有效”。
4. **认知解释可变，事实不可变**：对用户给不同深度的说明，但共用同一数值合同与证据图；不用模型摘要回写覆盖事实。
5. **把弃权作为验收成功之一**：没有日历、许可、单位、时效时正确拒绝，是控制系统有效的证据。强行每次输出交易意见会破坏系统可信度。

## 后续研究队列与停止条件

| 优先级 | 问题 | 最小实验 | 关闭条件 |
|---|---|---|---|
| P0 | GPT 当前界面究竟能读/触发/写哪些操作 | 同一 SHA + 新挑战值 + 真实工具回执 | 明确能力卡，不猜测 |
| P0 | WB 冷启动能否运行同一发布包 | 新 release 目录、断网合成回放、重启回滚 | 哈希一致且无隐含环境依赖 |
| P1 | 哪条数据路径许可和字段最完整 | 一条来源、最小白名单、只读 probe | entitlement/单位/PIT/缺口证据齐全 |
| P1 | 现有 P2 金融规则与生产要求的差距 | 当前官方规则包 + 边界案例 | 覆盖范围明确；缺项保持 UNKNOWN |
| P2 | 新模型是否真更省钱 | 同任务集，记录成本/耗时/验收/返工 | 有质量约束的成本比较 |
| P2 | 新策略/周期方法是否有增量 | 预登记、简单基线、试验族、时间样本外 | 无增量也保存结果，不无限优化 |

不以“顶级论文”“大师案例”作效果担保；可复现与反证比称号重要。每个新系统扩展先算净价值、维护负担和回滚成本，优先借用既有模块。
