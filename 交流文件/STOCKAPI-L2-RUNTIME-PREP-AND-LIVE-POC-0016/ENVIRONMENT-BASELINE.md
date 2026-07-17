# ENVIRONMENT-BASELINE — 运行环境基线

> 采集时间: 2026-07-17 02:55 UTC+8  
> 状态: 离线环境准备 — 未安装任何新程序

## 系统

| 指标 | 值 |
|------|-----|
| OS | Windows (x64) |
| Python | 3.13.14 (managed, C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe) |
| Timezone | China Standard Time (UTC+8) |
| Time sync | 2026-07-17 02:55:16 +08:00 |
| Disk (F:) | Free: 4.65 TB / Used: 19.3 TB |

## 端口可用性

所有 StockAPI 相关端口均未被占用：

| 端口 | 用途 | 状态 |
|------|------|:---:|
| 18100 | Market (dy1) | FREE |
| 18103 | Order (dy1) | FREE |
| 18104 | Queue (dy1) | FREE |
| 18105 | Tran (dy1) | FREE |
| 28100 | Market (gzqt1) | FREE |
| 28103 | Order (gzqt1) | FREE |
| 28105 | Tran (gzqt1) | FREE |

## 出站网络

- `dy1.l2api.cn` — 北京接入点
- `gzqt1.l2api.cn` — 广州接入点
- 出站 TCP 连接无需额外配置（Windows 默认允许出站）

## 入站规则

- 不开放任何入站公网端口
- 本机 localhost 仅用于进程间通信（不暴露到局域网）

## Python 依赖

当前未安装任何 StockAPI 相关依赖。PoC 基于纯标准库 socket/threading:
- `socket` (stdlib)
- `threading` (stdlib)
- `queue` (stdlib)
- `json` (stdlib)
- `gzip` (stdlib)
- `base64` (stdlib)
- `re` (stdlib)
- `signal` (stdlib)

如启用 HTTP 回补: 需要 `requests` 库。

## 周一启动前检查项

- [ ] 北京/广州接入点网络可达性 (`nc -zv dy1.l2api.cn 18100`)
- [ ] 账号到手且已验证
- [ ] 环境变量 `STOCKAPI_USERNAME` / `STOCKAPI_PASSWORD` 已配置
- [ ] 服务器发现接口已调用, 选定最优接入点
- [ ] Queue 端口 18104 可达
- [ ] 磁盘空间 ≥ 10GB (全天四端口原始帧估计)
- [ ] 时间已同步 (误差 ≤ 1秒)
- [ ] 采集器脚本已 Review (P0修正完成)
- [ ] 防火墙出站确认
- [ ] 日志轮转策略已就位
