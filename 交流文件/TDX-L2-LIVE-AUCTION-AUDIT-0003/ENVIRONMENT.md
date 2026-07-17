# ENVIRONMENT — TDX-L2-LIVE-AUCTION-AUDIT-0003

> 采集日期: 2026-07-16 | 审计窗口: 09:24:15 – 09:39:09 (北京时间) | 任务状态: 采集中

## 一、客户端环境
| 项目 | 值 | 来源 |
|---|---|---|
| 北京时间(采集起点) | 2026-07-16 09:24:15 | PowerShell Get-Date |
| 当前北京时间 | 2026-07-16 09:39:09 | 系统时钟 |
| 通达信主进程 | TdxW.exe | PID=1628 |
| 主进程版本 | 1,0,0,1 (ProductVersion) | Get-Item.VersionInfo |
| 主进程启动 | 2026-07-16 09:21:53 | Process.StartTime |
| CEF子进程 | tdxcef.exe ×6 | PID 1916/5292/5916/10328/15268/16164, VER 81.3.10+chromium-81.0.4044.138 |
| 安装目录 | F:\tongdaxin | 实测 |
| 数据目录 | vipdoc/{bj,cw,ds,ot,sh,sz}, T0002, PYPlugins | 实测 |
| TdxQuant插件 | tqcenter.py 存在 (sys/ + user/), v1.0.4 (2026-03-06), 桥接 TPythClient.dll | 只读读取 |

## 二、Level-2 生效状态
| 能力 | 状态 | 证据 |
|---|---|---|
| L2 已开通(沪深) | UI_VERIFIED_BY_USER | 用户陈述已开通沪深Level-2 |
| 十档盘口(UI) | UI_VERIFIED_BY_USER | 用户陈述客户端显示十档 (未截图) |
| 逐笔成交(UI) | UI_VERIFIED_BY_USER | 用户陈述客户端显示逐笔成交 (未截图) |
| 逐笔委托(UI) | UI_VERIFIED_BY_USER | 用户陈述 (未截图) |
| 委托队列(UI) | UI_VERIFIED_BY_USER | 用户陈述 (未截图) |
| 集合竞价虚拟参考价(UI) | UI_VERIFIED_BY_USER | 用户陈述客户端显示 (未截图) |
| 虚拟匹配量/未匹配量(UI) | UI_VERIFIED_BY_USER | 用户陈述 (未截图) |
| 总撤买/总撤卖/L2资金(UI) | UI_VERIFIED_BY_USER | 用户陈述 (未截图) |

> ⚠️ **UI 能力仅标记 UI_VERIFIED，不能直接推断 Python 接口可读取。** 见 CAPABILITY-MATRIX。
> 截图未采集: 桌面截图会干扰正在运行的竞价客户端, 风险违反"保护现场"禁令。改为以 MCP 字段证据为主。

## 三、现场保护确认
全部采集均为**只读**操作, 严格遵守禁令:
- ❌ 未重启/关闭客户端 (TdxW PID 1628 全程在运行)
- ❌ 未覆盖安装/升级客户端
- ❌ 未修改通达信配置
- ❌ 未 Hook 进程 / 未注入 DLL
- ❌ 未登录或连接实盘交易 (tqcenter.order_stock/SetNewOrder 严禁调用, 未调用)
- ❌ 未输出账号/密码/Cookie/Token
- ❌ 未为安装 TdxQuant 中断竞价 (tqcenter.py 已存在, 无需安装; 运行时探针未执行以避免 DLL 干扰)
- ❌ 未修改/移动/锁定通达信文件 (find 仅只读)

## 四、采集数据源
| 数据源 | 入口 | 状态 |
|---|---|---|
| TDX MCP | mcp__tdx-connector__tdx_quotes (bspNum=10, hasProInfo=1) | MCP_VERIFIED, 连续稳定 |
| WeStock MCP | mcp__westock-mcp__data_quote | MCP_VERIFIED, 交叉验证用 |
| TdxQuant (tqcenter) | 静态枚举(tq类公开方法) | STATIC_SURFACE_VERIFIED; 运行时未执行 |
| 公式 L2 统计 | — (MCP未暴露公式求值) | FORMULA_AGGREGATE_ONLY (取自ProInfo聚合) |
| 本地文件 | find 只读 (bounded+timeout) | LOCAL_FILE_VERIFIED |

## 五、测试标的
| 标的 | 名称 | 市场 | 用途 |
|---|---|---|---|
| 300418 | 昆仑万维 | 深圳创业板 | 主观察 |
| 300058 | 蓝色光标 | 深圳创业板 | 主观察 |
| 600519 | 贵州茅台 | 上海主板 | 高价低换手 |
| 510300 | 沪深300ETF华泰柏瑞 | 上海ETF | ETF |
| 000609 | *ST中迪 | 深圳主板 | 低流动性 |
| 999999 | 上证指数 | 上海指数 | 指数 |
