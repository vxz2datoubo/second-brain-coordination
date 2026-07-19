
# 🔧 错误排查 FAQ

## 原子用途
这是一张来源页笔记，用来在以后研究 MaiBot 时快速定位官方文档页面、标题结构和主要信息点。

## 来源
- 官方页面：[https://docs.mai-mai.org/manual/faq/error-troubleshooting.md](https://docs.mai-mai.org/manual/faq/error-troubleshooting.md)
- 本地快照：[maibot-docs-llms-full-2026-06-22.md](../../sources/maibot-docs-llms-full-2026-06-22.md)

## 页面摘要
> ⚠️ **网络是 80% 问题的根源** — API 连不上、Git 拉不下来、插件装不了，大概率都是网络问题。
> 遇到任何报错，先检查能不能访问外网（`curl -I https://www.baidu.com`），不行就换网络/开代理。
> 按错误出现的频率从高到低排列，新手请优先查看 🔴 极高频章节。
> 如果不确定问题属于哪一类，先看文末的「📋 错误排查流程图」。
覆盖场景 1–6，新手部署和首次使用 MaiBot 时最容易遇到的问题。
* 启动 MaiBot 时立即崩溃
* 终端打印 TOML 解析错误，如 `Invalid TOML syntax`
* 或提示 `FileNotFoundError: config/bot_config.toml`
* 或提示 `API密钥不能为空，请在配置中设置有效的API密钥。`
* 或提示 `API基础URL不能为空`
1️⃣ 配置文件存在吗？看看 `config/` 文件夹里有没有 `bot_config.toml`
2️⃣ TOML 语法对吗？字符串加引号、数字不引号、布尔值小写
3️⃣ 用 WebUI 改过吗？WebUI 会自动验证语法，不会出错
**方法一（推荐

## 快速要点
- 启动 MaiBot 时立即崩溃
- 终端打印 TOML 解析错误，如 `Invalid TOML syntax`
- 或提示 `FileNotFoundError: config/bot_config.toml`
- 或提示 `API密钥不能为空，请在配置中设置有效的API密钥。`
- 或提示 `API基础URL不能为空`
- 启动 MaiBot，打开浏览器访问 `http://localhost:8001`
- 进入「配置管理」页面
- 按页面提示填写内容，保存即可

## 标题树
- 🔧 错误排查 FAQ
  - 🔴 极高频错误（新手必遇）
    - 场景 1：配置文件找不到或格式不对
      - 错误现象
      - 快速自查三连
      - 解决方案
- ✅ 正确示例
- ❌ 错误示例
      - 预防建议
    - 场景 2：API Key 错误/余额不足
      - 错误现象
      - 快速自查三连
      - 解决方案
- model_config.toml
- 测试 DeepSeek API
- ✅ 正确示例
- ❌ 错误示例
      - 预防建议
    - 场景 3：端口被占用
      - 错误现象
      - 快速自查三连
      - 解决方案
- config/bot_config.toml
- WebUI 端口（默认 8001）
- WebSocket 端口（默认 8000）
      - 预防建议
    - 场景 4：WebUI 页面打不开
      - 错误现象
      - 快速自查三连
      - 解决方案
      - 预防建议
    - 场景 5：MCP 配置错误
      - 错误现象
      - 快速自查三连
      - 解决方案
- config/bot_config.toml
- STDIO 类型（本地进程通信）
- HTTP 类型（远程服务）
- 测试 HTTP 类型 MCP
- 测试 STDIO 类型 MCP
- 应该能看到 MCP 服务启动日志
- ❌ 错误示例 1：stdio 模式缺少 command
- ❌ 错误示例 2：HTTP 模式缺少 url
- ❌ 错误示例 3：Bearer 认证未填 Token
      - 预防建议
    - 场景 6：机器人不回复消息
      - 错误现象
      - 快速自查三连
      - 解决方案
- 检查关键词规则
- config/bot_config.toml
- 检查是否设置了过严的频率限制
- 手动测试 API
- 应该能收到 API 返回的回复
      - 预防建议
  - 🟡 高频错误（常见）
    - 场景 7：插件加载失败
      - 错误现象
      - 快速自查三连
      - 解决方案
      - 预防建议
    - 场景 8：数据库错误
      - 错误现象
      - 快速自查三连
      - 解决方案
- 启用 WAL 模式，减少多进程锁定冲突
      - 预防建议
    - 场景 9：网络超时/连接失败
      - 错误现象
      - 快速自查三连
      - 解决方案
- 测试 API 端点是否可达
      - 预防建议
    - 场景 10：表情包系统错误
      - 错误现象
      - 快速自查三连
      - 解决方案
- VLM API Key（如使用视觉模型验证表情）
      - 预防建议
    - 场景 11：知识图谱/记忆系统错误


---
*来源: https://docs.mai-mai.org/manual/faq/error-troubleshooting.md*
