# DEMO-RUNTIME-RISK-REVIEW — Demo 运行风险审查

> 审查对象: `test_demo.py` (参考骨架) + `test_demo (2)(1).py` (反例)  
> 状态: 离线审查 — 未安装未知程序, 未连接任何服务器

## 一、两个 Demo 的差异概览

| 维度 | test_demo.py (dy1) | test_demo (2)(1).py (gzqt1) |
|------|:---:|:---:|
| 服务器 | dy1.l2api.cn | gzqt1.l2api.cn |
| 端口 | 18100/18103/18105 | 28100/28103/28105 |
| Queue端口(18104) | ❌ 缺失 | ❌ 缺失 |
| 粘包处理 | ✅ 字符缓冲区 `<...> ` 正确切包 | ❌ 正则 `PKG_PATTERN.finditer` 嵌套, 逻辑错误 |
| gzip解压 | ✅ 实际调用 `decompress_base64_to_bytes` | ⚠️ 函数存在但被注释掉了 |
| 数据落盘 | ✅ 按symbol分组写JSON | ❌ 仅print到控制台 |
| 密码安全 | ❌ 源码plaintext | ❌ 源码plaintext |
| 登录确认 | ❌ `time.sleep(0.1)` 盲等待 | ❌ 盲收一次回复 |
| 超时重连 | ❌ 固定5秒快速重连 | ❌ 固定5秒快速重连 |
| KICK处理 | ⚠️ 识别但未停止重连 | ❌ 未处理 |
| 队列 | ✅ Queue + threading | ✅ Queue + threading |
| graceful shutdown | ✅ signal_handler | ✅ signal_handler |
| 带宽控制 | 65KB buffer | 4KB buffer (接收效率低) |
| 控制消息区分 | ✅ 区分HeartBeat/欢迎/DL/DY2/KICK | ❌ 简单的payload跳过 |

## 二、必须修正的运行风险 (按GPT要求)

### P0 (不修不能运行)

1. **密码明文在源码** — 两 Demo 均直接写 `ACCOUNT="" PASSWORD=""`。必须改为环境变量读取。
2. **无登录确认** — test_demo.py 用 `time.sleep(0.1)` 盲等, test_demo (2)(1).py 盲收一次。必须改为解析 `<DL,...>` 响应成功后再订阅。
3. **缺失 Queue 端口 18104** — 两 Demo 均未连接 18104 委托队列端口。这是本 PoC 的核心能力验证目标，必须加入。
4. **test_demo (2)(1).py 的嵌套解析逻辑错误** — `PKG_PATTERN.finditer` 嵌套导致内层 finditer 在外层匹配后再次解析，且 gzip 解压被注释。必须以 test_demo.py 的字符缓冲区模型为参考重写。

### P1 (运行会出问题)

5. **固定 5 秒无限重连** — 商家明确警告频繁断连可能拉黑 IP。必须改为指数退避 + jitter + 每小时最大重连次数。
6. **KICK 后继续重连** — test_demo.py 识别 KICK 但主循环继续重连。必须 KICK 后立即停止。
7. **无有界队列** — 生产环境必须有 `maxsize` 和 `dropped_count`。
8. **无 frame 级落盘** — 两个 Demo 都解析后再存，丢失原始 frame。必须 `raw_frame first → parse later`。

### P2 (生产就绪)

9. **无 HTTP 回补接口** — 周一 PoC 需要验证 HTTP GetData 补缺。
10. **无 monotonic clock** — 需要 `time.monotonic_ns()` 做本地时序。
11. **无 local_sequence** — 需要自增序列号。
12. **无 connection_id/reconnect_count** — 无法区分重连边界。

## 三、可保留的部分

test_demo.py 的以下设计可直接复用：
- ✅ 字符缓冲区 `<...>` 切包（正确处理 TCP 粘包/半包）
- ✅ 四端口并行线程模型
- ✅ Queue + 处理线程分离（IO/解析解耦）
- ✅ parse_market_record 的十档+聚合字段覆盖（66字段）
- ✅ parse_order_record 的 13 字段（含 order_no/channel_no）
- ✅ parse_tran_record 的 14 字段（含 trade_no/ask_order_seq/bid_order_seq）
- ✅ signal_handler 优雅退出
- ✅ daemon 线程

## 四、严禁直接运行原 Demo

除非至少完成 P0 三项修正：密码环境变量、登录确认、Queue 端口。运行顺序必须是：
```
TCP connect → 等欢迎 → 发登录 → 等登录成功 → 发订阅 → 查订阅状态 → 进入streaming
```

## 五、d1 vs gzqt 服务器

- `dy1.l2api.cn` — 北京接入点 (端口族 181xx)
- `gzqt1.l2api.cn` — 广州接入点 (端口族 281xx)
- 两 Demo 使用的是不同接入点的不同端口族，**先通过服务器发现获取官方列表再选**
- 不硬编码服务器地址
