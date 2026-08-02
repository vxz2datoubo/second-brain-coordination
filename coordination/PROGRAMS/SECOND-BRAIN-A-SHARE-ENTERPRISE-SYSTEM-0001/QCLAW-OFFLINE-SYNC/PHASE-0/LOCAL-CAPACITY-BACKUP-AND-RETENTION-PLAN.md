# 本地容量、备份与保留计划

## 当前磁盘占用

| 目录 | 大小 | 年增长预估 | 风险 |
|------|------|-----------|------|
| QCLAW workspace | 7.1 GB | +2-5 GB/年 | 🔴 主要消费者 |
| data/raw (tushare) | 153 MB | +50-100 MB/年 | 🟡 |
| qclaw-output | 2 MB | +5-10 MB/年 | 🟢 |
| qclaw-knowledge (新) | 0 | +50-200 MB/年 | 🟢 |

## 容量监控

| 指标 | 阈值 | 动作 |
|------|------|------|
| 单个目录 >1 GB | warning | 检查是否积压 |
| qclaw-knowledge >500 MB | warning | 考虑归档旧批次 |
| 总QCLAW相关 >15 GB | alert | 清理workspace/过期日志 |
| 磁盘剩余 <10 GB | alert | 紧急清理 |

## 备份策略

### 本地备份
- `state/state.sqlite` → 每日自动备份到 `state/backups/`
- 保留最近30天
- manifest文件备份到 `manifests/backups/`

### 关键数据保护
| 数据 | 备份方式 | 频率 |
|------|---------|------|
| 原始材料 (00-inbox-raw) | 只追加, 不删除 → 自备份 | 持续 |
| 候选包 (02-candidate-packets) | JSONL追加 → 自备份 | 持续 |
| 同步出站箱 (05-sync-outbox) | Git提交后 → 远程备份 | 每批次 |
| 状态数据库 | 本地SQLite备份 | 每日 |

## 清理与保留

### 自动清理
- `01-processing/`: 每次处理完成后清理临时文件
- `logs/`: 30天轮转, 保留最近90天
- `manifests/backups/`: 保留最近30天

### 手动归档
- `06-synced/`: 确认Git推送成功后, 批次可移动到 `archive/`
- `07-quarantine/`: 问题解决后移回正常流或移到 `08-rejected/`
- `08-rejected/`: 永久保留 (审计), 可被superseded

### 永不清除
- `00-inbox-raw/` — 原始材料不可变, 只追加
- `state/state.sqlite` — 状态历史不可丢失
- 同步成功的批次记录 — 审计轨迹

## QCLAW Workspace 清理建议

- `~/.qclaw/workspace-*/` — 40+ agent workspace子目录
- 建议: 识别不再活跃的workspace, 归档到对象存储或本地archive
- Git不管理这个目录 — 需要QCLAW或手动清理
- 预估可回收: 3-5 GB (清理过期Agent workspace)

## 磁盘增长预估

```
Phase 1 (Shell): +5 MB (目录+SQLite)
Phase 2-4 (运行中): +200-500 MB/年 (candidate packets + state)
Phase 5 (生产化): +1-2 GB/年 (with Supabase projection cache)
```

首次Git同步: ~50-200 MB (取决于现有207个文件的分类)
