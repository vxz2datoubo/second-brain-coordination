# 交易系统可持续接力：交付与验证入口

agent_id: CODEX

状态：`SUCCESS_WITH_FINDINGS`（本轮候选架构/技能/合成验证完成；完整交易系统未验收）。实际独立复核者：尚未复核。指定复核角色：GPT。

## 实际执行结果

验证代码版本：`db7bbbe78e1d0e71eae714a3f531e95fa1f22269`。其后的本包结果归档仅增加文档/证据，不应冒称后续整个提交已重新做独立验收。

- [GitHub 云运行成功回执](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/33926390665)：在干净 Linux runner 检出上述 SHA，163 个原 P2 测试、5 个验证器测试及两次真实回放均成功。
- Windows 本地同一 SHA、Python 3.13.3 两次真实回放成功。
- 下载云端工件后，逐项重算 JSON 内容哈希；本地/云端源码、锁、验证器、Python 版本和 **13 个结果工件全部一致**。
- 结果集合 SHA-256：`c52ea3a7fb489d47311b5b9ee2d147a977f61847a96b79b3250cffe05102c3a6`。
- [候选 Draft PR #588](https://github.com/vxz2datoubo/second-brain-coordination/pull/588)，未合并。
- [精简长期验证记录](VERIFICATION.json)；完整公开合成工件在上述 Actions run（保留 14 天），本机同时留存副本。

这证明 GitHub 上的既有离线研究程序可以真正执行，并与本机一致；不是证明 GPT 当前会话能触发该程序，也不是 WB 服务上线或真实 A 股策略有效。

这次用户希望 GPT 制定方向、Codex 工程架构、WB 实施运行，并在 Codex 不可用时由 GPT 承担详细架构。目标是软件从 GitHub 下载后实际运行，数据和数值可追溯，知识与技能可持续复用。

## 交付入口

- [实施架构、部门接口、部署目录与验收门](skills/trading-system-relay/references/architecture.md)
- [数值与语义防漂移合同](skills/trading-system-relay/references/numeric-contract.md)
- [四层认知、技能和系统映射](skills/trading-system-relay/references/knowledge-map.md)
- [一手资料与研究反证账本](skills/trading-system-relay/references/research-ledger.md)
- [可复用技能](skills/trading-system-relay/SKILL.md)
- [三方交接对象](AI_HANDOFF.yaml)

## 本轮工作过程与证据边界

1. 核对母仓未提交工作、远端 main、公开仓库属性、原交易目录；未覆盖其他 Agent 文件。
2. 在规定的 worktree 目录创建 `codex/trading-reproducible-relay-20260904` 分支，基于远端 `04124e233dc813cca4054851ef6a470b342d82fe`。
3. 发现已有 P1/P2/P3、治理路由、认知映射等架构；改用包装现有 P2，不再建设平行交易系统。
4. 阅读 OpenAI、GitHub、迅投、交易所、Qlib、LEAN 与研究论文的一手资料；来源与限制在研究账本，未声称复现全部论文。
5. 原 P2 裸 Python 测试 163 项中 19 项因 Windows GBK 解码失败；固定 `-X utf8` 后 **163/163 通过**。
6. 新增验证器负例和真实双进程验证测试 **5/5 通过**；技能结构校验通过。测试验证输入漂移、NO_TRADE/时间改变、输出篡改和额外工件拒绝。
7. 实现源码/输入锁、两次独立进程运行、13 工件比较、实际 commit 与环境回执。完成提交后执行，不能拿未提交源码称为精确版本验证。
8. 第一次 GitHub 冷环境测试发现本机已有、云端未声明的 `PyYAML` 测试依赖，CI 因此失败。已在测试依赖文件固定 `PyYAML==6.0.2` 并加入安装步骤。这正说明“本地可运行”不能替代干净环境验证；没有删除失败测试绕过问题。

难度 D2：跨已有治理/市场/知识边界的集成验证，避免重复权威；不是完整交易生产实现。预期影响限于候选交付与验证，不变更现有引擎、任务路由或部署。

## 运行现有程序的单一验证入口

在此分支的干净仓库根执行，输出目录必须此前不存在：

```powershell
python -X utf8 coordination/RESEARCH/TRADING-RELAY-20260904/scripts/prove_replay.py --output F:/aidanao/交易系统/协作验证-唯一运行编号 --agent-id WORKBUDDY --challenge 调用者本次提供的新编号
```

输出包括两个真实子进程的命令与退出码、13 个业务/检查点 JSON、`execution-receipt.json`。运行不需要 LLM、实时行情或券商接口。固定合成输入为 8 个事件；无治理日历时正确拒绝模拟成交。它证明离线研究链执行，不证明完整实盘或盈利。

GitHub Actions 工作流 `Trading relay synthetic proof` 在本研究分支的代码/锁变更时验证；使用 Python 3.13.3、固定 Action 提交、只读权限和 5 分钟上限。CI 产物保留 14 天，不是永久审计存储。正式长期运维需将公开安全精简回执按现有工件治理归档。

## GPT 小测试协议

1. 在用户实际 GPT 会话读取本报告与精确分支 SHA，回传路径与 SHA。这只能证明读取。
2. 若会话有获授权的执行工具，在隔离环境检出同一 SHA，用新 challenge 运行上述验证器；否则状态写 `READ_ONLY_VERIFIED / EXECUTION_UNVERIFIED`。
3. 回传真实执行 URL 或进程回执、source_commit、challenge、artifact_set_sha256、退出码。外部验证端重算业务工件哈希。
4. 若使用 Actions，由真实工具发起并核对 run ID/head_sha/工件；关联挑战只用于区分运行，不是密码学签名。当前用户 GPT 会话不能由本 Codex 会话冒名认证。

## 尚未完成的系统门

本轮没有部署 WB 服务、迁移本机生产、连接真实行情、确认行情再分发许可、验证用户实际 GPT 会话执行权或执行真实交易。下一步是 GPT 独立审核候选并通过现有路由给 WB 发布 G4 合成安装任务，不抢占当前电影项目等活动工作。

本地原系统与远端主仓不一致；原目录的 78 技能清单是历史目录声明，不能算作 78 个已验证运行器。不要据此宣称交易系统已全部完成。

## 改良、负面结果与持续推进

高价值改良已做：复用已有引擎、真实源码绑定、UTF-8 一致性、输入/输出漂移门、候选知识边界。提案未实施：WB 版本化安装/回滚、GPT 当前产品能力测试、真实数据字段许可审计、按通过任务成本评估模型。

额外发现：上交所通知确认 2026 规则已生效且有暂缓条款；未来生产规则包应逐条核验，不用旧聊天记忆填规则。深交所页面及 SSRN 抓取失败记录在研究账本，DSR 已改读作者 PDF。

停止条件依 AGENTS.md：真实凭证/账户、未授权行情、重要文件覆盖、蓝图冲突或真实生产风险。当前成果保持 `research_only / NO_TRADE`，没有自动合并或正式发布授权升级。
