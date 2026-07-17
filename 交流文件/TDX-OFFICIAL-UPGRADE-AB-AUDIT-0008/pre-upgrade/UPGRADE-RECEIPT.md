# UPGRADE-RECEIPT — TDX-OFFICIAL-UPGRADE-AB-AUDIT-0008

> 生成: 2026-07-16 11:13 | 状态: **AWAITING_15:00_CLOSE**

## 执行计划 (用户确认 B — v2 精密版)

| 步骤 | 时间 | 操作 | 执行者 | 状态 |
|---|---|---|---|---|
| 1 | 现在–15:05 | 冻结一切，不修改 | WorkBuddy | ✅ FROZEN |
| A | 15:05 | 确认采集器关闭 + 刷新落盘 | WorkBuddy | ⬜ |
| B | 15:05 | 复算 tqcenter.py + DLL SHA256 | WorkBuddy | ⬜ |
| C | 15:05 | 比对 PRE-UPGRADE-HASHES.csv | WorkBuddy | ⬜ |
| D | 15:05 | 保存最后端口17709/PID/方法状态 | WorkBuddy | ⬜ |
| E | 15:05+ | **提示波仔点击「TQ策略→检查更新」** | **波仔** | ⬜ |
| F | 更新后 | 验证 L2权限+十档UI+TdxW稳定 | 波仔+WorkBuddy | ⬜ |
| G | 验证后 | 确认 SHA256 变化或官方无更新提示 | WorkBuddy | ⬜ |
| H | 确认后 | 执行 `_post_upgrade_test.py` | WorkBuddy | ⬜

## 脚本安全规则
- 原始返回必须完整保存，不得只保留汇总结论
- 方法存在、文档声明、累计计数 ≠ Tick/十档/逐笔验证成功
- 只有独立的时间+价格+数量记录 → TICK_RUNTIME_VERIFIED
- 交易函数禁止清单全程生效

## 升级前基线 (已封存)
- 证据副本: 0008/pre-upgrade/evidence/ (SHA256 匹配)
- 方法清单: 30个方法，5个缺失
- 运行时基线: 0007 probe_v2 (86字段 get_more_info, tick rejected)
- 端口 17709: NOT_LISTENING

## 停止条件
- 来源非官方 → 立即停止
- 要求覆盖 DLL → 停止
- L2 异常 → 停止
- 需要重启但证据未封存 → 停止
- 弹出账户/交易请求 → 停止

## 升级后测试脚本
已就绪: `_post_upgrade_test.py` (P0+P1+P2 全覆盖)
