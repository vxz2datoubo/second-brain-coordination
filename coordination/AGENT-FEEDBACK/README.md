# AGENT-FEEDBACK — 执行反馈与机会雷达

本目录是长期开放的 Agent 执行反馈收集系统。所有非 trivial 任务完成后，执行 Agent 必须在此提交结构化反馈。

## 设计目标

- 让 GPT 看见真实执行环境，不根据理想化假设下达命令
- 避免"只看结果、不看现场"的盲目调度
- 积累可复用的工程经验（问题、方案、发现、机会）
- 帮助 GPT 持续改进任务设计质量

## 目录结构

```
AGENT-FEEDBACK/
  README.md              — 本文件
  TEMPLATE.yaml          — 反馈模板（所有 Agent 共用）
  <task-id>/             — 每个任务的反馈目录
    WORKBUDDY-FEEDBACK.yaml
    CODEX-REVIEW-FEEDBACK.yaml (如适用)
```

## 强制规则

1. 所有非 trivial 任务必须提交反馈
2. 任何字段无内容时写 `none`，不能省略
3. D4/D5、安全风险、范围变化和生产相关问题必须中途立即上报
4. 反馈中的发现、机会和建议要单独列出，不埋在长描述中
5. 涉及密钥/凭证时只报告类别和位置，不粘贴完整敏感内容

## 已完成任务索引

| 任务ID | Agent | 难度 | 状态 | 日期 | 链接 |
|--------|-------|------|------|------|------|
| P0-000-R1 | WORKBUDDY | D3 | SUCCESS_WITH_FINDINGS | 2026-07-17 | [反馈文件](P0-000-R1/WORKBUDDY-FEEDBACK.yaml) |
| P0-000-R2 | WORKBUDDY | D2 | SUCCESS_WITH_FINDINGS | 2026-07-18 | [反馈文件](P0-000-R2/WORKBUDDY-FEEDBACK.yaml) |
| P0-000-R3 | WORKBUDDY | D1 | SUCCESS_CLEAN | 2026-07-18 | [反馈文件](P0-000-R3/WORKBUDDY-FEEDBACK.yaml) |
| P0-000-R4 | WORKBUDDY | D1 | SUCCESS_CLEAN | 2026-07-18 | [反馈文件](P0-000-R4/WORKBUDDY-FEEDBACK.yaml) |

## 全局发现汇总

### 已被吸收为长期规则的发现

1. **Git 历史清理必须检查非标准 refs** (来源: P0-000-R1)
   - 仅检查 branch、tag、`git log` 会产生"看似已清理"的假阳性
   - `refs/codex/turn-diffs/checkpoints/` 可能保留旧 blob
   - 强制检查项：`git for-each-ref --format='%(refname)'` + `git rev-list --all --objects`
   - 详见 [P0-000-R1 反馈](P0-000-R1/WORKBUDDY-FEEDBACK.yaml) `unexpected_findings[0]`

2. **GitHub MCP 工具只读限制** (来源: P0-000-R1)
   - `update_pull_request` 返回 403 "Resource not accessible by integration"
   - 所有 PR body 更新和评论需回退到 `git credential fill` + Python requests

### 待分类的工程机会

- `xargs + shell fork` 在大文件清单场景下的性能限制（已切 Python 子进程方案）

### 已被吸收为交付规则的发现

3. **commit push 后必须 clean clone 验证** (来源: P0-000-R2)
   - 仅本地验证或 `git log --oneline` 不能保证远程文件已真正修改
   - 强制流程：commit 前 `git diff --cached` 逐文件确认 → push 后独立目录 clean clone → 逐文件 grep 关键内容
   - 详见 [P0-000-R2 反馈](P0-000-R2/WORKBUDDY-FEEDBACK.yaml) `root_cause_analysis`

## 关联 Issue

- [Issue #4: 长期收集台 v2（Agent执行遥测、困难、失败、发现、机会与建议）](https://github.com/vxz2datoubo/second-brain-coordination/issues/4)

## 模板版本

当前模板: **v2.0** (2026-07-18 升级，新增 execution_metrics / token_usage / environment / difficulty_delta / special_gains / root_cause_analysis / metrics_provenance)
历史: v1.0 (2026-07-17, P0-000-R1 feedback 生成)
