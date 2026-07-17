# VERSION-MISMATCH-ANALYSIS — 版本错位分析

## 版本对比
| 组件 | 版本 | 日期 | 来源 |
|---|---|---|---|
| tqcenter.py (本地) | **1.0.4** | 2026-03-06 | F:\tongdaxin\PYPlugins\user\tqcenter.py |
| TPythClient.dll (本地) | 未标版本 | 2026-03-23 | F:\tongdaxin\PYPlugins\TPythClient.dll |
| TQ-Local SKILL.md | **1.0.12** | 未知 | tdx.com.cn 官方下载 |
| TQ-Python SKILL.md | **1.0.12** | 未知 | tdx.com.cn 官方下载 |

## 本地 v1.0.4 缺失的方法 (v1.0.12 新增)
- `get_pricevol` — 价量分布
- `get_more_info` — 大量 L2 聚合字段(见 HTTP-CAPABILITY-MATRIX)
- `get_match_stkinfo` — 模糊查找
- `get_relation` — 关联品种
- `get_kzz_info` — 可转债信息
- `get_gb_info` / `get_gb_info_by_date` — 股本
- `download_file` — 下载(股东/ETF/舆情/龙虎榜)
- `exec_to_tdx` — URL命令(导航/指标)
- `create_sector` / `delete_sector` / `rename_sector` / `clear_sector` — 板块管理
- `send_message` / `send_file` / `send_warn` / `send_bt_data` / `send_user_block` — 通信

## 本地 v1.0.4 缺失的 L2 聚合字段 (get_more_info 新增)
- L2TicNum (L2逐笔成交数), L2OrderNum (L2逐笔委托数)
- BCancel (总撤买量), SCancel (总撤卖量)
- TotalBVol (总买量), TotalSVol (总卖量)
- Zjl (主买净额), Zjl_HB (主力净流入)
- OpenZTBuy (竞价涨停买入额), OpenAmo (开盘额)
- 其他 ~50+ 基本面/财务/事件字段

## 两种对齐方式
### A. 更新客户端 (推荐但本轮不执行)
更新 TPythClient.dll + tqcenter.py 到最新版本 → 本地 v1.0.4→v1.0.12 → 所有新接口可用。可在通达信【TQ策略】→【检查更新】操作（需重启客户端）。

### B. 启用 HTTP 服务
如果客户端支持从菜单开启 HTTP 17709 → TQ-Local Skill 可直接绕过本地 tqcenter.py 版本限制(走主程序内嵌 HTTP 服务, 可能用新版本内部实现)。

## 建议(仅写入报告, 本轮不执行)
1. **检查更新**: 在 TdxW【TQ策略】菜单检查 tqcenter/TPythClient 更新
2. **启用 HTTP**: 在 TdxW 查找开启 HTTP 服务(端口 17709)的选项
3. **更新后重跑审计**: 更新到 v1.0.12 后重新执行 HTTP 17709/TQ-Local 常规测试
4. **不用替换文件**: 不要手动替换 .py/.dll，走官方更新通道
