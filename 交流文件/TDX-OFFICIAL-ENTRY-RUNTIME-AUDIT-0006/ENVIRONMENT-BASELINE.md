# ENVIRONMENT-BASELINE — TDX-OFFICIAL-ENTRY-RUNTIME-AUDIT-0006

## 环境快照 (2026-07-16 ~10:42)
- **TdxW.exe**: PID 1628, VER 1,0,0,1, 启动 09:21:53, 存活中
- **安装目录**: F:\tongdaxin
- **tqcenter.py**: F:\tongdaxin\PYPlugins\user\tqcenter.py, SHA256=6D685E0ED802B63341D2CA07183CE84B121D950BB47C09048CB585DC74219EB4, **v1.0.4 (2026-03-06)**
- **TPythClient.dll**: F:\tongdaxin\PYPlugins\TPythClient.dll, SHA256=5772EF0C5D48C33B1BD14C9F6734135441C6AD767D86773031274D229FAF2170, 2,411,416 bytes, 2026-03-23
- **Level-2 权限**: 用户已开通沪深 Level-2 (USER_STATED_YES)
- **TQ 客户端运行中**: 是 (TdxW有 PYPlugins/py_strategy.cfg, TQ插件在场)

## 端口 17709 (HTTP 服务)
- **状态**: NOT_LISTENING (Test-NetConnection TCP connect 失败)
- **含义**: TDX 客户端 HTTP JSON-RPC 服务未启动。TQ-Local Skill 依赖此端口。
- **结论**: HTTP 路线在当前会话不可用。无法测试 get_market_snapshot/get_pricevol/formula_get_all 等 HTTP 调用。

## 官方 Skill 包
| 包 | 版本 | ZIP SHA256 | 来源 |
|---|---|---|---|
| 通达信TQ-Python | 1.0.12 | e2f5672f... | tdx.com.cn/products/autoup/skills/tdx-quant.zip |
| 通达信TQ-Local | 1.0.12 | ba9de77b... | tdx.com.cn/products/autoup/skills/tdx-tq-local.zip |

## 版本错位
- 本地 tqcenter.py: **v1.0.4** (2026-03-06)
- 官方 Skill 包: **v1.0.12** (TQ-Local/Python 均此版本)
- **落后约 8 个 minor 版本**(1.0.5-1.0.12)
- 官方 v1.0.12 新增方法: get_pricevol, get_more_info(含 L2TicNum/BCancel/SCancel/OpenZTBuy 等字段), exec_to_tdx, get_match_stkinfo, get_relation, get_kzz_info, download_file 等
- 任务名点的 formula_get_all / formula_get_info: **在官方 v1.0.12 SKILL.md 中未见**
- **本地 v1.0.4 缺失 v1.0.12 新增的大量接口和 L2 聚合字段**
