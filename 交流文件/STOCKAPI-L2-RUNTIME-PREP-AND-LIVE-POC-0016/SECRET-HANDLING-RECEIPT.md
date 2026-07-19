# SECRET-HANDLING-RECEIPT — 凭据处理回执

> 签发时间: 2026-07-17 02:55 UTC+8  
> 状态: **NO_CREDENTIALS_PRESENT** — 账号尚未取得

## 凭据状态

| 项目 | 值 |
|------|-----|
| credential_source | **NOT_PROVIDED** (用户尚未提供账号) |
| auth_success | N/A |
| credential_storage | 待配置: 本地环境变量 (不落盘) |
| account_identifier_hash | N/A |

## 凭据读取方式

采集器脚本只从环境变量读取，不硬编码密码:

```python
import os
ACCOUNT = os.environ.get("STOCKAPI_USERNAME", "")
PASSWORD = os.environ.get("STOCKAPI_PASSWORD", "")
```

## 禁止的操作

- [ ] ❌ 密码写入源码
- [ ] ❌ 密码写入日志
- [ ] ❌ 密码写入聊天/报告
- [ ] ❌ 密码发送给 ChatGPT/Codex
- [ ] ❌ 密码写入配置文件
- [ ] ❌ 密码写入环境初始化脚本
- [ ] ❌ 完整认证响应的存储

## 允许的记录

- [x] ✅ credential_source=local_secret
- [ ] ✅ auth_success=true/false (账号到手后)
- [ ] ✅ account_identifier_hash (SHA256前8位)
- [ ] ✅ server + port

## 账号到手后的配置流程

1. 用户在本地终端执行（不回显）: `set STOCKAPI_USERNAME=xxx` / `set STOCKAPI_PASSWORD=xxx`
2. WorkBuddy 只读取验证登录状态
3. 不存储密码到任何文件
4. 会话结束后自动过期（内存变量）
