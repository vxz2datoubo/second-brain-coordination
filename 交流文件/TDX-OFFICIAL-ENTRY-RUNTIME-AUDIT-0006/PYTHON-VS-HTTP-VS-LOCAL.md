# PYTHON-VS-HTTP-VS-LOCAL — 三条路线对比

## 路线定义
1. **Python tqcenter.py** (本地 v1.0.4 / F:\tongdaxin\PYPlugins\user\tqcenter.py)
2. **HTTP 17709** (官方 TQ-Local v1.0.12 SKILL 定义的 JSON-RPC)
3. **官方 TQ-Local** (Skill 包 v1.0.12, 安装到 AI 平台, 通过 HTTP 调用)

## 对比表
| 维度 | Python tqcenter v1.0.4 | HTTP 17709 (v1.0.12文档) | 官方 TQ-Local |
|---|---|---|---|
| 状态 | ✅ 可用 (仅内嵌/外部 InitConnect 失败) | ❌ 不可用 (端口未监听) | ❌ 不可用 (依赖 HTTP) |
| 初始化 | tq.initialize(__file__) 或 _auto_initialize | 无需初始化(HTTP服务已运行) | 同 HTTP |
| 方法数量 | ~25 公开方法 | ~45+ JSON-RPC 方法 | 与 HTTP 相同 |
| get_pricevol | ❌ 不存在 | ✅ 文档列出 | ✅ |
| get_more_info L2 | ❌ 不存在 | ✅ L2TicNum/BCancel/SCancel等 | ✅ |
| 五档/十档 | 五档(get_market_snapshot) | 五档(文档BspInfo[5]) | 五档 |
| Tick/逐笔 | ❌ (_fast_format_tick_data死代码) | ❌ (period列表无'tick') | ❌ |
| 委托队列 | ❌ | ❌ | ❌ |
| 集合竞价 | ❌ (仅 OpenAmo) | OpenAmo/OpenZTBuy(聚合) | AGGREGATE_ONLY |
| 公式查询 | ❌ | ❌ (未见 formula_get_all) | ❌ |
| 字段数量 | Base+Ext+ProInfo~50字段 | get_more_info ~96字段 | 同 HTTP |
| 订阅推送 | subscribe_hq存在(内嵌) | 未见subscribe类 | 未见 |
| 安全边界 | 注意 order_stock(禁止) | order_stock(禁止) | 注意交易接口(禁止) |

## 关键回答
1. **HTTP 是否绕过旧包装层限制？**: 理论上可以（HTTP直接调用TX客户端内嵌服务，绕过本地tqcenter.py版本限制），但**当前不可用**(端口未监听)。
2. **TQ-Local 是否比 HTTP 更丰富？**: TQ-Local **即** HTTP 入口(同一服务)。无差异。
3. **TQ-Local 是否只是 HTTP/tqcenter.py 的封装？**: TQ-Local Skill 是 HTTP 的 AI 平台适配层。**不是** tqcenter.py v1.0.4 的封装——它直接调用客户端内嵌 HTTP 服务(可能用主程序 DLL 而非 PYPlugins 的 TPythClient.dll)。
4. **官方 Skill 是否提供新版公式方法？**: **未见** formula_get_all/formula_get_info。
5. **是否存在版本错位？**: **是**。tqcenter.py v1.0.4 vs 官方 v1.0.12，落后约8个minor版本。
6. **TdxW 内嵌环境 vs 外部 python**: 外部 python 调用 tqcenter → InitConnect 失败；内嵌(TdxW策略管理器) → 成功(Codex已验证)。
