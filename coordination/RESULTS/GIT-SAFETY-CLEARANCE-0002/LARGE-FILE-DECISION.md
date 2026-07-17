# Large File Decision

## Files Above 10 MB

| Path | Size | Decision | Rationale |
|---|---:|---|---|
| `codex_siliconflow_proxy/.venv/Lib/site-packages/_polars_runtime_32/_polars_runtime.pyd` | `183,019,520` | Exclude | virtualenv binary |
| `data/super_brain_v01.sqlite` | `32,591,872` | Exclude | runtime database |
| `tools/dreamina/dreamina.exe` | `31,879,680` | User decision | third-party binary; better external or separate release asset |
| `data/raw/tushare/top_list.json` | `26,751,803` | Exclude | raw data |
| `data/raw/tushare/limit_up_all.json` | `17,192,198` | Exclude | raw data |
| `data/audit/events.jsonl` | `12,604,445` | Exclude | append-only runtime audit log |
| `backups/skills.zip` | `11,674,160` | Exclude | local backup archive |

## Git LFS Recommendation

当前**不建议**为首次基线引入 Git LFS 作为前置条件。

原因：

1. 当前的大文件大多是本地运行态、备份、二进制或原始数据，不属于首次基线应纳入的内容。
2. 先把安全边界和提交范围理顺，再决定哪些资产值得单独用 LFS 管理。

## Potential Later LFS Candidates

如果后续用户明确要求保留，才考虑进入 LFS 评估：

1. `tools/dreamina/dreamina.exe`
2. 特定的大型、稳定、可再分发样本数据
3. 已批准的二进制发布资产

## Current Recommendation

首次提交阶段：

- 不引入 LFS
- 直接排除大部分 >10MB 文件
- 对二进制和大样本一律转为“用户审批项”
