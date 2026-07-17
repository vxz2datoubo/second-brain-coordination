# second-brain-coordination
第二大脑、WorkBuddy、Codex、GPT协作中枢

## 项目简介

本仓库是「第二大脑」系统的协作中枢，承载：
- **交易系统**：A股AI量化交易与主导行为机制推断平台
- **第二大脑**：认知操作系统——记忆/知识证据/资产/检索/规划/协作
- **合作控制面**：多Agent（WorkBuddy/Codex/GPT）受控联动层

## 当前状态

`research_only / NO_TRADE` — 不进行真实交易。

## Agent 署名

GPT、Codex、WorkBuddy 使用同一 GitHub 账号。每份提交和报告必须显式写明 `agent_id`。

固定值：
- `agent_id: WORKBUDDY`
- `agent_id: CODEX`
- `agent_id: GPT`
- `agent_id: USER`

## 目录结构

```
.
├── README.md                ← 本文件
├── AGENTS.md                ← Agent协作规则
├── SECURITY.md              ← 安全策略
├── .gitignore               ← 排除凭证/大文件/构建产物
├── docs/
│   ├── blueprints/          ← 权威蓝图（受保护）
│   ├── adr/                 ← 架构决策记录
│   └── handoff/             ← 多Agent交接包
├── governance/              ← 规则/风控/策略
├── services/                ← 服务模块
├── libs/                    ← 共享库
├── adapters/                ← 外部接口适配
├── tests/                   ← 测试
└── scripts/                 ← 运维脚本
```

## 蓝图

权威蓝图（`docs/blueprints/`，只读）：
- `01_交易系统.md` — 企业级A股AI量化交易与主导行为机制推断平台
- `02_第二大脑_系统蓝图_v3.0.md` — 认知操作系统与知识库
- `03_交易系统与第二大脑_合作机制_v1.0.md` — 协作控制面

## 许可

未定。当前为私有仓库，仅供项目成员使用。
