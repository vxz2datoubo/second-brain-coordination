# 批量同步与恢复计划

> `agent_id: WORKBUDDY` | `task: PHASE0`

## 同步原则

- 分批, 不一次性巨型提交
- 每批可人工审查和可回滚
- 按主题/时间窗口/来源拆分
- 出站前重新做隐私+许可+冲突检查
- 远端权威版本先于本地

## 分批策略

### 按主题拆分
```
batch: finance-daily-2026Q2 → 金融日报项 2026 Q2
batch: brain-audit-202606    → 第二大脑审计记录
batch: codex-runs-202606     → Codex执行记录
batch: luoxue-project        → 珞雪项目
```

### 按时间窗口拆分
```
batch: 2026-W25 (6/15-6/21)
batch: 2026-W26 (6/22-6/28)
batch: 2026-W27 (6/29-7/5)
```

### 按大小限制
- 每批不超过 50MB (Git友好)
- 超过 1000 个packet自动拆分成子批次

## 恢复策略

### 本地恢复
- SQLite WAL + 定期checkpoint → 崩溃恢复
- 状态表保留完整历史 → 可重建任意时间点状态
- manifest备份 → 可验证本地文件完整性

### 同步中断恢复
- bundle_id + idempotency_key → 断点续传
- dry_run先检查 → 避免半成功状态
- FAILED_RETRYABLE → 指数退避重试(最多5次)
- FAILED_FINAL → 人工介入

### Git回滚
```
git revert <sync-commit>    # 回滚单批次
git reset --hard <pre-sync> # 紧急回滚
```

### 数据丢失恢复
- 本地候选仓 = 原始材料 + 候选包 → 可重建
- 私有Git = 权威版本 → 可从Git clone恢复
- Supabase = 投影 → 可从Git重建

## 冲突解决

```
三方比较:
  Base (上次同步的knowledge_revision)
  Local (本地最新)
  Remote (远端最新)

场景A: Local+Remote都改了同一atom → 并列保存, 标记CONFLICT, 人工裁决
场景B: Local改了, Remote没动 → 接受Local
场景C: Remote改了, Local没动 → 接受Remote (拉取最新)
场景D: 新增 → 合并
```

## 监控指标

| 指标 | 阈值 | 告警 |
|------|------|------|
| 同步延迟 | >24h since last sync | warning |
| 冲突率 | >10% of packets | review |
| 失败率 | >5% of bundles | alert |
| 磁盘增长 | >1GB/week | warning |
| Git仓库大小 | >500MB | alert (迁移大文件到对象存储) |
