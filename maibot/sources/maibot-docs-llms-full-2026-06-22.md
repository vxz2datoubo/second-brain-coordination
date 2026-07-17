---
url: /manual/faq.md
---

# ❓ 常见问题

新手最容易遇到的问题，都在这里了！

## 💰 费用相关

### MaiBot 需要花钱吗？

**答**：MaiBot 本身是免费的，但 AI 模型要花钱。

**具体情况**：

* 💡 **MaiBot 软件** - 完全免费，开源的
* 💳 **AI 模型** - 要付费，比如 DeepSeek、OpenAI 等
* 📊 **大概费用** - 聊天不多一个月几块钱就够了

**省钱技巧**：

* 用便宜的模型（DeepSeek 很便宜）
* 设置回复频率限制
* 关闭不必要的功能

### 用什么 AI 模型最好？

**推荐**：新手用 DeepSeek，便宜又好用！

**对比**：
| 模型 | 价格 | 效果 | 推荐度 |
|------|------|------|--------|
| DeepSeek | ⭐ 很便宜 | ⭐⭐⭐⭐ 很好 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| 千问 | ⭐⭐ 便宜 | ⭐⭐⭐⭐ 很好 | ⭐⭐⭐⭐ 推荐 |
| GPT-4o-mini | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 很好 | ⭐⭐⭐ 可以试试 |

### QQ 号会被封吗？

**答**：有风险，但可以用小号避免。

**建议**：

* 🔒 **用小号** - 不要用主号，降低风险
* ⚠️ **注意言行** - 不要说违规内容
* 🛡️ **分散风险** - 多个小号轮换使用

## 🚀 使用问题

### 启动不了怎么办？

**常见原因和解决**：

1️⃣ **Python 版本不对**

```
# 检查版本
python --version
# 需要 3.12 以上
```

2️⃣ **配置文件缺失**

```
# 第一次启动会自动创建
# 如果没有，手动创建 config 文件夹
```

3️⃣ **端口被占用**

启动报错示例：

```
WebUI 服务器 启动失败: 端口 8001 已被占用 (host=127.0.0.1)
```

**方法一：改端口** — 编辑 `config/bot_config.toml`：

* WebUI 端口：`[webui]` → `port = 8002`
* WebSocket 端口：`[maim_message]` → `ws_server_port = 8001`（默认 8000，冲突时改为其他端口）

**方法二：关进程**：

```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8001
kill -9 <PID>
```

### 机器人不回复消息？

**检查步骤**：

1. **看日志** - 有没有报错信息？
2. **检查配置** - API Key 填对了没？
3. **测试连接** - 网络能访问模型服务吗？
4. **看权限** - QQ 群里有发言权限吗？

**常见错误**：

* ❌ API Key 错了 → 401 错误
* ❌ 网络不通 → 连接超时
* ❌ 被禁言了 → 发不出消息

### 配置文件格式错误？

**新手建议**：

* 🖥️ **用 WebUI 改配置** - 不会出错
* ✏️ **手动编辑要小心** - 符号都要对
* 💾 **改前备份** - 错了还能恢复

**格式要点**：

```toml
# 字符串要加引号
name = "我的机器人"

# 数字不要引号
port = 8001

# 布尔值小写
enabled = true
```

## 🤖 功能问题

### 可以同时服务多个群吗？

**答**：当然可以！一个 MaiBot 可以服务很多群。

**设置方法**：

* 在配置里添加多个群号
* 每个群可以不同性格
* 统一管理很方便

### 数据存在哪里？安全吗？

**答**：所有数据都存在你自己的电脑上。

**存储位置**：

* 💾 **聊天记录** - 本地数据库
* 🧠 **记忆内容** - 本地文件
* ⚙️ **配置文件** - 本地磁盘

**安全提醒**：

* 🔒 **不会上传网络** - 数据都在本地
* 🏠 **隐私保护好** - 别人看不到
* 💿 **定期备份** - 防止丢失

### MaiBot 支持手机部署吗？

**答**：理论上可以，但不推荐。

**原因**：

* 📱 **手机性能有限** - 运行可能卡顿
* 🔋 **耗电量大** - 手机发热严重
* 📶 **网络不稳定** - 容易掉线

**建议**：

* 🖥️ **用电脑** - 台式机、笔记本都行
* ☁️ **用云服务器** - 24 小时在线
* 🏠 **树莓派** - 小型设备也可以

### 一定要用 QQ 吗？可以用别的平台吗？

**答**：目前主要支持 QQ，其他平台在开发中。

**现状**：

* ✅ **QQ** - 支持最好，功能最全
* 🚧 **微信** - 目前尚无可用适配器，欢迎社区开发
* 📋 **其他** - 可通过适配器插件接入更多平台

## 🔧 技术问题

### 回复太慢怎么办？

**优化方法**：

1. **换快模型** - DeepSeek 响应很快
2. **减少上下文** - 不要给太多历史记录
3. **检查网络** - 网络慢会影响速度
4. **关闭不必要功能** - 插件太多会拖慢速度

### NapCat 已连接，但群聊收不到消息？

**优先检查 NapCat 适配器的群聊名单过滤。**

NapCat 适配器默认启用聊天名单过滤，群聊默认是白名单模式。群号不在 `group_list` 中时，群消息会被适配器直接丢弃。

**处理方法**：

1. 打开 `plugins/MaiBot-Napcat-Adapter/config.toml`
2. Docker 部署则打开 `./data/MaiMBot/plugins/MaiBot-Napcat-Adapter/config.toml`
3. 在 `[chat]` 中把目标群号加入 `group_list`
4. 建议临时打开 `show_dropped_chat_list_messages = true`，方便在日志里看到被过滤的消息
5. 保存后重启 MaiBot

```toml
[chat]
enable_chat_list_filter = true
show_dropped_chat_list_messages = true
group_list_type = "whitelist"
group_list = ["你的QQ群号"]
```

### 内存占用太高？

**节省内存**：

* 📉 **减少记忆容量** - 少记一些东西
* 🗑️ **清理无用数据** - 定期删除垃圾
* 🔌 **少用插件** - 插件会占内存
* 💻 **升级配置** - 加内存条最直接

### 想换 AI 模型怎么换？

**简单步骤**：

1. 打开 WebUI → 配置管理
2. 找到模型设置
3. 选择新模型
4. 保存后立即生效

## 💡 新手建议

### 第一次用要注意什么？

1. **先用小号测试** - 避免主号风险
2. **从简单配置开始** - 不要一次开太多功能
3. **多看日志** - 有问题日志会告诉你
4. **加入交流群** - 有问题可以问别人

### 怎么让机器人更聪明？

1. **教它知识** - 用记忆管理功能
2. **调人格设置** - 让性格更鲜明
3. **装有用插件** - 增加各种能力
4. **多和它聊天** - 它会越学越聪明

### 哪里能学到更多？

* 📖 **看文档** - 这个文档网站
* 💬 **加群组** - 和其他用户交流
* 🔍 **搜教程** - 网上有很多经验分享
* 🐱 **看 GitHub** - 最新的更新和讨论

## 🆘 遇到解决不了的问题？

### 获取帮助的途径：

1. **先看 FAQ** - 可能已经有答案
2. **看日志** - 错误信息很重要
3. **搜一搜** - 网上可能有人遇到过
4. **问一问** - 加群问其他用户
5. **提 Issue** - GitHub 上提交问题

### 提问时要提供的信息：

* 🖥️ **系统信息** - Windows/Linux/Mac？
* 📋 **错误日志** - 具体的报错信息
* ⚙️ **配置信息** - 相关配置内容
* 🔢 **版本信息** - MaiBot 版本号
* 🎯 **复现步骤** - 怎么操作会出错

---

---
url: /manual/faq/error-troubleshooting.md
---

# 🔧 错误排查 FAQ

> ⚠️ **网络是 80% 问题的根源** — API 连不上、Git 拉不下来、插件装不了，大概率都是网络问题。
> 遇到任何报错，先检查能不能访问外网（`curl -I https://www.baidu.com`），不行就换网络/开代理。

> 按错误出现的频率从高到低排列，新手请优先查看 🔴 极高频章节。
> 如果不确定问题属于哪一类，先看文末的「📋 错误排查流程图」。

***

## 🔴 极高频错误（新手必遇）

覆盖场景 1–6，新手部署和首次使用 MaiBot 时最容易遇到的问题。

### 场景 1：配置文件找不到或格式不对

#### 错误现象

* 启动 MaiBot 时立即崩溃
* 终端打印 TOML 解析错误，如 `Invalid TOML syntax`
* 或提示 `FileNotFoundError: config/bot_config.toml`
* 或提示 `API密钥不能为空，请在配置中设置有效的API密钥。`
* 或提示 `API基础URL不能为空`

#### 快速自查三连

1️⃣ 配置文件存在吗？看看 `config/` 文件夹里有没有 `bot_config.toml`
2️⃣ TOML 语法对吗？字符串加引号、数字不引号、布尔值小写
3️⃣ 用 WebUI 改过吗？WebUI 会自动验证语法，不会出错

#### 解决方案

**方法一（推荐）：用 WebUI 修改配置**
WebUI 会自动创建和验证配置，不需要手写 TOML，不会出错：

1. 启动 MaiBot，打开浏览器访问 `http://localhost:8001`
2. 进入「配置管理」页面
3. 按页面提示填写内容，保存即可

> 如果 MaiBot 因配置错误无法启动，可以先修好关键错误让程序跑起来，再通过 WebUI 调整配置。

**方法二：手动复制示例文件**
如果暂时用不了 WebUI，可以复制示例文件作为起点：

```bash
cp config/bot_config.example.toml config/bot_config.toml
cp config/model_config.example.toml config/model_config.toml
```

**方法三：检查 TOML 语法（手改文件时参考）**

```toml
# ✅ 正确示例
[bot]
nickname = "麦麦"           # 字符串要引号
port = 8001                 # 数字不要引号
enabled = true              # 布尔值小写

# ❌ 错误示例
[bot]
nickname = 麦麦             # 错误！没引号
port = "8001"              # 错误！数字不该引号
enabled = True             # 错误！应该小写 true
```

**方法四：在线验证**
如果手动改了文件不确定格式对不对，可以用 [TOML 在线验证器](https://toml.io/cn/) 检查。

#### 预防建议

* 📝 **用 WebUI 改配置** — WebUI 会自动验证语法，不会出错
* 💾 **修改前备份** — `cp bot_config.toml bot_config.toml.bak`
* 🔍 **小步修改** — 每次只改几行，保存后测试能否启动

***

### 场景 2：API Key 错误/余额不足

#### 错误现象

* 机器人完全无回复
* 后端日志出现 `401 Unauthorized` / `402 Payment Required` / `403 Forbidden`
* 日志提示 `API key is invalid` 或 `Insufficient balance`

#### 快速自查三连

1️⃣ API Key 填对了吗？检查 `model_config.toml` 中 `api_key` 字段
2️⃣ 账户余额够吗？登录 API 提供商后台查看余额
3️⃣ 模型名对吗？检查 `model_identifier` 是否在提供商支持列表内

#### 解决方案

**步骤 1：检查 API Key 配置**

```toml
# model_config.toml
[[api_providers]]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
api_key = "sk-your-api-key-here"    # 必填！替换为你的真实 Key
auth_type = "bearer"
```

**步骤 2：验证 Key 是否有效**

```bash
# 测试 DeepSeek API
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer sk-your-api-key-here"
```

**步骤 3：检查余额**

* 登录 DeepSeek/OpenAI 等提供商后台
* 查看账户余额是否大于 0
* 检查 API Key 是否过期或被禁用

**步骤 4：确认模型名**

```toml
# ✅ 正确示例
[[models]]
model_identifier = "deepseek-chat"   # 必须是 API 商支持的模型名
name = "deepseek-chat"
api_provider = "DeepSeek"

# ❌ 错误示例
[[models]]
model_identifier = "gpt-4"           # DeepSeek 不支持 GPT-4！
api_provider = "DeepSeek"
```

#### 预防建议

* 🔑 **Key 不要提交到 Git** — 用环境变量或本地配置文件
* 💰 **设置余额提醒** — 在 API 后台设置低余额邮件通知
* 📊 **监控用量** — 定期检查 Token 消耗情况

***

### 场景 3：端口被占用

#### 错误现象

* 启动时报 `OSError: [Errno 98] Address already in use`
* 或 `[Errno 10048]`（Windows）
* 错误日志：`端口 8001 已被占用 (host=127.0.0.1)`

#### 快速自查三连

1️⃣ 哪个进程占用了端口？打开任务管理器/活动监视器找找
2️⃣ 能关掉占用进程吗？在任务管理器里结束占用进程
3️⃣ 能改 MaiBot 端口吗？编辑配置文件换其他端口

#### 解决方案

**方法一：结束占用进程**
在任务管理器（Windows）或活动监视器（macOS）中找到占用端口的进程并结束它。如果不知道哪个进程占用了，直接重启电脑也可以释放端口。

**方法二：修改 MaiBot 端口**

```toml
# config/bot_config.toml

# WebUI 端口（默认 8001）
[webui]
port = 8002             # 改为 8002 或其他空闲端口

# WebSocket 端口（默认 8000）
[maim_message]
ws_server_port = 8001   # 改为 8001 或其他空闲端口
```

**方法三：换个端口启动**
启动时换个端口也很简单，改完配置文件重新启动 MaiBot 就行。建议用 8002、9000 这类不太常用的端口。\`

#### 预防建议

* 📝 **记录端口分配** — 避免多个服务用同一端口
* 🔄 **重启后检查** — 有时旧进程未清理，重启后需手动结束
* 🔧 **使用非标准端口** — 如 8001 改为 18001，降低冲突概率

***

### 场景 4：WebUI 页面打不开

#### 错误现象

* 浏览器访问 `http://localhost:8001` 显示「无法访问此网站」或「连接被拒绝」
* 页面白屏或加载超时
* MaiBot 已启动但 WebUI 就是打不开

#### 快速自查三连

1️⃣ MaiBot 真的启动成功了吗？看终端有没有报错
2️⃣ 浏览器输入的地址对吗？默认是 `http://localhost:8001`
3️⃣ 防火墙有没有拦？Windows 防火墙/杀毒软件可能会阻止

#### 解决方案

**步骤 1：确认 MaiBot 已启动**
看运行 MaiBot 的终端窗口，有没有看到类似这样的日志：

```
WebUI 服务器 启动成功: http://127.0.0.1:8001
```

如果没看到，说明 MaiBot 还没完全启动，先解决启动报错。

**步骤 2：检查地址和端口**

* 默认地址：`http://127.0.0.1:8001`（推荐用 127.0.0.1 而不是 localhost）
* 如果改了端口，用你改的端口访问
* 如果部署在远程服务器，把 `127.0.0.1` 换成服务器 IP

**步骤 3：检查防火墙**

* **Windows**：打开「Windows 安全中心」→「防火墙和网络保护」→「允许应用通过防火墙」，确保 Python 被允许
* **macOS**：系统设置 → 网络 → 防火墙，检查是否阻止了 Python
* **Linux**：检查 iptables 或 ufw 规则

**步骤 4：检查端口是否被占用**
如果端口被其他程序占了，WebUI 也启动不了。参考场景 3 检查端口占用。

#### 预防建议

* 🖥️ **启动后看日志** — 看到「WebUI 服务器 启动成功」再打开浏览器
* 🔧 **固定用 127.0.0.1** — 比 localhost 更稳定，避免 DNS 解析问题
* 🛡️ **提前关防火墙** — 如果确定安全，可以暂时关防火墙测试

***

### 场景 5：MCP 配置错误

#### 错误现象

* 启动时报 `MCP 服务器 {name} 使用 stdio 时必须填写 command`
* 或 `MCP 服务器 {name} 使用 streamable_http 时必须填写 url`
* 或日志提示 `MCP server xxx failed to connect`

#### 快速自查三连

1️⃣ 服务器地址对吗？检查 `mcp.servers[].url` 或 `command` 字段
2️⃣ Token/Secret 匹配吗？确认 `bearer_token` 与 MCP 服务端一致
3️⃣ MCP 服务运行了吗？确认服务端已启动并可访问

#### 解决方案

**步骤 1：检查 MCP 配置**

```toml
# config/bot_config.toml

[mcp]
enable = true

# STDIO 类型（本地进程通信）
[[mcp.servers]]
name = "local-filesystem"
enabled = true
transport = "stdio"
command = "node"                          # 必填！启动命令
args = ["/path/to/mcp-server/index.js"]   # 命令参数

# HTTP 类型（远程服务）
[[mcp.servers]]
name = "remote-search"
enabled = true
transport = "streamable_http"
url = "https://mcp-search.example.com/sse"    # 必填！HTTP 端点

[mcp.servers.authorization]
mode = "bearer"
bearer_token = "your-bearer-token-here"       # 必填！认证 Token
```

**步骤 2：验证 MCP 服务可访问**

```bash
# 测试 HTTP 类型 MCP
curl -v https://mcp-search.example.com/sse \
  -H "Authorization: Bearer your-bearer-token-here"

# 测试 STDIO 类型 MCP
node /path/to/mcp-server/index.js
# 应该能看到 MCP 服务启动日志
```

**步骤 3：检查常见错误**

```toml
# ❌ 错误示例 1：stdio 模式缺少 command
[[mcp.servers]]
transport = "stdio"
command = ""              # 错误！必须填写启动命令

# ❌ 错误示例 2：HTTP 模式缺少 url
[[mcp.servers]]
transport = "streamable_http"
url = ""                  # 错误！必须填写 HTTP 端点

# ❌ 错误示例 3：Bearer 认证未填 Token
[mcp.servers.authorization]
mode = "bearer"
bearer_token = ""         # 错误！必须填写 Token
```

#### 预防建议

* 📋 **逐项核对配置** — 参考 MCP 服务端文档确认参数
* 🔍 **先测试后上线** — 用 `curl` 测试连通性再配置到 MaiBot
* 📝 **记录 Token 变更** — Token 更新后同步更新 MaiBot 配置

***

### 场景 6：机器人不回复消息

#### 错误现象

* 消息已发送到平台（QQ 群/私聊）
* 机器人无任何响应
* 日志无报错，但就是没回复

#### 快速自查三连

1️⃣ 看后端终端输出，有没有收到消息的提示？
2️⃣ 匹配到规则了吗？检查关键词/意图规则是否覆盖该消息
3️⃣ LLM 配置对吗？确认 API Key 和模型配置正确（参考场景 2）

#### 解决方案

**步骤 1：看终端输出**
重启 MaiBot 后观察终端日志，看有没有：

* `收到消息：...`（说明消息到了 MaiBot）
* `正在调用 LLM...`（说明在请求 AI）
* `发送回复：...`（说明回复发出去了）
  如果这些都有，说明 MaiBot 本身没问题，可能是平台权限或网络问题。

**步骤 2：检查回复规则**

```toml
# 检查关键词规则
[[keyword_reaction.keyword_rules]]
keywords = ["你好", "hello"]    # 确保包含你发送的消息
reaction = "你好呀！"
enabled = true                  # 确保规则启用
```

**步骤 3：检查频率限制**

```toml
# config/bot_config.toml
[chat]
# 检查是否设置了过严的频率限制
reply_frequency_limit = 10      # 每 10 秒最多回复 1 次
```

**步骤 4：检查平台权限**

* QQ 群：机器人是否被禁言？是否有发言权限？
* 私聊：是否被拉黑？
* 适配器：NapCat 是否正常连接？

**步骤 5：测试 LLM 响应**

```bash
# 手动测试 API
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}]}'
# 应该能收到 API 返回的回复
```

#### 预防建议

* 📊 **监控日志** — 定期查看日志，发现异常及时处理
* 🧪 **测试新规则** — 添加新规则后先测试是否生效
* 📝 **记录配置变更** — 修改回复规则后记录变更内容

***

## 🟡 高频错误（常见）

覆盖场景 7–11，正常使用过程中较常遇到的问题。

### 场景 7：插件加载失败

#### 错误现象

* 启动时报 `PluginLoadError`，插件列表里对应插件灰色不可用
* 日志显示 `ImportError`、`ModuleNotFoundError` 或 `ManifestValidationError`
* 插件目录存在但没有任何插件被加载

#### 快速自查三连

1️⃣ 先试试重新安装插件，换个最新版本
2️⃣ 看看日志里提示缺少什么依赖
3️⃣ 确认 Python 版本 ≥ 3.10 且插件和 MaiBot 版本兼容

#### 解决方案

**步骤 1：换个版本试试**
重新下载插件，选一个和 MaiBot 版本兼容的版本。优先用官方插件或社区热门插件，兼容性更好。

**步骤 2：安装缺少的依赖**
看日志里有没有类似 `No module named 'xxx'` 的错误。如果有，说明插件缺少依赖，在插件目录下运行：

```bash
cd plugins/你的插件目录
uv sync
```

**步骤 3：看完整的错误日志**
启动 MaiBot 时注意看终端的完整错误信息，找到类似这样的提示：

```
No module named 'requests'
```

根据提示缺什么装什么。

#### 预防建议

* 安装插件前先看说明，确认兼容的 MaiBot 版本
* 优先用官方插件或社区热门插件
* 定期更新插件和 MaiBot 到最新版本

***

### 场景 8：数据库错误

#### 错误现象

* 运行时报 `DatabaseError` 或 `OperationalError`
* 启动时提示数据库迁移失败
* 日志显示 `database is locked` 或 `disk I/O error`

#### 快速自查三连

1️⃣ 检查是否同时启动多个 MaiBot 实例连接同一数据库
2️⃣ 查看磁盘空间是否已满（打开文件管理器看看）
3️⃣ 确认 `data/maibot.db` 文件权限是否正确（可读写）

#### 解决方案

**步骤 1：解决数据库锁定**

如果日志显示 `database is locked`，说明可能有多个 MaiBot 实例同时访问同一个数据库文件。关掉多余的 MaiBot 进程，只保留一个就行。

如果关掉后还是锁定，可以尝试把 `data/maibot.db` 文件删掉重来（注意先备份）。

**步骤 2：修复损坏的数据库**

如果怀疑数据库损坏（如突然断电后）：

1. 先备份：复制 `data/maibot.db` 到安全位置
2. 重启 MaiBot，程序会自动重建或修复数据库
3. 如果还不行，删掉 `data/maibot.db` 让程序重新创建（之前的重要数据需要从备份恢复）

**步骤 3：启用 WAL 模式（减少锁定冲突）**

```toml
[database]
# 启用 WAL 模式，减少多进程锁定冲突
journal_mode = "wal"
```

**步骤 4：清理磁盘空间**

打开 `logs/` 文件夹，删除不需要的旧日志文件。如果磁盘空间严重不足，也检查一下其他目录的大文件。

#### 预防建议

* 避免同时启动多个 MaiBot 实例连接同一数据库文件
* 定期备份 `data/maibot.db`（建议每周一次）
* 配置日志轮转，避免日志文件占满磁盘
* 使用 WAL 模式减少锁定冲突

***

### 场景 9：网络超时/连接失败

#### 错误现象

* LLM 请求长时间无响应后报 `APIConnectionError` 或 `TimeoutError`
* 日志显示 `Connection refused`、`Connection reset` 或 `Read timed out`
* 机器人完全无回复，但本地功能正常

#### 快速自查三连

1️⃣ 测试网络通不通（`curl -v https://api.deepseek.com`）
2️⃣ 换个网络试试（比如切换手机热点）
3️⃣ 确认 `timeout` 参数不是太小（建议 60-120 秒）

#### 解决方案

**步骤 1：测试网络连通性**

```bash
# 测试 API 端点是否可达
curl -v https://api.deepseek.com
```

如果能连上（返回 HTTP 200 或 401 都算连通），说明网络没问题。
如果超时或连不上，说明你的网络到 API 服务商的线路不通，换个网络试试。

**步骤 2：增大超时时间**

如果网络不太好，把超时设长一点：

```toml
[[api_providers]]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
api_key = "sk-your-api-key-here"
timeout = 120              # 单次请求超时（秒），网络差时可设到 180
max_retry = 3              # 失败重试次数
retry_interval = 8         # 重试间隔（秒）
```

**步骤 3：换一个 API 提供商试试**

如果 DeepSeek 不稳定，可以在配置中加一个备用 API：

```toml
[[api_providers]]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
api_key = "sk-key-1"

[[api_providers]]
name = "备用"
base_url = "https://api.openai.com/v1"  # 换成其他 API
api_key = "sk-your-backup-key"
```

#### 预防建议

* 设置合理的 `timeout`（60-120 秒）和 `max_retry`（2-3 次）
* 网络不稳定时换个网络试试（如切换手机热点）
* 配置多个 API 提供商做备份，避免单点故障
* 定期检查 API 服务商状态（关注官方公告）

***

### 场景 10：表情包系统错误

#### 错误现象

* 发送表情命令无反应
* 表情生成失败，日志中有 `VLMError` 或 `FilterError`
* 表情注册失败，提示数量超限

#### 快速自查三连

1️⃣ 确认 `emoji.vlm_api_key` 已配置（如使用 VLM 验证）
2️⃣ 检查 `emoji.filter` 规则是否过于严格
3️⃣ 确保 `data/emojis/` 目录可写（权限正确）

#### 解决方案

**步骤 1：检查 VLM 配置**

如果使用 VLM 进行表情验证，确保配置了 API Key：

```toml
[emoji]
# VLM API Key（如使用视觉模型验证表情）
vlm_api_key = "sk-your-vlm-key"
```

**步骤 2：调整表情过滤规则**

如果表情被过滤规则误杀：

```toml
[emoji]
content_filtration = false   # 暂时关闭过滤，排查是否为规则问题
```

**步骤 3：检查目录权限**

确保 `data/emojis/` 目录可写。如果权限不对，在文件管理器里右键设置读写权限。

**步骤 4：调整表情数量限制**

如果提示注册数量超限：

```toml
[emoji]
emoji_send_num = 25          # 单次发送候选数（1-64）
max_reg_num = 64             # 最大注册表情包数量
do_replace = true            # 满额后替换旧表情
```

#### 预防建议

* 首次使用时临时关闭 VLM 验证，排查是否为模型问题
* 谨慎开启 `content_filtration`，避免误杀正常表情
* 定期清理 `data/emojis/` 目录，删除不用的表情
* 设置合理的 `max_reg_num`，避免占用过多存储空间

***

### 场景 11：知识图谱/记忆系统错误

#### 错误现象

* 机器人回答"我不记得"或"未找到相关信息"
* 日志提示知识文件加载失败
* 记忆添加后无法检索到

#### 快速自查三连

1️⃣ 运行 `maibot knowledge rebuild` 重建知识索引
2️⃣ 检查 `data/knowledge/` 目录下文件是否完整
3️⃣ 确认 `knowledge.enabled` 为 `true`

#### 解决方案

**步骤 1：重建知识索引**

```bash
# 使用 CLI 命令重建索引
maibot knowledge rebuild

# 或在 WebUI 中点击"重建索引"按钮
```

**步骤 2：检查知识文件**

```bash
# 查看知识目录
ls -la data/knowledge/

# 确认文件格式正确（JSON 或 TXT）
# 损坏的文件会导致加载失败
```

**步骤 3：启用知识系统**

在配置文件中确认知识系统已启用：

```toml
[knowledge]
enabled = true
```

**步骤 4：限制单条知识长度**

如果知识太长超出 embedding 模型 Token 限制：

```toml
[knowledge]
# 单条知识最大长度（Token 数）
max_chunk_size = 512
# 知识块重叠大小（避免上下文断裂）
chunk_overlap = 50
```

**步骤 5：检查向量数据库**

如果索引损坏，删除 `data/vector_index/` 目录下的内容，然后重建：

```bash
maibot knowledge rebuild
```

#### 预防建议

* 添加知识时控制单条长度，避免超出 embedding 模型 Token 限制
* 定期重建知识索引，确保索引与知识文件同步
* 备份 `data/knowledge/` 和 `data/vector_index/` 目录
* 使用 WebUI 的知识管理功能，避免手动编辑知识文件

***

## 🟢 中频错误（特定场景）

覆盖场景 12–17，在特定操作或配置场景下才会遇到的问题。

### 场景 12：WebUI 登录失败 / Token 过期

#### 错误现象

* 打开 WebUI 页面后自动跳回登录页
* 输入密码登录后提示「登录失败」或「密码错误」
* API 请求返回 `401 Unauthorized` 错误
* 浏览器控制台显示 `Token expired` 或 `Invalid session`

#### 快速自查三连

1️⃣ **清除浏览器缓存** — Cookie/LocalStorage 可能已过期或损坏
2️⃣ **检查密码是否正确** — 确认大小写、特殊字符输入无误
3️⃣ **查看 WebUI 服务状态** — 确认服务正在运行且未重启过

#### 解决方案

**方法一：清除 Cookie 重新登录**

```bash
# 浏览器操作：
# 1. 按 F12 打开开发者工具
# 2. 进入 Application → Cookies
# 3. 删除所有 MaiBot 相关的 Cookie
# 4. 刷新页面重新登录
```

**方法二：重启 WebUI 服务**

```bash
# 如果修改了密码或 secret_key，需要重启服务
# Docker 部署
docker restart maibot

# 源码部署
# 先停止当前进程（Ctrl+C），再重新启动
python bot.py
```

**方法三：检查 secret\_key 配置**

```toml
# 编辑 config/bot_config.toml
[webui]
secret_key = "your-secret-key-here"  # 确保与之前保持一致
session_expire = 7                   # Session 有效期（天），默认 7 天
```

> ⚠️ **注意**：修改 `secret_key` 后所有已登录的 Session 都会失效，需要重新登录。

#### 预防建议

* **延长 Session 有效期** — 将 `session_expire` 改为 30 天
* **固定 secret\_key** — 不要频繁修改，否则每次都要重新登录
* **使用浏览器书签** — 保存登录后的页面，避免重复输入密码

***

### 场景 13：平台未配置机器人账号

#### 错误现象

* 某平台（如 QQ）的消息无法发送
* 日志提示 `No bot account configured for platform qq`
* 适配器已连接但机器人无响应
* 消息发送失败，返回 `400 Bad Request`

#### 快速自查三连

1️⃣ **检查平台配置** — 确认 `platforms.qq.bot_accounts` 已填写
2️⃣ **验证账号凭证** — 确认 Token/密码正确且未过期
3️⃣ **查看适配器日志** — 确认适配器已正常连接

#### 解决方案

**步骤一：配置机器人账号**

```toml
# 编辑 config/bot_config.toml
[platforms.qq]
enabled = true

# 添加机器人账号配置
[[platforms.qq.bot_accounts]]
uin = "123456789"              # 机器人 QQ 号
token = "your-bot-token"       # 机器人 Token（根据适配器类型填写）

# 如果使用 NapCat 适配器，还需配置：
[[platforms.qq.bot_accounts]]
uin = "123456789"
adapter = "napcat"
napcat_uin = "987654321"       # NapCat 登录的 QQ 号
```

**步骤二：检查适配器连接**

```bash
# 查看适配器日志
# Docker 部署
docker logs maibot | grep -i adapter

# 源码部署
# 观察终端输出，寻找「适配器已连接」相关日志
```

**步骤三：验证账号凭证**

* **QQ 平台** — 确认 QQ 号能正常登录 NapCat/GoCQ
* **微信平台** — 确认 Token 未过期且权限正确
* **其他平台** — 参考对应适配器的文档

#### 预防建议

* **使用小号** — 避免主号被封风险
* **定期更新凭证** — Token 过期前及时更换
* **配置备用账号** — 主账号异常时可快速切换

***

### 场景 14：正则表达式无效

#### 错误现象

* 启动或保存配置时报 `re.error: bad escape` 等错误
* 日志提示 `Invalid regex pattern` 或 `正则表达式编译失败`
* 关键词规则/消息过滤不生效
* 配置页面提示「保存失败：正则语法错误」

#### 快速自查三连

1️⃣ **检查特殊字符转义** — `\.` `\*` `\+` 等特殊字符是否加了反斜杠
2️⃣ **检查括号闭合** — `()` `[]` `{}` 是否成对出现
3️⃣ **使用在线工具测试** — 用 regex101.com 验证正则是否正确

#### 解决方案

**方法一：使用在线正则测试工具**

```text
# 访问 https://regex101.com/
# 1. 在左侧输入你的正则表达式
# 2. 在下方输入测试文本
# 3. 查看是否报错并调整
```

**方法二：转义特殊字符**

```toml
# 错误示例：未转义
ban_msgs_regex = ["\d{17}[\dXx"]  # 方括号未闭合

# 正确示例：转义并闭合
ban_msgs_regex = [
    "\\d{17}[\\dXx]",            # 身份证号（TOML 中需要双反斜杠）
    "1[3-9]\\d{9}",              # 手机号
    "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",  # 邮箱
]
```

**方法三：使用普通字符串代替正则**

```toml
# 如果不需要复杂匹配，用普通字符串更安全
ban_words = ["广告", "加微信", "兼职"]  # 简单关键词，无需正则

# 避免写复杂的正则表达式
# ban_msgs_regex = ["(今天 | 明天 | 后天).*(天气 | 气温)"]  # 容易出错
# 改用关键词匹配
ban_words = ["天气", "气温", "温度"]
```

> 💡 **提示**：TOML 文件中正则表达式需要双反斜杠 `\\` 转义，因为 `\` 本身是 TOML 的转义字符。

#### 预防建议

* **优先用关键词匹配** — 简单场景不需要正则
* **复杂正则单独测试** — 先在 regex101.com 验证再填入配置
* **添加注释说明** — 在正则旁边注释匹配的内容，方便后续维护

***

### 场景 15：关键词规则配置错误

#### 错误现象

* 消息匹配到错误的回复规则
* 规则完全不生效，机器人不回复
* 优先级冲突，高优先级规则覆盖低优先级
* 中英文标点混用导致匹配失败

#### 快速自查三连

1️⃣ **检查规则优先级** — `priority` 高的规则会覆盖低的
2️⃣ **确认规则已启用** — `enabled = true` 是否设置
3️⃣ **测试标点符号** — 全角/半角符号差异会影响匹配

#### 解决方案

**步骤一：检查关键词规则配置**

```toml
# 编辑 config/bot_config.toml
[keyword_reaction]

# 纯关键词规则
[[keyword_reaction.keyword_rules]]
keywords = ["你好", "hello", "嗨"]
regex = []
reaction = "你好呀！有什么可以帮你的吗？"
priority = 10                    # 优先级，数字越大优先级越高
enabled = true                   # 确保规则已启用

# 纯正则规则
[[keyword_reaction.regex_rules]]
keywords = []
regex = ["(早安 | 早上好 | 早 [上啊].*)"]
reaction = "早上好！今天又是美好的一天~"
priority = 20
enabled = true

# 关键词 + 正则混合规则
[[keyword_reaction.keyword_rules]]
keywords = ["天气"]
regex = ["(今天 | 明天 | 后天).*(天气 | 气温 | 温度)"]
reaction = "让我看看天气预报..."
priority = 15
enabled = true
```

**步骤二：调整优先级**

```toml
# 优先级示例：
# priority = 30 — 最高优先级（精确匹配）
# priority = 20 — 中等优先级（正则匹配）
# priority = 10 — 默认优先级（普通关键词）
# priority = 1  — 最低优先级（兜底规则）

# 确保重要规则的优先级高于通用规则
[[keyword_reaction.keyword_rules]]
keywords = ["帮助", "help"]
reaction = "我可以帮你..."
priority = 30                    # 高优先级，确保优先匹配

[[keyword_reaction.keyword_rules]]
keywords = ["吗", "呢", "吧"]     # 通用疑问词，优先级放低
reaction = "这个嘛..."
priority = 5
```

**步骤三：测试标点符号差异**

```toml
# 全角标点（中文输入法）
keywords = ["你好，", "你好，"]   # 逗号不同

# 半角标点（英文输入法）
keywords = ["hello,", "hello!"]

# 建议同时配置两种标点
keywords = ["你好，", "你好，", "hello", "hello!"]
```

#### 预防建议

* **规则命名加注释** — 在规则旁边注释用途
* **优先级分层管理** — 精确匹配 > 正则匹配 > 普通关键词 > 兜底规则
* **定期测试规则** — 在群里发送测试消息验证匹配效果
* **使用调试模式** — 打开 `DEBUG` 日志查看实际匹配链路

***

### 场景 16：Git 操作失败（WebUI）

#### 错误现象

* WebUI 中知识库同步/Git 镜像操作失败
* 日志显示 `Git clone failed` 或 `Permission denied`
* SSH Key 验证失败提示 `Host key verification failed`
* Git LFS 文件过大导致超时

#### 快速自查三连

1️⃣ **先确认网络** — 能不能访问 GitHub/Gitee？
2️⃣ **换个公开仓库试试** — 不需要登录的仓库有没有问题？
3️⃣ **仓库是不是太大了** — 大文件会导致超时

#### 解决方案

**步骤一：确认网络连通**
看看能不能打开 GitHub 或 Gitee 网站。如果打不开，说明网络有问题，先解决网络。

**步骤二：换个不需要登录的仓库试试**
如果提示权限错误（Permission denied），在 WebUI 中换个公开仓库（不需要 SSH Key 的那种）测试一下。如果公开仓库能正常同步，说明是 SSH 权限配置问题，去 GitHub/Gitee 检查 SSH Key 设置。

**步骤三：调整 Git 超时配置**
如果仓库较大，在 `config/bot_config.toml` 中把超时设长一点：

```toml
[git_mirror]
timeout = 300                    # Git 操作超时（秒），默认 300 秒
max_file_size = 100              # 单文件最大体积（MB），超过会跳过
```

#### 预防建议

* **先用公开仓库测试** — 确认能同步了再换私有仓库
* **避免大文件** — 不要在仓库里放大型二进制文件

***

### 场景 17：日志文件过大 / 磁盘空间满

#### 错误现象

* 系统运行缓慢或崩溃
* 日志轮转失败报 `No space left on device`
* 磁盘使用率 100%，无法写入新文件
* MaiBot 启动失败，提示数据库锁定或写入失败

#### 快速自查三连

1️⃣ **检查磁盘空间** — 打开文件管理器看看磁盘还剩多少空间
2️⃣ **查看日志文件大小** — 看看 `logs/` 文件夹有多大
3️⃣ **检查日志级别** — `DEBUG` 级别会产生大量日志

#### 解决方案

**步骤一：清理日志文件**
打开 `logs/` 文件夹，删除不需要的旧日志文件。一般只需要保留最近几天的日志，以前的可以直接删掉。

**步骤二：配置日志轮转**

```toml
# 编辑 config/bot_config.toml
[logging]
level = "INFO"                 # 生产环境用 INFO，调试时用 DEBUG
max_bytes = 10485760           # 单文件最大 10MB
backup_count = 5               # 保留 5 个备份文件
enable_rotation = true         # 启用日志轮转
```

**步骤三：清理其他垃圾文件**

* Docker 用户：清理未使用的镜像和容器释放空间
* 检查 `~/.cache/` 目录，可以删除里面不需要的缓存文件

**步骤四：如果还不行，换个盘**
如果当前磁盘确实空间太小，考虑把 MaiBot 的日志和数据目录移到空间更大的磁盘上。

#### 预防建议

* **生产环境用 INFO 级别** — 避免 DEBUG 日志过多
* **配置日志轮转** — 限制日志文件大小和数量
* **定期清理** — 设置 crontab 每周自动清理旧日志
* **独立磁盘挂载** — 将日志目录挂载到独立磁盘分区
* **监控磁盘空间** — 设置告警，使用率超过 80% 时通知

***

## ⚪ 低频错误（罕见）

覆盖场景 18–19，极少遇到但在特殊操作时可能出现的问题。

### 场景 18：人物/用户系统数据异常

#### 错误现象

* WebUI 中用户资料加载失败，显示空白或报错
* 人物卡信息丢失，之前设置的性格/背景没了
* 绑定账号时提示「用户已存在」或「外键约束失败」

#### 快速自查三连

1️⃣ 是不是直接改过 SQLite 数据库文件？
2️⃣ `data/persons/` 文件夹里的人物卡 JSON 格式对吗？
3️⃣ 有没有多个 MaiBot 实例同时访问同一个数据库？

#### 解决方案

**重建用户索引**

```bash
maibot person rebuild
```

**检查人物卡格式**

```bash
# 进入人物卡目录
cd data/persons/

# 验证 JSON 格式（以某个角色为例）
python -m json.tool "角色名.json" > /dev/null
```

**修复数据库（谨慎操作）**

```bash
# 备份数据库
cp data/maibot.db data/maibot.db.bak

# 使用 WebUI 管理用户，不要直接操作数据库
```

#### 预防建议

* 🖥️ **用 WebUI 管理** - 不要直接改数据库文件
* 💾 **定期备份** - `data/persons/` 和 `data/maibot.db` 很重要
* 🔒 **避免并发访问** - 不要同时启动多个 MaiBot 连同一个数据库

***

### 场景 19：适配器 WebSocket 断开重连循环

#### 错误现象

适配器日志持续刷屏：

```
[WebSocket] Connection closed, reconnecting...
[WebSocket] Reconnecting in 3s...
[WebSocket] Connection established
[WebSocket] Connection closed, reconnecting...
```

消息收发不稳定，有时能收到有时收不到。

#### 快速自查三连

1️⃣ `adapter.ws_url` 地址和端口填对了吗？
2️⃣ 网络稳不稳定？（服务器和适配器之间）
3️⃣ 服务端 WebSocket 服务正常运行吗？

#### 解决方案

**检查 WebSocket 地址**

```toml
# 打开适配器配置文件
[adapter]
ws_url = "ws://127.0.0.1:8000"  # 确保地址和端口正确
```

**调整重连间隔**

```toml
[adapter]
reconnect_interval = 5  # 增大间隔，避免频繁重连（单位：秒）
```

**检查服务端状态**
检查 MaiBot 终端输出，确认 WebSocket 服务已在正常运行（应该有类似 `WebSocket 服务启动成功` 的日志）。

**添加心跳保活（高级）**
如果网络环境较差，可以在适配器配置中启用心跳：

```toml
[adapter]
enable_heartbeat = true
heartbeat_interval = 30  # 每 30 秒发送一次心跳
```

#### 预防建议

* 🌐 **确保网络稳定** - 服务器和适配器之间网络要通畅
* 🔔 **启用心跳检测** - 长连接建议开启心跳保活
* 📊 **监控日志** - 发现频繁重连及时排查
* 🔄 **考虑用进程管理** - systemd/supervisor 可以自动重启服务

***

## ⚡ 错误代码速查表

> 按错误日志中常见的关键词快速定位到对应场景。

### HTTP 状态码速查

**HTTP 400 Bad Request** 🟧 严重 → [场景 13：平台未配置机器人账号](#场景-13平台未配置机器人账号) — 请求参数错误，消息发送失败

**HTTP 401 Unauthorized** 🟥 致命 → [场景 2：API Key 错误/余额不足](#场景-2api-key-错误余额不足) — API Key 无效或缺失

**HTTP 401 Unauthorized** 🟧 严重 → [场景 12：WebUI 登录失败 / Token 过期](#场景-12webui-登录失败-token-过期) — Session 过期或 Token 失效

**HTTP 402 Payment Required** 🟧 严重 → [场景 2：API Key 错误/余额不足](#场景-2api-key-错误余额不足) — 账户余额不足

**HTTP 403 Forbidden** 🟥 致命 → [场景 2：API Key 错误/余额不足](#场景-2api-key-错误余额不足) — API Key 权限不足

**HTTP 429 Too Many Requests** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — 请求频率过高被限流

**HTTP 500 Internal Server Error** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — API 服务端内部错误

**HTTP 502 Bad Gateway** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — 网关错误，上游服务不可达

**HTTP 503 Service Unavailable** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — 服务暂时不可用（过载/维护）

### 常见错误关键词索引

**`Address already in use`** / **`[Errno 98]`** / **`[Errno 10048]`** 🟧 严重 → [场景 3：端口被占用](#场景-3端口被占用) — 端口已被其他进程占用

**`APIConnectionError`** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — API 连接失败

**`Connection refused`** / **`无法访问此网站`** 🟥 致命 → [场景 4：WebUI 页面打不开](#场景-4webui-页面打不开) — WebUI 服务未启动或端口不可达

**`database is locked`** 🟧 严重 → [场景 8：数据库错误](#场景-8数据库错误) — 数据库被多进程锁定

**`DatabaseError`** / **`OperationalError`** 🟧 严重 → [场景 8：数据库错误](#场景-8数据库错误) — 数据库操作异常

**`FileNotFoundError`** 🟥 致命 → [场景 1：配置文件找不到或格式不对](#场景-1配置文件找不到或格式不对) — 配置文件不存在

**`FilterError`** 🟨 警告 → [场景 10：表情包系统错误](#场景-10表情包系统错误) — 表情过滤规则误杀

**`ImportError`** / **`ModuleNotFoundError`** 🟧 严重 → [场景 7：插件加载失败](#场景-7插件加载失败) — 插件依赖缺失

**`No space left on device`** 🟧 严重 → [场景 17：日志文件过大 / 磁盘空间满](#场景-17日志文件过大-磁盘空间满) — 磁盘空间不足

**`PluginLoadError`** 🟧 严重 → [场景 7：插件加载失败](#场景-7插件加载失败) — 插件加载异常

**`re.error`** / **`bad escape`** 🟨 警告 → [场景 14：正则表达式无效](#场景-14正则表达式无效) — 正则语法错误

**`TimeoutError`** 🟧 严重 → [场景 9：网络超时/连接失败](#场景-9网络超时连接失败) — 请求超时

**`Token expired`** 🟨 警告 → [场景 12：WebUI 登录失败 / Token 过期](#场景-12webui-登录失败-token-过期) — 登录 Session 已过期

**`TOML syntax error`** 🟥 致命 → [场景 1：配置文件找不到或格式不对](#场景-1配置文件找不到或格式不对) — 配置文件格式错误

**`ValueError`** 🟥 致命 → [场景 5：MCP 配置错误](#场景-5mcp-配置错误) — MCP 服务器配置参数无效

**`VLMError`** 🟨 警告 → [场景 10：表情包系统错误](#场景-10表情包系统错误) — 视觉语言模型调用失败

**知识加载失败** 🟧 严重 → [场景 11：知识图谱/记忆系统错误](#场景-11知识图谱记忆系统错误) — 知识文件损坏或格式错误

**Session 过期** 🟨 警告 → [场景 12：WebUI 登录失败 / Token 过期](#场景-12webui-登录失败-token-过期) — 浏览器 Session 已失效

***

## 🆘 获取帮助指引

### 🤔 提问前自查

在向别人求助之前，花 2 分钟做以下检查，大部分问题可以自己解决：

**`📖 1. 查阅官方文档`**
: 你的问题很可能已经在本文档的各个场景中有解答了。先搜一遍，省时省力。

**`🔍 2. 查看错误日志`**
: 日志里会写明具体的错误原因和堆栈跟踪，这是定位问题的第一线索。不知道怎么导出？往下看「如何获取日志」。

**`⚙️ 3. 检查近期改动`**
: 回想最近改过什么配置、装过什么插件、更新过什么版本。尝试回退到最后一次正常工作的状态，确认是不是哪步改错了。

**`🌐 4. 搜索已知问题`**
: 用错误关键词搜索 [GitHub Issues](https://github.com/LightStudents/MaiBot-Docs/issues) 或搜索引擎，看看是否有别人遇到过相同的问题。

### 📋 提交 Issue 的信息清单

向 GitHub 提交 Issue 时，请务必包含以下信息。缺少关键信息的问题可能会被延迟处理：

**`🖥️ 系统与环境`**
: 操作系统类型及版本、部署方式（源码/Docker）、Python 版本（源码部署时）

**`🔢 MaiBot 版本`**
: 运行 `git log --oneline -1` 查看当前 commit，或从 WebUI 底部的版本号获取

**`📄 完整错误日志`**
: 包含堆栈跟踪（traceback）的日志片段，不要只截图一小段。详见下方的「如何获取日志」

**`⚙️ 相关配置`**
: 与问题相关的配置内容（注意隐去 API Key 等敏感信息）

**`🎯 复现步骤`**
: 从启动到出现错误的具体操作步骤，越详细越好

### 🌐 社区支持渠道

**`💬 QQ 群`**
: 加入 MaiBot 用户交流群，和其他用户一起交流使用经验。群号：`[请填写群号]`

**`🐱 GitHub Issues`**
: 确认是 Bug 或功能建议，请在 [GitHub Issues](https://github.com/LightStudents/MaiBot-Docs/issues) 提交。提交前记得先搜索，避免重复

**`📖 官方文档站`**
: 最新最全的文档请访问 [MaiBot 文档站](https://maibot-docs.vercel.app/)

**`💬 GitHub Discussions`**
: 功能讨论、技术提问可访问 [GitHub Discussions](https://github.com/LightStudents/MaiBot-Docs/discussions) 参与社区讨论

### 📝 如何获取日志

根据部署方式不同，获取日志的方法也不同：

**`🐍 源码部署`**
: 启动 MaiBot 的终端输出就是最直接的日志。如果终端已关闭，查看日志文件如下：

```bash
cat logs/maibot-*.log
```

如果需要更详细的日志，在 `config/bot_config.toml` 中开启 DEBUG 级别：

```toml
[log]
log_level = "DEBUG"
```

**`🐳 Docker 部署`**
: 使用 `docker logs` 命令查看容器日志：

```bash
# 查看所有日志
docker logs maibot

# 持续跟踪日志输出
docker logs -f maibot

# 只查看最近 100 行
docker logs --tail 100 maibot
```

**`🪟 Windows 部署`**
: 日志文件默认在 `logs\` 目录下：

```powershell
type logs\maibot-*.log

# 或使用 PowerShell
Get-Content logs\maibot-*.log
```

> 💡 **提示**：获取日志后，用 ` ``` ` 代码块包起来粘贴到 Issue 中。如果日志很长，只贴最近一次启动到出错的部分即可，不要贴几千行的完整日志。

***

## 📋 错误排查流程图

> 不确定问题属于哪一类？按流程图指引找到对应章节。

```mermaid
graph TD
    A[❓ 遇到什么问题？] --> B{启动时崩溃/报错退出？}
    B -->|是| C[🔴 极高频错误]
    B -->|否| D{启动正常但功能异常？}
    D -->|是| E{哪方面功能？}
    E -->|消息不回复| F[场景 6：机器人不回复]
    E -->|表情包| G[场景 10：表情包系统]
    E -->|记忆/知识| H[场景 11：知识图谱]
    E -->|插件| I[场景 7：插件加载]
    D -->|否| J{WebUI 相关问题？}
    J -->|是| K{WebUI 打得开吗？}
    K -->|打不开| L[场景 4：WebUI 页面打不开]
    K -->|打得开但登录失败| M[🟢 中频错误]
    J -->|否| N{平台消息收发？}
    N -->|是| O{具体表现？}
    O -->|发不出消息| P[场景 13：平台账号]
    O -->|频繁断连| Q[场景 19：适配器重连]
    N -->|否| R{运行时性能/存储？}
    R -->|是| S[场景 17：磁盘满]
    R -->|否| T[⚪ 低频错误]

    click C "scenario-1"
    click F "scenario-6"
    click G "scenario-10"
    click H "scenario-11"
    click I "scenario-7"
    click L "scenario-4"
    click M "scenario-12"
    click P "scenario-13"
    click Q "scenario-19"
    click S "scenario-17"
```

---

---
url: /manual/webui.md
---

# 🖥️ WebUI 管理面板

通过浏览器就能管理你的机器人！

## 第一次使用

### 获取登录密码

第一次启动 MaiBot 时，控制台会显示一个密码（Token）：

```
WebUI Access Token: a1b2c3d4...
请使用此 Token 登录 WebUI
```

**重要**：这个密码只显示一次，记得保存好！

### 登录步骤

1. 打开浏览器，访问 `http://localhost:8001`（默认地址）
2. 输入控制台显示的密码
3. 登录成功后，就能看到管理面板了

## 能做什么？

WebUI 让你轻松管理 MaiBot：

* ⚙️ **改配置** - 不用编辑文件，点点鼠标就能改设置
* 🧠 **管记忆** - 查看、编辑、删除机器人的记忆
* 🔌 **装插件** - 安装和管理各种功能插件
* 📊 **看统计** - 查看聊天记录和使用数据

## 基本设置

在 `bot_config.toml` 里可以改 WebUI 的设置：

```toml
[webui]
enabled = true                # 是否启用 WebUI
host = "127.0.0.1"            # 绑定地址
port = 8001                   # 端口号
mode = "production"           # 运行模式：development(开发) 或 production(生产)
anti_crawler_mode = "basic"   # 防爬虫模式：false / strict / loose / basic
allowed_ips = "127.0.0.1"     # IP 白名单（逗号分隔）
```

* `host` 改成 `0.0.0.0` 可以让局域网其他设备访问
* `port` 可以改成其他数字避免冲突

## 忘记密码怎么办？

如果忘记密码了：

1. 关闭 MaiBot
2. 删除 `data/webui.json` 文件
3. 重新启动 MaiBot，会生成新密码

## 安全提醒

* 不要把密码告诉别人
* 公网部署时建议改默认端口
* 定期更换密码更安全

## 更多功能

* [配置管理](./config-management.md) - 在浏览器里改配置
* [记忆管理](./memory-management.md) - 查看和管理记忆
* [插件管理](./plugin-management.md) - 安装和管理插件
* [聊天记录](./chat-stats.md) - 查看聊天统计

---

---
url: /manual/configuration/amemorix-config.md
---

# A\_Memorix 记忆系统配置

A\_Memorix 是 MaiBot 的长期记忆系统，负责记忆的存储、向量化、检索、人物画像、记忆演化和 Web 运维。它替代了旧版 `[memory]` 配置段落，提供了更细粒度的控制。

本文详细介绍如何在 `bot_config.toml` 中配置 `[a_memorix]` 段落。

::: tip 先了解概念
如果你还不熟悉记忆系统是什么，建议先阅读 [记忆系统功能介绍](../features/memory-system.md)，了解它能做什么。
:::

## 配置结构总览

A\_Memorix 配置位于 `bot_config.toml` 的 `[a_memorix]` 段落下，包含 12 个子段落。TOML 段名区分大小写，请使用小写 `a_memorix`：

```toml
[a_memorix]

[a_memorix.integration]          # 记忆在聊天中的使用
[a_memorix.plugin]               # 记忆系统总开关
[a_memorix.storage]              # 数据存储位置
[a_memorix.embedding]            # 记忆向量化
[a_memorix.retrieval]            # 记忆检索
[a_memorix.threshold]            # 阈值过滤
[a_memorix.filter]               # 聊天过滤
[a_memorix.episode]              # Episode 生成
[a_memorix.person_profile]       # 人物画像
[a_memorix.memory]               # 记忆演化
[a_memorix.advanced]             # 高级运行时
[a_memorix.web]                  # Web 运维
```

::: info
旧资料或旧版独立配置文件中可能出现 `A_memorix` 或 `config/a_memorix.toml`。当前 MaiBot 主配置以 `config/bot_config.toml` 中的 `[a_memorix]` 为准；旧版 `config/a_memorix.toml` 仅作为兼容迁移来源。
:::

***

## 记忆集成 \[a\_memorix.integration]

控制麦麦在聊天中如何使用长期记忆。包括记忆检索工具、人物画像查询/注入、聊天摘要写回和反馈纠错。

### 基础集成

* **`enable_memory_query_tool`** — 是否允许麦麦在聊天时查询长期记忆。默认开启
* **`memory_query_default_limit`** — 每次默认从长期记忆中取回多少条结果，范围 `1-20`。默认 5
* **`enable_person_profile_query_tool`** — 是否允许麦麦查询人物画像记忆。默认开启
* **`enable_person_profile_injection`** — 是否在 Maisaka Planner 调用前自动注入当前对象相关的人物画像。默认开启
* **`person_profile_injection_max_profiles`** — 每轮自动注入的人物画像数量上限，范围 `1-5`。默认 3
* **`person_fact_writeback_enabled`** — 是否在发送回复后自动提取并写回人物事实到长期记忆。默认开启
* **`chat_summary_writeback_enabled`** — 是否在 Maisaka 聊天过程中按消息窗口自动写回聊天摘要到长期记忆。默认开启
* **`chat_summary_writeback_message_threshold`** — 自动写回聊天摘要的消息窗口阈值（高级）。默认 36
* **`chat_summary_writeback_context_length`** — 自动写回聊天摘要时，从聊天流中回看的消息条数，范围 `1-500`（高级）。默认 36

### 反馈纠错

反馈纠错默认关闭，属于高级功能。它会基于 `query_memory` 后一段时间内的用户反馈，尝试纠正旧记忆。

* **`feedback_correction_enabled`** — 是否启用反馈驱动的延迟记忆纠错任务（高级）。默认关闭
* **`feedback_correction_window_hours`** — 反馈窗口时长（小时），以 `query_memory` 执行时间为起点（高级）。默认 12.0
* **`feedback_correction_check_interval_minutes`** — 反馈纠错定时任务轮询间隔（分钟）（高级）。默认 30
* **`feedback_correction_batch_size`** — 反馈纠错每轮最大处理任务数，范围 `1-200`（高级）。默认 20
* **`feedback_correction_auto_apply_threshold`** — 自动应用纠错动作的最低置信度阈值，范围 `0-1`（高级）。默认 0.85
* **`feedback_correction_max_feedback_messages`** — 每个纠错任务最多使用的窗口内用户反馈消息数（高级）。默认 30
* **`feedback_correction_prefilter_enabled`** — 是否启用纠错前置预筛，用于减少不必要的模型调用（高级）。默认开启
* **`feedback_correction_paragraph_mark_enabled`** — 是否为受影响 paragraph 写入已纠正旧事实标记（高级）。默认开启
* **`feedback_correction_paragraph_hard_filter_enabled`** — 是否在用户侧查询中硬过滤带有 stale 标记的 paragraph（高级）。默认开启
* **`feedback_correction_profile_refresh_enabled`** — 是否在反馈纠错后将受影响人物画像加入刷新队列（高级）。默认开启
* **`feedback_correction_profile_force_refresh_on_read`** — 人物画像处于脏队列时，读取是否强制刷新而不直接复用旧快照（高级）。默认开启
* **`feedback_correction_episode_rebuild_enabled`** — 是否在反馈纠错后将受影响 source 加入 episode 重建队列（高级）。默认开启
* **`feedback_correction_episode_query_block_enabled`** — episode source 处于重建队列时，是否对用户侧查询做屏蔽（高级）。默认开启
* **`feedback_correction_reconcile_interval_minutes`** — 反馈纠错二阶段一致性后台协调任务轮询间隔（分钟）（高级）。默认 5
* **`feedback_correction_reconcile_batch_size`** — 反馈纠错二阶段一致性每轮处理 profile/episode 队列的批大小（高级）。默认 20

::: warning 反馈纠错是高级功能
反馈纠错默认关闭。启用后会产生额外的模型调用和计算开销。如果你不清楚它的作用，建议保持默认的 `false`。
:::

***

## 记忆系统 \[a\_memorix.plugin]

长期记忆系统的总开关。

* **`enabled`** — 是否启用长期记忆系统。默认关闭

::: warning 默认关闭
记忆系统默认关闭，需要手动设为 `true` 才能启用。启用前请确保已正确配置 embedding 模型。
:::

***

## 存储 \[a\_memorix.storage]

* **`data_dir`** — 数据目录，记忆数据将存储在此目录下。默认 `data/a-memorix`

***

## 记忆向量化 \[a\_memorix.embedding]

把记忆内容转换为向量时使用的基础设置。向量化是记忆检索的基础，选择合适的模型和参数直接影响检索质量。

### 基础配置

* **`model_name`** — 用于把记忆内容转换成向量的模型，`auto` 表示自动选择。默认 `auto`
* **`dimension`** — 记忆向量的维度，需要与向量化模型保持一致。默认 1024
* **`batch_size`** — 每次向量化请求处理的记忆条数。默认 32
* **`max_concurrent`** — 同时进行的向量化请求数量。默认 5
* **`enable_cache`** — 是否缓存向量化结果。默认关闭
* **`quantization_type`** — 向量压缩方式，当前仅支持 `int8`（SQ8）。默认 `int8`

### Embedding 回退 \[a\_memorix.embedding.fallback]

当主力 embedding 服务不可用时的降级策略。

* **`enabled`** — 是否启用回退机制。默认开启
* **`probe_interval_seconds`** — 探测间隔秒数，定期检测主力服务是否恢复。默认 180
* **`allow_metadata_only_write`** — 是否允许仅写入元数据（回退期间跳过向量化）。默认开启

### 段落向量回填 \[a\_memorix.embedding.paragraph\_vector\_backfill]

处理缺少向量的段落，异步补全向量数据。

* **`enabled`** — 是否启用回填任务。默认开启
* **`interval_seconds`** — 回填轮询间隔（秒）。默认 60
* **`batch_size`** — 单批回填数量。默认 64
* **`max_retry`** — 最大重试次数。默认 5

***

## 检索 \[a\_memorix.retrieval]

控制记忆检索的行为，包括 Top-K 参数、PPR 图计算和稀疏检索。

### 基础检索配置

* **`top_k_paragraphs`** — 段落候选数。默认 20
* **`top_k_relations`** — 关系候选数。默认 10
* **`top_k_final`** — 最终返回条数。默认 10
* **`alpha`** — 关系融合权重，范围 `0.0-1.0`。默认 0.5
* **`enable_ppr`** — 是否启用 PPR（Personalized PageRank）图计算。默认开启
* **`ppr_alpha`** — PPR alpha 参数，范围 `0.0-1.0`。默认 0.85
* **`ppr_timeout_seconds`** — PPR 超时秒数。默认 1.5
* **`ppr_concurrency_limit`** — PPR 并发限制。默认 4
* **`enable_parallel`** — 是否启用并行检索。默认开启

### 稀疏检索 \[a\_memorix.retrieval.sparse]

基于全文检索（FTS5）的稀疏检索配置，用于补充向量检索。

* **`enabled`** — 是否启用稀疏检索。默认开启
* **`backend`** — 稀疏检索后端。默认 `fts5`
* **`mode`** — 稀疏检索模式：`auto` 自动选择、`fallback_only` 仅在向量检索失败时回退、`hybrid` 混合模式。默认 `auto`
* **`tokenizer_mode`** — 分词模式。可选 `jieba`、`mixed`、`char_2gram`。默认 `jieba`
* **`candidate_k`** — 段落候选数。默认 80
* **`relation_candidate_k`** — 关系候选数。默认 60

***

## 阈值过滤 \[a\_memorix.threshold]

控制检索结果的阈值过滤策略，用于筛选出高质量的记忆条目。

* **`min_threshold`** — 最小阈值，低于此值的检索结果将被过滤，范围 `0.0-1.0`。默认 0.3
* **`max_threshold`** — 最大阈值，范围 `0.0-1.0`。默认 0.95
* **`percentile`** — 动态阈值百分位，范围 `0-100`。默认 75
* **`min_results`** — 最小保留条数，即使阈值过滤后结果不足也至少保留此数量。默认 3
* **`enable_auto_adjust`** — 是否启用自动阈值调整。默认开启

***

## 聊天过滤 \[a\_memorix.filter]

控制哪些聊天流参与记忆系统的读写。

* **`enabled`** — 是否启用聊天过滤。默认开启
* **`mode`** — 过滤模式：黑名单模式排除列表中的聊天流，白名单模式仅包含列表中的聊天流。可选 `blacklist`、`whitelist`。默认 `blacklist`
* **`chats`** — 聊天流列表。默认为空

***

## Episode \[a\_memorix.episode]

Episode 是对一段对话的自动总结与分段，是记忆系统的核心数据单元之一。

* **`enabled`** — 是否启用 Episode。默认开启
* **`generation_enabled`** — 是否启用自动生成。默认开启
* **`pending_batch_size`** — 待处理批大小。默认 50
* **`pending_max_retry`** — 待处理最大重试次数。默认 3
* **`max_paragraphs_per_call`** — 单次最大段落数。默认 20
* **`max_chars_per_call`** — 单次最大字符数，范围 `100+`。默认 6000
* **`source_time_window_hours`** — 来源时间窗口小时数。默认 24.0
* **`segmentation_model`** — 分段模型选择，`auto` 表示自动选择。默认 `auto`

***

## 人物画像 \[a\_memorix.person\_profile]

人物画像为每个用户维护一份摘要档案，包含关键事实和偏好，在聊天时自动注入上下文。

* **`enabled`** — 是否启用画像。默认开启
* **`refresh_interval_minutes`** — 刷新间隔分钟数。默认 30
* **`active_window_hours`** — 活跃窗口小时数，范围 `1.0+`。默认 72.0
* **`max_refresh_per_cycle`** — 单轮最大刷新数。默认 50
* **`top_k_evidence`** — 证据条数。默认 12

***

## 记忆演化 \[a\_memorix.memory]

记忆演化控制记忆的衰减机制，使旧记忆随时间自然弱化，避免过时信息干扰。

* **`enabled`** — 是否启用记忆演化。默认开启
* **`half_life_hours`** — 半衰期小时数，记忆权重每经过此时长衰减一半。默认 24.0
* **`prune_threshold`** — 裁剪阈值，权重低于此值的记忆将被标记为待裁剪，范围 `0.0-1.0`。默认 0.1
* **`freeze_duration_hours`** — 冻结时长小时数，新写入的记忆在冻结期内不参与演化。默认 24.0

***

## 高级运行时 \[a\_memorix.advanced]

* **`enable_auto_save`** — 是否启用自动保存。默认开启
* **`auto_save_interval_minutes`** — 自动保存间隔（分钟）。默认 5
* **`debug`** — 是否启用调试模式。默认关闭

***

## Web 运维 \[a\_memorix.web]

通过 WebUI 管理记忆系统的运维配置，包含导入中心和调优中心两个子模块。

### 导入中心 \[a\_memorix.web.import]

* **`enabled`** — 是否启用导入中心。默认开启
* **`max_queue_size`** — 最大队列长度。默认 20
* **`max_files_per_task`** — 单任务最大文件数。默认 200
* **`max_file_size_mb`** — 单文件大小上限（MB）。默认 20
* **`max_paste_chars`** — 粘贴字符数上限。默认 200000
* **`default_file_concurrency`** — 默认文件并发数。默认 2
* **`default_chunk_concurrency`** — 默认分块并发数。默认 4

### 调优中心 \[A\_memorix.web.tuning]

* **`enabled`** — 是否启用调优中心。默认开启
* **`max_queue_size`** — 最大队列长度。默认 8
* **`poll_interval_ms`** — 轮询间隔（毫秒）。默认 1200
* **`default_intensity`** — 默认调优强度，可选 `quick`、`standard`、`deep`。默认 `standard`
* **`default_objective`** — 默认调优目标，可选 `precision_priority`、`balanced`、`recall_priority`。默认 `precision_priority`
* **`default_top_k_eval`** — 默认评估 Top-K。默认 20
* **`default_sample_size`** — 默认样本数。默认 24

***

## 从旧版 \[memory] 迁移

A\_Memorix 替代了旧版 `[memory]` 配置段落。如果你之前使用过 `[memory]`，需要按照以下对应关系迁移：

### 字段映射

* **`global_memory`** → **`filter.mode`** — 全局记忆功能现由过滤模式控制。旧版 `global_memory = true` 对应新版 `filter.mode = "blacklist"` + 清空 `filter.chats`；旧版 `global_memory = false` 对应白名单模式或黑名单+加入所有聊天流
* **`global_memory_blacklist`** → **`filter.chats`** — 黑名单列表迁移到 `filter.chats`，配合 `filter.mode = "blacklist"`
* **`enable_memory_query_tool`** → **`integration.enable_memory_query_tool`** — 直接迁移
* **`memory_query_default_limit`** → **`integration.memory_query_default_limit`** — 直接迁移
* **`person_fact_writeback_enabled`** → **`integration.person_fact_writeback_enabled`** — 直接迁移
* **`chat_summary_writeback_enabled`** → **`integration.chat_summary_writeback_enabled`** — 直接迁移
* **`chat_summary_writeback_message_threshold`** → **`integration.chat_summary_writeback_message_threshold`** — 直接迁移，注意默认值从 `12` 变为 `36`
* **`chat_summary_writeback_context_length`** → **`integration.chat_summary_writeback_context_length`** — 直接迁移，注意默认值从 `50` 变为 `36`
* **`feedback_correction_*`** → **`integration.feedback_correction_*`** — 反馈纠错配置全部移入 `integration` 子段落

### 默认值变更

* **`chat_summary_writeback_message_threshold`** — 旧默认值 `12`，新默认值 `36`。消息窗口阈值增大，减少摘要写回频率
* **`chat_summary_writeback_context_length`** — 旧默认值 `50`，新默认值 `36`。回看消息数调整

### 迁移示例

旧版配置：

```toml
[memory]
global_memory = true
global_memory_blacklist = []
enable_memory_query_tool = true
memory_query_default_limit = 5
person_fact_writeback_enabled = true
chat_summary_writeback_enabled = true
chat_summary_writeback_message_threshold = 12
chat_summary_writeback_context_length = 50
feedback_correction_enabled = false
```

迁移后：

```toml
[a_memorix]

[a_memorix.plugin]
enabled = true

[a_memorix.integration]
enable_memory_query_tool = true
memory_query_default_limit = 5
person_fact_writeback_enabled = true
chat_summary_writeback_enabled = true
chat_summary_writeback_message_threshold = 12
chat_summary_writeback_context_length = 50
feedback_correction_enabled = false

[a_memorix.filter]
enabled = true
mode = "blacklist"
chats = []
```

***

## 配置示例

### 最小配置

最简单的配置，仅启用记忆系统并使用全部默认值：

```toml
[a_memorix]

[a_memorix.plugin]
enabled = true
```

其余所有子段落将使用默认值。这种方式适合快速上手，但需要确保 embedding 模型能够自动选择。

### 推荐日常配置

适合日常使用的推荐配置，在默认值基础上做少量调整：

```toml
[a_memorix]

[a_memorix.plugin]
enabled = true

[a_memorix.integration]
enable_memory_query_tool = true
memory_query_default_limit = 5
enable_person_profile_query_tool = true
enable_person_profile_injection = true
person_profile_injection_max_profiles = 3
person_fact_writeback_enabled = true
chat_summary_writeback_enabled = true

[a_memorix.embedding]
model_name = "auto"
dimension = 1024

[a_memorix.filter]
enabled = true
mode = "blacklist"
chats = []

[a_memorix.threshold]
enable_auto_adjust = true
```

### 高级配置

启用反馈纠错、调整检索参数和记忆演化策略：

```toml
[a_memorix]

[a_memorix.plugin]
enabled = true

[a_memorix.integration]
enable_memory_query_tool = true
memory_query_default_limit = 8
enable_person_profile_query_tool = true
enable_person_profile_injection = true
person_fact_writeback_enabled = true
chat_summary_writeback_enabled = true
feedback_correction_enabled = true
feedback_correction_window_hours = 12.0
feedback_correction_auto_apply_threshold = 0.9

[a_memorix.embedding]
model_name = "auto"
dimension = 1024
batch_size = 64
max_concurrent = 8

[a_memorix.embedding.fallback]
enabled = true
probe_interval_seconds = 120

[a_memorix.retrieval]
top_k_paragraphs = 30
top_k_relations = 15
top_k_final = 15
alpha = 0.6
enable_ppr = true
enable_parallel = true

[a_memorix.retrieval.sparse]
enabled = true
mode = "hybrid"
candidate_k = 100

[a_memorix.threshold]
min_threshold = 0.35
max_threshold = 0.95
percentile = 80
min_results = 5
enable_auto_adjust = true

[a_memorix.filter]
enabled = true
mode = "blacklist"
chats = []

[a_memorix.episode]
enabled = true
generation_enabled = true
source_time_window_hours = 48.0

[a_memorix.person_profile]
enabled = true
refresh_interval_minutes = 20
active_window_hours = 96.0

[a_memorix.memory]
enabled = true
half_life_hours = 48.0
prune_threshold = 0.15
freeze_duration_hours = 12.0

[a_memorix.advanced]
enable_auto_save = true
auto_save_interval_minutes = 3
debug = false
```

***

## 常见问题

### Q: 启用记忆系统后检索不到内容？

1. 确认 `[a_memorix.plugin]` 的 `enabled` 设为 `true`
2. 确认 embedding 模型配置正确，`model_name = "auto"` 会自动选择可用模型
3. 记忆需要积累一定数据量后检索效果才会提升，刚启用时可能检索不到内容
4. 检查 `[a_memorix.threshold]` 的 `min_threshold` 是否过高

### Q: 向量化失败怎么排查？

1. 检查 embedding 模型是否可用
2. 查看 `[a_memorix.embedding.fallback]` 是否启用，回退机制能在主力服务不可用时保持基本运行
3. 如果回退期间记忆无法向量化，检查 `allow_metadata_only_write` 是否为 `true`（允许仅写元数据）

### Q: 反馈纠错应该开启吗？

反馈纠错默认关闭，属于实验性高级功能。它能根据用户后续对话自动纠正旧记忆，但会增加模型调用开销。建议在记忆数据量较大且出现明显过时信息时考虑开启。

### Q: 人物画像是怎么工作的？

人物画像会为每个聊天对象维护一份关键事实摘要。`enable_person_profile_injection = true` 时，Planner 在生成回复前会自动注入相关人员画像，让麦麦"记住"对方。`refresh_interval_minutes` 控制画像的刷新频率。

### Q: 记忆演化会影响已有的记忆吗？

记忆演化是渐进式的。`half_life_hours` 控制衰减速度，`freeze_duration_hours` 确保新记忆在写入后一段时间内不会被演化修改，`prune_threshold` 设置了裁剪下限。权重低于裁剪阈值的记忆会被标记但不会立即删除。

### Q: 稀疏检索模式怎么选？

* `auto`：自动根据向量检索结果决定是否启用稀疏检索补充，推荐大多数情况使用
* `fallback_only`：仅在向量检索失败时使用，适合向量化服务稳定的场景
* `hybrid`：始终混合使用向量检索和稀疏检索，检索召回率最高但计算开销更大

***

## 下一步

* 了解记忆系统的概念和架构 -> [记忆系统功能介绍](../features/memory-system.md)
* 查看所有配置项总览 -> [Bot 配置总览](./bot-config.md)

---

---
url: /develop/plugin-dev/actions.md
---

# Action 组件（Legacy）

::: danger 已废弃
`@Action` 装饰器已废弃，SDK 内部会自动将其转换为 `@Tool` 声明。**新插件应直接使用 [`@Tool`](./tools.md)**。使用 `@Action` 时会触发 `DeprecationWarning`。
:::

## 从 @Action 迁移到 @Tool

`@Action` 和 `@Tool` 的核心区别：

* **参数类型**：`@Action` 全部为 `string` → `@Tool` 支持 `string`、`integer`、`boolean`、`array`、`object` 等 7 种类型
* **参数声明**：`action_parameters={"key": "描述"}` → `parameters=[ToolParameterInfo(...)]`
* **参数 Schema**：无 JSON Schema 生成 → 自动生成完整 JSON Schema
* **激活方式**：`activation_type` + `activation_keywords` → 始终可用（由 LLM 自行判断何时调用）
* **描述机制**：单一 `description` → `brief_description` + `detailed_description`

### 迁移示例

**旧写法（@Action）：**

```python
from maibot_sdk import MaiBotPlugin, Action

class MyPlugin(MaiBotPlugin):
    @Action(
        "search",
        description="搜索互联网获取信息",
        activation_type="always",
        action_parameters={"query": "搜索关键词"},
    )
    async def handle_search(self, query: str, **kwargs):
        results = await self._do_search(query)
        return results
```

**新写法（@Tool）：**

```python
from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

class MyPlugin(MaiBotPlugin):
    @Tool(
        "search",
        brief_description="搜索互联网获取信息",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="搜索关键词",
                required=True,
            ),
        ],
    )
    async def handle_search(self, query: str, **kwargs):
        results = await self._do_search(query)
        return {"results": results}
```

## @Action 装饰器签名（参考）

以下为 `@Action` 的完整参数签名，仅供旧插件维护参考：

```python
from maibot_sdk import Action

@Action(
    name: str,                                          # Action 名称
    description: str = "",                              # Action 描述
    activation_type: ActivationType = ActivationType.ALWAYS,  # 激活类型
    activation_keywords: list[str] | None = None,       # 激活关键词
    activation_probability: float = 1.0,                # 随机激活概率
    chat_mode: ChatMode = ChatMode.NORMAL,              # 聊天模式
    action_parameters: dict[str, Any] | None = None,    # 参数定义
    action_require: list[str] | None = None,            # 使用要求
    associated_types: list[str] | None = None,          # 关联消息类型
    parallel_action: bool = False,                      # 是否可并行执行
    action_prompt: str = "",                            # LLM 提示语
    **metadata,
)
```

### ActivationType 枚举

* **`NEVER`** — 从不激活
* **`ALWAYS`** — 始终作为候选工具
* **`RANDOM`** — 以一定概率随机启用
* **`KEYWORD`** — 当消息包含关键词时启用

### ChatMode 枚举

* **`FOCUS`** — 专注模式
* **`NORMAL`** — 普通模式
* **`PRIORITY`** — 优先模式
* **`ALL`** — 所有模式

## 内部转换机制

SDK 内部会将 `@Action` 的所有参数转换为 `@Tool` 等价的元数据：

* `action_parameters` → 转换为 Tool 的参数 Schema（所有字段类型为 `string`）
* `activation_type` / `activation_keywords` / `activation_probability` / `chat_mode` → 保存为 Tool `metadata` 中的 `legacy_action` 标记字段
* `action_require` / `associated_types` / `action_prompt` → 合并到 Tool 的 `detailed_description` 中
* `invoke_method` 固定为 `"plugin.invoke_action"`（兼容旧调用路径）

转换后，Host 侧只维护一套 Tool 抽象，不再区分 Action 和 Tool 的调用流程。

---

---
url: /manual/deployment/installation-agent.md
---

# Agent 安装指南(测试中，不保证可用)

让 AI 帮你装好 MaiBot，你只需要回答几个问题。

复制下面的提示词，发给你正在使用的 AI 助手（Claude、GPT、Gemini 等都可以），它会全程帮你完成克隆、安装、配置和启动。

::: info 提示词

> 请帮我安装 MaiBot，按照这里的指南操作：
>
> https://docs.mai-mai.org/installation-agent.md

:::

> **运行本程序即表示你同意 [MaiBot 最终用户许可协议（EULA）](../faq/EULA)。**

---

---
url: /develop/plugin-dev/api-reference.md
---

# API 参考

MaiBot 插件通过 `self.ctx`（`PluginContext`）访问 16 种能力代理。所有调用自动通过 RPC 转发到 Host 处理，SDK 会自动解包结果。

```python
self.ctx.send       # 发送消息
self.ctx.db         # 数据库操作
self.ctx.llm        # LLM 调用
self.ctx.config     # 配置读取
self.ctx.message    # 历史消息
self.ctx.chat       # 聊天流
self.ctx.person     # 用户信息
self.ctx.emoji      # 表情包管理
self.ctx.frequency  # 发言频率
self.ctx.component  # 插件管理
self.ctx.api        # 跨插件 API
self.ctx.gateway    # 消息网关
self.ctx.tool       # 工具定义
self.ctx.render     # HTML 渲染
self.ctx.knowledge  # 知识库搜索
self.ctx.maisaka    # Maisaka 上下文与主动任务
```

此外，`self.ctx.logger` 提供标准 `logging.Logger` 实例，不属于能力代理体系。详见下方的 [logger](#logger) 章节。

## send — 消息发送

```python
send = self.ctx.send
```

* `await send.text(text, stream_id)` — 发送文本消息
* `await send.image(image_data, stream_id)` — 发送图片
* `await send.emoji(emoji_data, stream_id)` — 发送表情
* `await send.command(command, stream_id)` — 发送指令消息
* `await send.forward(messages, stream_id)` — 发送转发消息
* `await send.hybrid(segments, stream_id)` — 发送图文混合消息
* `await send.custom(custom_type, data, stream_id)` — 发送自定义类型消息

```python
# 发送文本
await self.ctx.send.text("你好", stream_id)

# 发送图片（base64）
import base64
with open("image.png", "rb") as f:
    data = base64.b64encode(f.read()).decode()
await self.ctx.send.image(data, stream_id)

# 图文混合
await self.ctx.send.hybrid([
    {"type": "text", "content": "看看这张图："},
    {"type": "image", "content": image_base64},
], stream_id)
```

说明：`send.custom()` 会同时携带 `custom_type/data` 和 `message_type/content` 两套字段名，用于兼容不同版本的 Host 实现。插件侧只需要继续传 `custom_type` 与 `data`。

所有 `send.*` 方法返回 `bool`，表示是否发送成功。

## db — 数据库操作

```python
db = self.ctx.db
```

* `await db.query(model_name, query_type="get", data=None, filters=None, order_by=None, limit=None, single_result=False)` — 通用数据库操作
* `await db.save(model_name, data, key_field="id", key_value=None)` — 插入或按字段更新
* `await db.get(model_name, filters=None, limit=None, order_by=None, single_result=False)` — 按条件获取记录
* `await db.delete(model_name, filters)` — 删除数据
* `await db.count(model_name, filters)` — 计数

`db.count()` 的返回值始终是 `int`。即使 Host 侧 RPC 返回的是带 `count` 字段的对象，SDK 也会自动解包。

注意：这里的 `model_name` 必须是 Host 侧 `src.common.database.database_model` 中存在的模型类名，例如 `"ChatHistory"`、`"ActionRecord"`。旧版 `table` 参数名和 `db.get(key_field, key_value)` 形式已经废弃。

```python
# 查询
results = await self.ctx.db.query(
    model_name="ChatHistory",
    query_type="get",
    filters={"session_id": "session-123"},
    order_by=["-start_timestamp"],
    limit=10,
)

# 获取单条记录
record = await self.ctx.db.get(
    model_name="ActionRecord",
    filters={"action_id": "a-1"},
    single_result=True,
)

# 插入
await self.ctx.db.save(
    model_name="ActionRecord",
    data={"action_id": "a-1", "session_id": "session-123", "action_name": "reply"},
)

# 更新
updated = await self.ctx.db.query(
    model_name="ChatHistory",
    query_type="update",
    data={"summary": "updated"},
    filters={"session_id": "session-123"},
)

# 删除
await self.ctx.db.delete(
    model_name="ChatHistory",
    filters={"session_id": "session-123"},
)

# 计数
count = await self.ctx.db.count("ChatHistory", {"session_id": "session-123"})
```

## llm — LLM 调用

```python
llm = self.ctx.llm
```

* `await llm.generate(prompt, model="", temperature=None, max_tokens=None)` — 文本生成，`prompt` 支持字符串或消息列表
* `await llm.generate_with_tools(prompt, tools, model="", temperature=None, max_tokens=None)` — 带工具调用的生成
* `await llm.embed(text=..., texts=...)` — 生成文本嵌入向量
* `await llm.transcribe_audio(audio=..., audio_base64=...)` — 调用 Host 当前 `voice` 任务进行 ASR 语音识别，`audio` 支持音频字节或 Base64/Data URL 字符串
* `await llm.get_available_models()` — 获取可用模型列表，返回 `list[str]`

`temperature` 和 `max_tokens` 省略或传入 `None` 时，会使用模型管理页中当前模型/任务配置的值；只有显式传入具体值时才会覆盖配置。

**generate 返回值**：

```python
{
    "success": True,
    "response": "生成的文本",
    "reasoning": "推理内容（如有）",
    "model": "实际使用的模型名",
    "model_name": "实际使用的模型名"
}
```

SDK 会始终补齐 `model` 字段；若 Host 仍返回旧字段名 `model_name`，SDK 会自动兼容。

```python
# 简单文本生成
result = await self.ctx.llm.generate(
    prompt="请用一句话介绍 Python",
    temperature=0.5,
)
if result["success"]:
    text = result["response"]

# 用消息列表格式
result = await self.ctx.llm.generate(
    prompt=[
        {"role": "system", "content": "你是一个翻译助手"},
        {"role": "user", "content": "翻译：Hello World"},
    ],
)

# 带工具调用
result = await self.ctx.llm.generate_with_tools(
    prompt="今天天气怎么样",
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
            },
        },
    }],
)
tool_calls = result.get("tool_calls", [])

# 单条文本嵌入
embedding = await self.ctx.llm.embed(text="需要向量化的文本")

# 批量文本嵌入
embeddings = await self.ctx.llm.embed(
    texts=["第一段文本", "第二段文本"],
    task_name="embedding",
    max_concurrent=4,
)

# ASR 语音识别
with open("voice.mp3", "rb") as audio_file:
    asr_result = await self.ctx.llm.transcribe_audio(audio_file.read())
if asr_result["success"]:
    text = asr_result["text"]

# 获取可用模型列表
models = await self.ctx.llm.get_available_models()
```

## config — 配置读取

```python
config = self.ctx.config
```

* `await config.get(key, default=None)` — 获取配置值，`key` 支持点分割
* `await config.get_plugin(plugin_name=None)` — 获取指定插件的配置
* `await config.get_all()` — 获取插件全部配置

配置来源为插件目录下的 `config.toml`。

`config.get()`、`config.get_plugin()` 和 `config.get_all()` 都会直接返回配置值或配置字典，不需要手动从 RPC 结果中读取 `value` 字段。

```python
# 读取单个值
api_key = await self.ctx.config.get("api_key", "")
timeout = await self.ctx.config.get("network.timeout", 30)

# 读取指定插件配置
config = await self.ctx.config.get_plugin("com.example.my-plugin")

# 读取全部配置
all_config = await self.ctx.config.get_all()
```

## message — 历史消息

```python
message = self.ctx.message
```

* `await message.get_recent(chat_id, limit)` — 获取最近消息
* `await message.get_by_id(message_id, chat_id="", stream_id="")` — 按消息 ID 查询单条消息
* `await message.build_readable(messages, **kwargs)` — 将消息列表格式化为可读字符串
* `await message.get_by_time(start_time, end_time)` — 按时间范围查询（全局）
* `await message.get_by_time_in_chat(chat_id, start_time, end_time)` — 按时间范围查询指定聊天
* `await message.count_new(chat_id, since)` — 统计新消息数（`since` 为 UNIX 时间戳字符串）

`build_readable` 支持两种调用方式：

```python
# 方式 1：传入已查询的消息列表
msgs = await self.ctx.message.get_recent(chat_id, limit=20)
readable = await self.ctx.message.build_readable(msgs)

# 按消息 ID 查询
message_detail = await self.ctx.message.get_by_id(message_id, stream_id=chat_id)

# 方式 2：通过关键字参数传入 chat_id + 时间范围，由 Host 端查询
readable = await self.ctx.message.build_readable(
    messages=None,
    chat_id=chat_id,
    start_time=start_ts,
    end_time=end_ts,
)
```

可选关键字参数：`replace_bot_name`（默认 `True`）、`timestamp_mode`（默认 `"relative"`）、`truncate`（默认 `False`）。

`message.get_by_time()`、`message.get_by_time_in_chat()` 和 `message.get_recent()` 会直接返回消息列表；`message.count_new()` 直接返回数量；`message.build_readable()` 直接返回字符串。

## chat — 聊天流

```python
chat = self.ctx.chat
```

* `await chat.get_all_streams(platform="qq")` — 获取所有聊天流
* `await chat.get_group_streams(platform="qq")` — 获取所有群聊流
* `await chat.get_private_streams(platform="qq")` — 获取所有私聊流
* `await chat.get_stream_by_group_id(group_id, platform="qq")` — 按群 ID 查找聊天流
* `await chat.get_stream_by_user_id(user_id, platform="qq")` — 按用户 ID 查找私聊流
* `await chat.open_session(platform, chat_type, **kwargs)` — 打开或创建聊天流

```python
# 获取所有群聊流
streams = await self.ctx.chat.get_group_streams()

# 获取私聊聊天流
streams = await self.ctx.chat.get_private_streams()

# 按 Group ID 获取聊天流
stream = await self.ctx.chat.get_stream_by_group_id(group_id="123456")

# 按用户 ID 获取聊天流
stream = await self.ctx.chat.get_stream_by_user_id(user_id="789012")

# 打开或创建私聊聊天流
stream = await self.ctx.chat.open_session(
    platform="qq",
    chat_type="private",
    user_id="789012",
)

# 打开或创建群聊聊天流
stream = await self.ctx.chat.open_session(
    platform="qq",
    chat_type="group",
    group_id="123456",
)
```

`chat.open_session()` 会返回 `stream_id`、`session_id`、`chat_type`、`created` 以及完整 `stream` 对象。在多账号或多路由部署中，建议同时传入 `account_id` 和 `scope`，避免打开到错误的聊天流。

## maisaka — Maisaka 主动任务

```python
# 请求 Maisaka 基于指定聊天流主动处理一轮对话
result = await self.ctx.maisaka.proactive.trigger(
    stream_id=stream["stream_id"],
    intent="提醒用户今晚 20:00 有日程",
    reason="calendar_reminder",
    metadata={"source": "calendar_plugin"},
)

# 向指定聊天流追加一条插件上下文消息
await self.ctx.maisaka.context.append(
    stream_id=stream["stream_id"],
    segments=[{"type": "text", "content": "用户刚刚完成了一个插件任务"}],
    visible_text="用户刚刚完成了一个插件任务",
    source_kind="plugin:calendar",
)
```

`maisaka.proactive.trigger()` 不会直接发送固定文本，也不会伪装成用户消息。它会把 `intent` 写入 Maisaka 内部上下文并唤醒 Planner，让 Maisaka 基于人格、记忆、当前上下文和可用工具自行决定是否回复以及如何表达。目标聊天流必须已经存在。

## person — 用户信息

```python
person = self.ctx.person
```

* `await person.get_id(platform, user_id)` — 获取 person\_id
* `await person.get_value(person_id, field_name)` — 获取用户字段值
* `await person.get_id_by_name(person_name)` — 根据用户名获取 person\_id

```python
# 获取 person_id
pid = await self.ctx.person.get_id("qq", "12345")

# 获取昵称
name = await self.ctx.person.get_value(pid, "nickname") or "未知"
```

## emoji — 表情包管理

```python
emoji = self.ctx.emoji
```

* `await emoji.get_random(count)` — 随机获取表情包
* `await emoji.get_by_description(description, limit)` — 按描述搜索
* `await emoji.get_count()` — 获取总数
* `await emoji.get_info()` — 获取统计信息
* `await emoji.get_emotions()` — 获取情感标签列表
* `await emoji.get_all()` — 获取全部表情包
* `await emoji.register_emoji(emoji_base64)` — 注册新表情
* `await emoji.delete_emoji(emoji_hash, keep_desc=None)` — 删除表情；`keep_desc=True` 时保留描述缓存，仅移除文件和注册状态，`False` 时同步删除数据库记录，默认 `None` 由主程序按当前记录决定

## frequency — 发言频率

```python
frequency = self.ctx.frequency
```

* `await frequency.get_current_talk_value(chat_id)` — 获取当前 talk value
* `await frequency.set_adjust(chat_id, value)` — 设置频率调整值
* `await frequency.get_adjust(chat_id)` — 获取频率调整值

两个 `get_*` 方法都会直接返回数值；`set_adjust()` 返回布尔值表示是否设置成功。

## component — 插件与组件管理

```python
component = self.ctx.component
```

* `await component.get_all_plugins()` — 获取所有插件信息（含各插件注册的组件列表）
* `await component.get_plugin_info(plugin_name)` — 获取指定插件信息
* `await component.list_loaded_plugins()` — 列出已加载插件
* `await component.list_registered_plugins()` — 列出已注册插件
* `await component.enable_component(name, component_type, scope="global", stream_id="")` — 启用组件（`name` 支持 `plugin_id.comp_name` 全名或短名）
* `await component.disable_component(name, component_type, scope="global", stream_id="")` — 禁用组件（`name` 支持 `plugin_id.comp_name` 全名或短名）
* `await component.load_plugin(plugin_name)` — 加载插件（会校验插件是否存在并路由到对应 Supervisor）
* `await component.unload_plugin(plugin_name)` — 卸载插件
* `await component.reload_plugin(plugin_name)` — 重新加载插件

`scope` 支持 `"global"` 和 `"stream"`，`stream` 级别需传入 `stream_id`。

> **注意**：`enable_component` / `disable_component` 的 `name` 参数既可以传完整名称 `"my_plugin.my_command"`，也可以只传短名 `"my_command"`（Host 会自动按 `component_type` 匹配）。当使用短名且存在同名组件时，优先匹配指定 `type` 的组件。
>
> `load_plugin()` / `reload_plugin()` 返回 `True` 仅表示新 Runner 已完成初始化并成功切换；如果预热失败且 Host 回滚到旧 Runner，这两个接口会返回 `False`。

## api — 跨插件 API

```python
api = self.ctx.api
```

* `await api.call(api_name, version="", **kwargs)` — 调用其他插件公开的 API
* `await api.get(api_name, version="")` — 获取单个可见 API 的元信息
* `await api.list(plugin_id="")` — 列出当前插件可见的 API
* `await api.replace_dynamic_apis(apis, offline_reason="动态 API 已下线")` — 用新的动态 API 集合替换当前插件已暴露的动态 API

```python
# 调用其他插件公开的 API
result = await self.ctx.api.call("plugin_a.sum_numbers", a=1, b=2)

# 查询可见 API
apis = await self.ctx.api.list()
info = await self.ctx.api.get("plugin_a.sum_numbers", version="1")
```

说明：

* `api_name` 支持完整名 `plugin_id.api_name`，也支持唯一短名。
* `replace_dynamic_apis()` 适合 MCP 服务器、外部能力市场等"API 集合会动态变化"的场景。
* 动态 API 下线后，Host 会把它们标记为 offline，并对后续调用返回 `offline_reason`。

## gateway — 消息网关

```python
gateway = self.ctx.gateway
```

* `await gateway.route_message(gateway_name, message, route_metadata=None, external_message_id="", dedupe_key="")` — 通过指定消息网关把外部平台消息注入 Host
* `await gateway.update_state(gateway_name, ready, platform="", account_id="", scope="", metadata=None)` — 向 Host 上报消息网关运行时状态
* `await gateway.receive_external_message(message, gateway_name=..., ...)` — `route_message()` 的兼容别名
* `await gateway.update_runtime_state(gateway_name=..., connected=..., ...)` — `update_state()` 的兼容别名

```python
await self.ctx.gateway.update_state(
    gateway_name="napcat_gateway",
    ready=True,
    platform="qq",
    account_id="10001",
    scope="primary",
    metadata={"protocol": "napcat"},
)

accepted = await self.ctx.gateway.route_message(
    gateway_name="napcat_gateway",
    message={
        "message_id": "msg-1",
        "platform": "qq",
        "message_info": {...},
        "raw_message": [],
    },
    route_metadata={"self_id": "10001", "connection_id": "primary"},
    external_message_id="external-1",
    dedupe_key="dedupe-1",
)
```

详见 [消息网关](./message-gateway.md)。

## tool — 工具定义

```python
tool = self.ctx.tool
```

* `await tool.get_definitions()` — 获取 LLM 可用的工具定义列表

返回的列表中每个元素包含 `name` 和 `definition` 字段。`tool.get_definitions()` 会直接返回工具定义列表，不需要再从 RPC 结果里手动读取 `tools` 字段。

## render — HTML 渲染

```python
render = self.ctx.render
```

* `await render.html2png(html, **kwargs)` — 将 HTML 内容渲染为 PNG 图片

常用参数包括：

* `selector`：需要截图的目标选择器，默认是 `body`
* `viewport`：视口大小，例如 `{"width": 1200, "height": 800}`
* `device_scale_factor`：设备像素比
* `full_page`：是否截取整页
* `omit_background`：是否去掉默认背景
* `wait_until` / `wait_for_selector` / `wait_for_timeout_ms`：控制页面稳定时机
* `allow_network`：是否允许页面访问外部网络资源

```python
card = await self.ctx.render.html2png(
    "<body><div id='card'>Hello MaiBot</div></body>",
    selector="#card",
    viewport={"width": 960, "height": 540},
    device_scale_factor=2.0,
)

await self.ctx.send.image(card["image_base64"], stream_id)
```

`render.html2png()` 会直接返回 Host 解包后的结果字典，通常包含 `image_base64`、`mime_type`、`width` 和 `height` 等字段。

## knowledge — 知识库搜索

```python
knowledge = self.ctx.knowledge
```

* `await knowledge.search(query, limit=5)` — 搜索 LPMM 知识库

```python
content = await self.ctx.knowledge.search("Python 是什么", limit=3)
if content:
    print(content)
```

## logger — 日志

```python
# 方式一：通过 ctx.logger（名称自动为 plugin.<plugin_id>）
logger = self.ctx.logger
logger.info("插件已启动")
logger.error(f"请求失败: {err}", exc_info=True)

# 方式二：直接用 stdlib logging（同样会被自动传输）
import logging
logger = logging.getLogger(__name__)
logger.warning("配置缺失，使用默认值")
```

`self.ctx.logger` 是标准 `logging.Logger`，名称为 `plugin.<plugin_id>`。支持所有标准方法：`debug()`、`info()`、`warning()`、`error()`、`critical()`。

::: tip 日志自动转发
Runner 进程中的日志会自动通过 IPC 传输到主进程，无需额外配置。在主进程日志中可以找到插件输出的所有日志。
:::

> **注意**：旧版的 `await self.ctx.logging.info(...)` 异步 API 已移除。请改用上述标准 `logging` 写法。

---

---
url: /develop/plugin-dev/api-components.md
---

# API 组件

`@API` 装饰器用于声明插件间通信的 API 接口。其他插件可以通过 `ctx.api.call()` 调用这些 API，实现插件间的功能互操作。

## 装饰器签名

```python
from maibot_sdk import API

@API(
    name: str,                  # API 名称（必填）
    description: str = "",      # API 描述
    version: str = "1",         # API 版本
    public: bool = False,       # 是否允许其他插件调用
    **metadata,                 # 额外元数据
)
```

## 参数说明

### name

API 的唯一标识名称。同一插件内不能有重复名称的 API。其他插件通过 `插件 ID + API 名称` 来定位和调用。

### public

* **`False`**（默认） — 仅插件内部可见，其他插件无法调用
* **`True`** — 公开 API，其他插件可通过 `ctx.api.call()` 调用

### version

API 版本号，默认为 `"1"`。用于 API 版本管理，当需要不兼容更新时可以递增版本号。

## 静态 API 示例

通过 `@API` 装饰器在插件类上直接声明 API：

```python
from maibot_sdk import MaiBotPlugin, API


class RenderPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("渲染插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("渲染插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @API(
        "render_html",
        description="将 HTML 渲染为图片",
        version="1",
        public=True,
    )
    async def handle_render_html(self, html: str, **kwargs):
        # 调用渲染能力
        result = await self.ctx.render.html2png(html)
        return {"success": True, "image_path": result}

    @API(
        "get_stats",
        description="获取渲染统计信息",
        version="1",
        public=True,
    )
    async def handle_get_stats(self, **kwargs):
        return {
            "total_renders": 42,
            "avg_time_ms": 150,
        }
```

## 动态 API 注册

除了使用 `@API` 装饰器静态声明外，还可以在运行时动态注册和注销 API。动态 API 适合需要根据配置或运行时条件决定是否暴露 API 的场景。

### 动态 API 方法

* `self.register_dynamic_api(name, handler, *, description, version, public, handler_name, **metadata)` — 注册动态 API
* `self.unregister_dynamic_api(name, *, version="1")` — 注销动态 API
* `self.clear_dynamic_apis()` — 清空所有动态 API
* `await self.sync_dynamic_apis(*, offline_reason="动态 API 已下线")` — 将动态 API 同步到主程序

### 动态注册示例

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field
from typing import Any


class DynamicApiPlugin(MaiBotPlugin):
    class MyConfig(PluginConfigBase):
        enable_translate: bool = Field(default=False, description="是否启用翻译 API")

    config_model = MyConfig

    async def on_load(self) -> None:
        # 根据配置动态注册 API
        if self.config.enable_translate:
            self.register_dynamic_api(
                "translate",
                self._handle_translate,
                description="文本翻译",
                version="1",
                public=True,
                handler_name="handle_translate",
            )

            self.register_dynamic_api(
                "detect_language",
                self._handle_detect_language,
                description="语言检测",
                version="1",
                public=True,
            )

        # 同步动态 API 到主程序
        await self.sync_dynamic_apis()
        self.ctx.logger.info("动态 API 已同步")

    async def on_unload(self) -> None:
        # 清空并同步下线
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    async def _handle_translate(self, text: str, target_lang: str = "en", **kwargs) -> dict[str, Any]:
        # 翻译逻辑
        return {"translated": f"[translated {text} to {target_lang}]"}

    async def _handle_detect_language(self, text: str, **kwargs) -> dict[str, Any]:
        # 语言检测逻辑
        return {"language": "zh", "confidence": 0.95}
```

### 动态注销示例

```python
class ManagedApiPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 批量注册
        for name, handler in [("api_a", self._a), ("api_b", self._b)]:
            self.register_dynamic_api(name, handler, public=True)
        await self.sync_dynamic_apis()

    async def disable_api_b(self) -> None:
        # 注销单个 API
        self.unregister_dynamic_api("api_b")
        await self.sync_dynamic_apis(offline_reason="API B 已禁用")

    async def on_unload(self) -> None:
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    async def _a(self, **kwargs):
        return {"result": "a"}

    async def _b(self, **kwargs):
        return {"result": "b"}
```

## 调用其他插件的 API

通过 `self.ctx.api` 代理可以查询和调用其他插件公开的 API。

### ctx.api 方法

* `await self.ctx.api.call(api_name, *, version="", **kwargs)` — 调用其他插件的 API
* `await self.ctx.api.get(api_name, *, version="")` — 获取 API 信息
* `await self.ctx.api.list()` — 列出所有可用 API
* `await self.ctx.api.replace_dynamic_apis(components, offline_reason="...")` — 替换动态 API

### 调用示例

```python
from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class CallerPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 列出所有可用 API
        apis = await self.ctx.api.list()
        self.ctx.logger.info("可用 API: %s", apis)

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Tool(
        "translate_text",
        brief_description="翻译文本",
        detailed_description="参数说明：\n- text：string，必填。待翻译文本。",
        parameters=[
            ToolParameterInfo(
                name="text",
                param_type=ToolParamType.STRING,
                description="待翻译文本",
                required=True,
            ),
        ],
    )
    async def handle_translate(self, text: str, **kwargs):
        # 调用其他插件的翻译 API
        result = await self.ctx.api.call(
            "com.example.translate.translate",
            text=text,
            target_lang="en",
        )
        return result
```

### 查询 API 信息

```python
# 获取特定 API 的详细信息
api_info = await self.ctx.api.get("com.example.translate.translate")
self.ctx.logger.info("API 信息: %s", api_info)
```

## API 设计建议

### 命名规范

* 使用小写字母和下划线：`render_html`、`get_stats`
* 动词开头：`get_`、`render_`、`detect_`、`translate_`
* 避免过于通用的名称，应体现功能含义

### 版本管理

* 初始版本使用 `"1"`
* 不兼容更新时递增版本号
* 同名 API 可以同时存在多个版本

### 参数设计

* API 处理器方法接收 `**kwargs`，从中提取参数
* 必要参数应以位置参数明确声明
* 返回值应为可序列化的字典

## 静态 API 与动态 API 对比

* **声明时机**：`@API` 类定义时 → `register_dynamic_api()` 运行时（通常在 on\_load 中）
* **条件暴露**：`@API` 不支持 → `register_dynamic_api()` 可根据配置动态决定
* **注销**：`@API` 不支持 → `register_dynamic_api()` 可通过 unregister 动态注销
* **同步**：`@API` 自动 → `register_dynamic_api()` 需调用 sync\_dynamic\_apis()
* **适用场景**：`@API` 固定不变的 API → `register_dynamic_api()` 按需启用/禁用的 API

---

---
url: /manual/configuration/bot-config.md
---

# Bot 配置

`bot_config.toml` 是 MaiBot 的主配置文件，包含机器人身份、人设、聊天行为、记忆、学习、表情、WebUI、MCP、插件等全部主设置。

配置文件由 MaiBot 自动生成和升级，不建议手动新增不存在的字段。

***

# 基础

机器人身份信息，包含平台、账号、昵称等。

```toml
[bot]
platform = ""
qq_account = ""
platforms = []
nickname = "麦麦"
alias_names = []
```

**`platform`** — 平台标识。**类型**：`str`。**默认值**：`""`。填写平台名称，如 `qq`。

**`qq_account`** — QQ 账号。**类型**：`str`。**默认值**：`""`。机器人登录的 QQ 号（字符串格式），用于识别 @ 消息和自身消息。

**`platforms`** — 其他平台列表。**类型**：`list[str]`。**默认值**：`[]`。多平台部署场景填写。

**`nickname`** — 机器人昵称。**类型**：`str`。**默认值**：`"麦麦"`。聊天中显示的名称。

**`alias_names`** — 别名列表。**类型**：`list[str]`。**默认值**：`[]`。被提及时参与回复判断。

***

# 人格

控制麦麦的人设和语言风格。

```toml
[personality]
personality = "你是一个大二女大学生，现在正在上网和群友聊天。"
reply_style = "你的风格平淡简短。可以参考贴吧，知乎和微博的回复风格。不浮夸不长篇大论，不要过分修辞和复杂句。尽量回复的简短一些，平淡一些"
multiple_reply_style = [
  "你的风格平淡但不失讽刺，很简短，很白话。可以参考贴吧，微博的回复风格。",
  "用 1-2 个字进行回复",
  "用 1-2 个符号进行回复",
  "言辭凝練古雅，穿插《論語》經句卻不晦澀，以文言短句為基，輔以淺白語意，持長者溫和風範，全用繁體字表達，具先秦儒者談吐韻致。",
  "带点翻译腔，但不要太长",
]
multiple_probability = 0
```

**`personality`** — 人格设定。**类型**：`str`。**默认值**：`"你是一个大二女大学生，现在正在上网和群友聊天。"`。建议 200 字以内，使用第二人称描述人格特质和身份特征。

**`reply_style`** — 默认表达风格。**类型**：`str`。**默认值**：见上方配置。描述说话的表达风格和习惯，建议 1-2 行。

**`multiple_reply_style`** — 备用表达风格列表。**类型**：`list[str]`。**默认值**：包含 5 种默认风格。按 `multiple_probability` 的概率从中随机选择一种临时注入。

**`multiple_probability`** — 风格替换概率。**类型**：`float`。**默认值**：`0`。取值范围：`0.0-1.0`。每次构建回复时从备用列表中随机替换的概率。`0` 表示不替换，`1` 表示每次都替换。

***

# 视觉

控制图片消息进入规划器和回复器时的处理模式。

```toml
[visual]
planner_mode = "auto"
replyer_mode = "auto"
wait_image_recognize_max_time = 10
handle_oversized_images = true
max_image_size_mb = 30.0
oversized_image_handle_method = "compress"
```

**`planner_mode`** — 规划器视觉模式。**类型**：`str`（枚举）。**默认值**：`"auto"`。**可选值**：

* `"auto"` — 根据模型信息自动选择
* `"text"` — 纯文本模式，不发送视觉输入
* `"multimodal"` — 多模态模式，发送视觉输入

**`replyer_mode`** — 回复器视觉模式。**类型**：`str`（枚举）。**默认值**：`"auto"`。可选值同上。

**`wait_image_recognize_max_time`** — 识图最长等待。**类型**：`float`。**默认值**：`10`。**单位**：秒。非视觉 planner 请求前等待图片识别完成的最长秒数；设为 `0` 不等待。

**`handle_oversized_images`** — 处理过大图片。**类型**：`bool`。**默认值**：`true`。

**`max_image_size_mb`** — 最大图片大小。**类型**：`float`。**默认值**：`30.0`。**单位**：MB。设为 `0` 不限制。

**`oversized_image_handle_method`** — 过大图片处理方法。**类型**：`str`（枚举）。**默认值**：`"compress"`。**可选值**：

* `"compress"` — 压缩后继续处理
* `"discard"` — 丢弃该图片组件

***

# 聊天

控制回复频率、上下文长度、群聊 / 私聊提示词、no\_action 退避策略、动态发言频率。

```toml
[chat]
talk_value = 1
private_talk_value = 1
mentioned_bot_reply = false
inevitable_at_reply = true
self_message_special_mark = true
max_context_size = 40
max_private_context_size = 60
enable_context_optimization = true
mid_term_memory = true
mid_term_memory_lenth = 10
enable_reply_quote = true
typing_speed = 1.0
planner_interrupt_max_consecutive_count = 0
no_action_backoff_base_seconds = 15
no_action_backoff_cap_seconds = 300
no_action_backoff_start_count = 2
no_action_backoff_bypass_pending_count = 6
group_chat_prompt = "你正在 qq 群里聊天，下面是群里正在聊的内容..."
private_chat_prompts = "你正在聊天，下面是正在聊的内容..."
chat_prompts = []
enable_talk_value_rules = false
```

## 字段说明

**`talk_value`** — 群聊频率。**类型**：`float`。**默认值**：`1`。取值范围：`0-1`。越小越沉默。

**`private_talk_value`** — 私聊频率。**类型**：`float`。**默认值**：`1`。取值范围：`0-1`。

**`mentioned_bot_reply`** — 提及必回复。**类型**：`bool`。**默认值**：`false`。

**`inevitable_at_reply`** — @ 必回复。**类型**：`bool`。**默认值**：`true`。

**`self_message_special_mark`** — 自身消息特殊标注。**类型**：`bool`。**默认值**：`true`。进一步强调哪些消息是自己发送的，减少 bot 认错的情况。

**`max_context_size`** — 群聊上下文长度。**类型**：`int`。**默认值**：`40`。条消息。

**`max_private_context_size`** — 私聊上下文长度。**类型**：`int`。**默认值**：`60`。条消息。

**`enable_context_optimization`** — 优化上下文。**类型**：`bool`。**默认值**：`true`。优化约 50% 的 Planner 上下文消耗，可能影响缓存。

**`mid_term_memory`** — 中期聊天摘要。**类型**：`bool`。**默认值**：`true`。上下文裁切时生成中期摘要，以可展开复杂消息保留。使用的模型回退到 `planner`。

**`mid_term_memory_lenth`** — 中期摘要保留数。**类型**：`int`。**默认值**：`10`。超出后移除最早的摘要。

**`enable_reply_quote`** — 启用引用回复。**类型**：`bool`。**默认值**：`true`。

**`typing_speed`** — 聊天速度。**类型**：`float`。**默认值**：`1.0`。取值范围：`0-2`。模拟打字时间倍乘。`0` 表示不等待，`1` 保持默认等待时间，`2` 表示两倍。

**`planner_interrupt_max_consecutive_count`** — Planner 连续打断上限。**类型**：`int`。**默认值**：`0`。Planner 遇到新消息重新思考的次数，`0` 表示不限制。

## no\_action 退避策略

当麦麦连续沉默（no\_action）时，自动逐步增加等待间隔，避免频繁无意义轮询。

**`no_action_backoff_base_seconds`** — 退避基准秒数。**类型**：`float`。**默认值**：`15`。`0` 表示不启用退避。

**`no_action_backoff_cap_seconds`** — 退避上限秒数。**类型**：`float`。**默认值**：`300`。

**`no_action_backoff_start_count`** — 退避起点。**类型**：`int`。**默认值**：`2`。连续第几次 no\_action 后开始退避。

**`no_action_backoff_bypass_pending_count`** — 退避绕过消息数。**类型**：`int`。**默认值**：`6`。退避期间待处理消息达到该数量直接绕过，`0` 表示不按消息数绕过。

**`group_chat_prompt`** — 群聊提示词。**类型**：`str`。**默认值**：较长默认文本。群聊通用注意事项。

**`private_chat_prompts`** — 私聊提示词。**类型**：`str`。**默认值**：较长默认文本。私聊通用注意事项。

**`chat_prompts`** — 额外提示词列表。**类型**：`list[ExtraPromptItem]`。**默认值**：`[]`。按平台 / 聊天流附加的额外提示词。

**`enable_talk_value_rules`** — 启用动态发言频率规则。**类型**：`bool`。**默认值**：`false`。

## talk\_value\_rules

按聊天流 / 日内时段配置发言频率，默认 2 条全局规则：

```toml
[[chat.talk_value_rules]]
platform = ""
item_id = ""
rule_type = "group"
time = "00:00-08:59"
value = 0.8

[[chat.talk_value_rules]]
platform = ""
item_id = ""
rule_type = "group"
time = "09:00-18:59"
value = 1.0
```

**`platform`** — 平台。**类型**：`str`。**默认值**：`""`。与 `item_id` 一起留空表示全局。

**`item_id`** — 用户 / 群 ID。**类型**：`str`。**默认值**：`""`。

**`rule_type`** — 聊天流类型。**类型**：`str`（枚举）。**默认值**：`"group"`。**可选值**：`"group"` / `"private"`。

**`time`** — 时间段。**类型**：`str`。格式：`"HH:MM-HH:MM"`，支持跨夜。

**`value`** — 发言频率。**类型**：`float`。取值范围：`0-1`。

## chat\_prompts

```toml
[[chat.chat_prompts]]
platform = "qq"
item_id = "123456"
rule_type = "group"
prompt = "这个群里说话要更简短。"
```

`platform`、`item_id`、`rule_type` 和 `prompt` 均需填写，否则该条无效。

***

# 实验性功能

实验性功能，默认全部关闭。

```toml
[experimental]
enable_behavior_learning = false
enable_replyer_format_output = false
focus_mode = false
focus_on_private = false
focus_groups = []
focus_cool_time = 120
```

**`enable_behavior_learning`** — 启用行为学习。**类型**：`bool`。**默认值**：`false`。关闭后不再从裁切历史中抽取和写入行为经验。

**`enable_replyer_format_output`** — Replyer 格式化输出。**类型**：`bool`。**默认值**：`false`。允许 replyer 输出 `<text>`、`<at>`、`<emoji>`、`<image>` 等格式化片段，并在发送前解析为真实消息组件，可能影响回复表现。

**`focus_mode`** — Focus 模式。**类型**：`bool`。**默认值**：`false`。开启后同一时间只有一个 Maisaka 处于活跃关注状态，忽略聊天频率控制。

**`focus_on_private`** — 私聊启用 Focus。**类型**：`bool`。**默认值**：`false`。关闭时 Focus 仅作用于群聊。

**`focus_groups`** — Focus 互通组。**类型**：`list[ChatStreamGroup]`。**默认值**：`[]`。不配置时所有启用 Focus 的聊天共享一个 Focus；配置后同组互通，不同组可同时 Focus。

**`focus_cool_time`** — Focus 冷却时间。**类型**：`int`。**默认值**：`120`。**单位**：秒。Focus 超过该秒数没有进入循环时，会被其他聊天的新消息唤醒一次。

***

# 消息接收

控制图片解析和消息过滤。

```toml
[message_receive]
image_parse_threshold = 5
ban_words = []
ban_msgs_regex = []
```

**`image_parse_threshold`** — 图片解析阈值。**类型**：`int`。**默认值**：`5`。消息中图片数量不超过此值启用图片解析，超过则跳过。

**`ban_words`** — 过滤词列表。**类型**：`set[str]`。**默认值**：`{}`。包含这些词汇的消息会被过滤。

**`ban_msgs_regex`** — 过滤正则列表。**类型**：`set[str]`。**默认值**：`{}`。正则非法会导致配置校验失败。

***

# 记忆

A\_Memorix 是 MaiBot 的长期记忆系统，负责记忆存储、向量化、检索、人物画像、记忆演化和 Web 运维。

完整说明（12 个子段落）请移步 → **[A\_Memorix 配置详解](./amemorix-config.md)**

```toml
# 快速启用
[a_memorix]

[a_memorix.plugin]
enabled = true
```

***

# 表达学习

控制表达方式学习、AI 审核和互通组。

```toml
[expression]
expression_checked_only = true
expression_self_reflect = true
enable_precise_expression_selection = false
max_expression_learner = 3
learning_list = []
expression_groups = []
```

**`expression_checked_only`** — 仅选择已人工检查的表达。**类型**：`bool`。**默认值**：`true`。

**`expression_self_reflect`** — 表达学习 AI 审核。**类型**：`bool`。**默认值**：`true`。写入前进行 AI 审核。

**`enable_precise_expression_selection`** — 精细表达选择。**类型**：`bool`。**默认值**：`false`。replyer 用子代理挑选更贴合语境的表达。

**`max_expression_learner`** — 表达学习批次数上限。**类型**：`int`。**默认值**：`3`。同一聊天流始终只允许一个批次。

**`learning_list`** — 表达学习配置列表。**类型**：`list[LearningItem]`。**默认值**：`[]`。

**`expression_groups`** — 表达学习互通组。**类型**：`list[ChatStreamGroup]`。**默认值**：`[]`。组内的表达学习结果共享。

### learning\_list

```toml
[[expression.learning_list]]
platform = ""
item_id = ""
type = "group"
use = true
learn = true
```

`platform` / `item_id` 留空表示全局规则。`type` 可选 `"group"` / `"private"`。

***

# 黑话

控制黑话学习和互通组。`platform` 或 `item_id` 可使用 `*` 通配。

```toml
[jargon]
learning_list = []
jargon_groups = []
```

**`learning_list`** — 黑话学习配置列表。**类型**：`list[LearningItem]`。**默认值**：`[]`。

**`jargon_groups`** — 黑话学习互通组。**类型**：`list[ChatStreamGroup]`。**默认值**：`[]`。

### learning\_list

字段含义与 [expression.learning\_list](#_5-1-learning-list) 相同。

***

# 语音

```toml
[voice]
enable_asr = false
```

**`enable_asr`** — 启用语音识别。**类型**：`bool`。**默认值**：`false`。

***

# 表情包

```toml
[emoji]
emoji_send_num = 25
max_reg_num = 64
do_replace = true
check_interval = 10
steal_emoji = true
content_filtration = false
```

**`emoji_send_num`** — 表情包发送选择数。**类型**：`int`。**默认值**：`25`。取值范围：`1-64`。

**`max_reg_num`** — 表情包最大注册数。**类型**：`int`。**默认值**：`64`。

**`do_replace`** — 满额后替换旧表情包。**类型**：`bool`。**默认值**：`true`。关闭则达到上限后不再收集。

**`check_interval`** — 表情包检查间隔。**类型**：`int`。**默认值**：`10`。**单位**：分钟。

**`steal_emoji`** — 偷取聊天中的表情包。**类型**：`bool`。**默认值**：`true`。

**`content_filtration`** — 表情包过滤。**类型**：`bool`。**默认值**：`false`。

***

# 关键词反应

```toml
[[keyword_reaction.keyword_rules]]
keywords = ["关键词"]
reaction = "触发后的反应"

[[keyword_reaction.regex_rules]]
regex = ["^正则.*"]
reaction = "触发后的反应"
```

每个规则包含 `keywords` / `regex` 列表和 `reaction` 触发回复内容。

***

# 回复后处理

```toml
[response_post_process]
enable_response_post_process = true
```

**`enable_response_post_process`** — 启用回复后处理总开关。**类型**：`bool`。**默认值**：`true`。关闭后错别字生成器和回复分割器均不生效。

***

# 中文错别字

```toml
[chinese_typo]
enable = true
error_rate = 0.01
min_freq = 9
tone_error_rate = 0.1
word_replace_rate = 0.006
```

**`enable`** — 启用错别字生成。**类型**：`bool`。**默认值**：`true`。

**`error_rate`** — 单字替换概率。**类型**：`float`。**默认值**：`0.01`。取值范围：`0-1`。

**`min_freq`** — 最小字频阈值。**类型**：`int`。**默认值**：`9`。

**`tone_error_rate`** — 声调错误概率。**类型**：`float`。**默认值**：`0.1`。取值范围：`0-1`。

**`word_replace_rate`** — 整词替换概率。**类型**：`float`。**默认值**：`0.006`。取值范围：`0-1`。

***

# 回复分割

```toml
[response_splitter]
enable = true
max_length = 512
max_sentence_num = 8
max_split_num = 3
enable_kaomoji_protection = false
enable_overflow_return_all = false
```

**`enable`** — 启用回复分割。**类型**：`bool`。**默认值**：`true`。

**`max_length`** — 单条回复最大字符数。**类型**：`int`。**默认值**：`512`。

**`max_sentence_num`** — 单条回复最大句子数。**类型**：`int`。**默认值**：`8`。

**`max_split_num`** — 最多分割条数。**类型**：`int`。**默认值**：`3`。

**`enable_kaomoji_protection`** — 颜文字保护。**类型**：`bool`。**默认值**：`false`。开启后分割时保护颜文字不被拆分。

**`enable_overflow_return_all`** — 超出上限时一次性返回全部。**类型**：`bool`。**默认值**：`false`。

***

# 日志

```toml
[log]
date_style = "m-d H:i:s"
log_level_style = "lite"
color_text = "full"
log_level = "INFO"
console_log_level = "INFO"
file_log_level = "DEBUG"
log_file_max_bytes = 5242880
max_log_files = 30
log_cleanup_days = 30
llm_request_snapshot_limit = 128
maisaka_prompt_preview_limit = 256
maisaka_reply_effect_limit = 256
suppress_libraries = ["faiss", "httpx", "urllib3", "asyncio", "websockets", "httpcore", "requests", "sqlalchemy", "openai", "uvicorn", "jieba"]
library_log_levels = {"aiohttp" = "WARNING", "PIL" = "WARNING"}
```

**`date_style`** — 日期格式。**类型**：`str`。**默认值**：`"m-d H:i:s"`。

**`log_level_style`** — 日志等级显示样式。**类型**：`str`（枚举）。**默认值**：`"lite"`。**可选值**：`"lite"` / `"compact"` / `"full"`。

**`color_text`** — 控制台颜色模式。**类型**：`str`（枚举）。**默认值**：`"full"`。**可选值**：`"none"` / `"title"` / `"full"`。

**`log_level`** — 全局日志级别。**类型**：`str`（枚举）。**默认值**：`"INFO"`。

**`console_log_level`** — 控制台日志级别。**类型**：`str`（枚举）。**默认值**：`"INFO"`。

**`file_log_level`** — 文件日志级别。**类型**：`str`（枚举）。**默认值**：`"DEBUG"`。

**`log_file_max_bytes`** — 单个日志文件最大字节数。**类型**：`int`。**默认值**：`5242880`（5MB）。

**`max_log_files`** — 最多保留主日志文件数。**类型**：`int`。**默认值**：`30`。

**`log_cleanup_days`** — 主日志文件保留天数。**类型**：`int`。**默认值**：`30`。

**`llm_request_snapshot_limit`** — 失败请求快照最多保留数。**类型**：`int`。**默认值**：`128`。

**`maisaka_prompt_preview_limit`** — 每个会话最多保留的 Maisaka Prompt 预览组数。**类型**：`int`。**默认值**：`256`。

**`maisaka_reply_effect_limit`** — 每个会话最多保留的回复效果记录数。**类型**：`int`。**默认值**：`256`。

**`suppress_libraries`** — 完全屏蔽日志的第三方库。**类型**：`list[str]`。**默认值**：包含 11 个库。

**`library_log_levels`** — 特定第三方库的日志级别。**类型**：`dict[str, str]`。**默认值**：`{"aiohttp" = "WARNING", "PIL" = "WARNING"}`。

***

# 遥测

```toml
[telemetry]
enable = true
```

**`enable`** — 启用遥测。**类型**：`bool`。**默认值**：`true`。

***

# 调试

```toml
[debug]
show_maisaka_thinking = true
show_jargon_prompt = false
show_memory_prompt = false
enable_reply_effect_tracking = false
record_reply_request = false
record_planner_request = false
enable_llm_cache_stats = false
```

**`show_maisaka_thinking`** — 显示回复器推理。**类型**：`bool`。**默认值**：`true`。

**`show_jargon_prompt`** — 显示黑话提示词。**类型**：`bool`。**默认值**：`false`。

**`show_memory_prompt`** — 显示记忆检索 prompt。**类型**：`bool`。**默认值**：`false`。

**`enable_reply_effect_tracking`** — 回复效果评分追踪。**类型**：`bool`。**默认值**：`false`。

**`record_reply_request`** — 记录 Replyer 请求体。**类型**：`bool`。**默认值**：`false`。

**`record_planner_request`** — 记录 Planner 完整请求和回复。**类型**：`bool`。**默认值**：`false`。

**`enable_llm_cache_stats`** — 记录 LLM prompt cache 统计。**类型**：`bool`。**默认值**：`false`。

***

# 消息服务

```toml
[maim_message]
ws_server_host = "127.0.0.1"
ws_server_port = 8000
auth_token = []
enable_api_server = false
api_server_host = "0.0.0.0"
api_server_port = 8090
api_server_use_wss = false
api_server_cert_file = ""
api_server_key_file = ""
api_server_allowed_api_keys = []
```

**`ws_server_host`** — 旧版 WS 服务器主机。**类型**：`str`。**默认值**：`"127.0.0.1"`。

**`ws_server_port`** — 旧版 WS 服务器端口。**类型**：`int`。**默认值**：`8000`。

**`auth_token`** — 认证令牌列表。**类型**：`list[str]`。**默认值**：`[]`。为空不启用验证。

**`enable_api_server`** — 启用新版 API Server。**类型**：`bool`。**默认值**：`false`。

**`api_server_host`** — 新版 API Server 主机。**类型**：`str`。**默认值**：`"0.0.0.0"`。

**`api_server_port`** — 新版 API Server 端口。**类型**：`int`。**默认值**：`8090`。

**`api_server_use_wss`** — 启用 WSS。**类型**：`bool`。**默认值**：`false`。

**`api_server_cert_file`** — SSL 证书路径。**类型**：`str`。**默认值**：`""`。

**`api_server_key_file`** — SSL 密钥路径。**类型**：`str`。**默认值**：`""`。

**`api_server_allowed_api_keys`** — 允许的 API Key 列表。**类型**：`list[str]`。**默认值**：`[]`。为空允许所有连接。

***

# WebUI

```toml
[webui]
enabled = true
host = "127.0.0.1"
port = 8001
mode = "production"
anti_crawler_mode = "basic"
allowed_ips = "127.0.0.1"
trusted_proxies = ""
trust_xff = false
secure_cookie = false
enforce_public_outbound_url = true
enable_paragraph_content = false
```

**`enabled`** — 启用 WebUI。**类型**：`bool`。**默认值**：`true`。

**`host`** — 绑定主机。**类型**：`str`。**默认值**：`"127.0.0.1"`。

**`port`** — 绑定端口。**类型**：`int`。**默认值**：`8001`。

**`mode`** — 运行模式。**类型**：`str`（枚举）。**默认值**：`"production"`。**可选值**：`"development"` / `"production"`。

**`anti_crawler_mode`** — 防爬虫模式。**类型**：`str`。**默认值**：`"basic"`。**可选值**：`false` / `"strict"` / `"loose"` / `"basic"`。

**`allowed_ips`** — IP 白名单。**类型**：`str`。**默认值**：`"127.0.0.1"`。逗号分隔，支持 CIDR 和通配符。

**`trusted_proxies`** — 信任的代理 IP。**类型**：`str`。**默认值**：`""`。逗号分隔。

**`trust_xff`** — 启用 X-Forwarded-For。**类型**：`bool`。**默认值**：`false`。

**`secure_cookie`** — 启用安全 Cookie。**类型**：`bool`。**默认值**：`false`。仅 HTTPS 传输。

**`enforce_public_outbound_url`** — 强制公网出站 URL 校验。**类型**：`bool`。**默认值**：`true`。关闭后允许内网 / TUN 代理地址。

**`enable_paragraph_content`** — 加载段落完整内容。**类型**：`bool`。**默认值**：`false`。会占用额外内存。

***

# 数据库

```toml
[database]
save_binary_data = false
```

**`save_binary_data`** — 保存二进制数据。**类型**：`bool`。**默认值**：`false`。开启后消息中的语音等二进制数据保存为独立文件，二次识别可用但数据文件夹体积增大。仅影响新存储的消息。

***

# MCP

```toml
[mcp]
enable = true
```

**`enable`** — 启用 MCP。**类型**：`bool`。**默认值**：`true`。

详细说明（服务器配置、Sampling、Roots、Elicitation）请移步 → **[MCP 配置详解](./mcp-config.md)**

***

# 插件管理

```toml
[plugin]
permission = []
```

**`permission`** — 插件管理权限列表。**类型**：`list[str]`。**默认值**：`[]`。格式：`platform:id`，如 `"qq:123456789"`。

***

# 插件运行时

```toml
[plugin_runtime]
enabled = true
health_check_interval_sec = 30.0
max_restart_attempts = 3
runner_spawn_timeout_sec = 30.0
hook_blocking_timeout_sec = 60
ipc_socket_path = ""
```

**`enabled`** — 启用插件系统。**类型**：`bool`。**默认值**：`true`。

**`health_check_interval_sec`** — 健康检查间隔。**类型**：`float`。**默认值**：`30.0`。**单位**：秒。

**`max_restart_attempts`** — Runner 崩溃后最大自动重启次数。**类型**：`int`。**默认值**：`3`。

**`runner_spawn_timeout_sec`** — Runner 启动超时。**类型**：`float`。**默认值**：`30.0`。**单位**：秒。

**`hook_blocking_timeout_sec`** — Hook 阻塞全局超时。**类型**：`float`。**默认值**：`60`。**单位**：秒。

**`ipc_socket_path`** — 自定义 IPC Socket 路径。**类型**：`str`。**默认值**：`""`。仅 Linux/macOS 生效，留空自动生成。

***

## 配置文件总览

`bot_config.toml` 顶层包含以下段落（按一级键分类）：

* **`[bot]`** — 机器人身份、平台、昵称、别名
* **`[personality]`** — 人设和回复风格
* **`[visual]`** — 图片理解模式和识图提示词
* **`[chat]`** — 回复频率、上下文、聊天提示词、退避策略
* **`[experimental]`** — 实验性功能（行为学习、Focus 模式）
* **`[message_receive]`** — 图片解析阈值、消息过滤
* **`[a_memorix]`** — 长期记忆系统 → [详见 A\_Memorix 配置](./amemorix-config.md)
* **`[expression]`** — 表达学习、表达检查、互通组
* **`[jargon]`** — 黑话学习、黑话互通组
* **`[voice]`** — 语音识别
* **`[emoji]`** — 表情包收集、过滤、发送
* **`[keyword_reaction]`** — 关键词 / 正则触发反应
* **`[response_post_process]`** — 回复后处理总开关
* **`[chinese_typo]`** — 中文错别字生成
* **`[response_splitter]`** — 回复分割
* **`[log]`** — 日志级别、格式、文件保留策略
* **`[telemetry]`** — 遥测开关
* **`[debug]`** — 调试显示和追踪
* **`[maim_message]`** — maim\_message WebSocket / API Server
* **`[webui]`** — WebUI 服务和安全设置
* **`[database]`** — 消息二进制数据保存策略
* **`[mcp]`** — MCP 客户端和服务器配置 → [详见 MCP 配置](./mcp-config.md)
* **`[plugin]`** — 插件管理权限
* **`[plugin_runtime]`** — 插件运行时和浏览器渲染配置

::: tip
配置文件开头的 `[inner] version` 由程序管理，普通用户不需要手动修改。
:::

***

## 下一步

* 配置模型：看 [模型配置](./model-config.md)
* 模型高级参数：看 [模型额外参数](./model-extra-params.md)
* 连接 QQ：看 [NapCat 适配器](../adapters/napcat.md)
* 管理 WebUI：[WebUI 配置管理](../webui/config-management.md)
* 记忆系统详解：[A\_Memorix 配置](./amemorix-config.md)
* MCP 配置详解：[MCP 配置](./mcp-config.md)

---

---
url: /develop/plugin-dev/commands.md
---

# Command 组件

`@Command` 是基于正则匹配的命令组件。当用户发送的消息匹配到某个 Command 的正则模式时，MaiBot 会调度执行对应的 Command 处理函数。

## 装饰器签名

```python
from maibot_sdk import Command

@Command(
    name: str,                    # 命令名称（必填）
    description: str = "",        # 命令描述
    pattern: str = "",            # 正则匹配模式
    aliases: list[str] | None = None,  # 命令别名列表
    **metadata,                   # 额外元数据
)
```

### 参数说明

* **`name`** `str` — 命令名称，需在插件内唯一
* **`description`** `str` — 命令描述
* **`pattern`** `str` — 正则匹配模式字符串。当用户消息匹配此模式时，触发该命令
* **`aliases`** `list[str] | None` — 命令别名列表，提供额外的触发方式

## 基本用法

```python
from maibot_sdk import MaiBotPlugin, Command


class MyPlugin(MaiBotPlugin):
    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2
```

### 带别名的命令

```python
@Command("greet", pattern=r"^/greet", aliases=["/hi", "/hey"])
async def handle_greet(self, **kwargs):
    await self.ctx.send.text("你好！", kwargs["stream_id"])
    return True, "你好！", 2
```

使用 `/greet`、`/hi` 或 `/hey` 均可触发此命令。

### 带正则捕获组的命令

```python
import re

@Command("echo", pattern=r"^/echo\s+(?P<text>.+)$")
async def handle_echo(self, **kwargs):
    matched = kwargs.get("matched_groups", {})
    text = matched.get("text", "").strip()
    stream_id = kwargs["stream_id"]
    await self.ctx.send.text(f"Echo: {text}", stream_id)
    return True, f"Echo: {text}", 1
```

## 处理函数参数

Command 处理函数接收 `**kwargs`，其中包含以下参数：

* **`stream_id`** `str` — 当前聊天流 ID，用于发送消息
* **`matched_groups`** `dict` — 正则命名捕获组的匹配结果
* **`raw_message`** `str` — 用户发送的原始消息文本
* **`message`** `dict` — 完整的消息对象

### 返回值

Command 处理函数必须返回三元组：

```python
return success, response, weight
```

* **`success`** `bool` — 命令是否成功执行
* **`response`** `str` — 命令执行结果的文本描述
* **`weight`** `int` — 命令优先级权重，数值越高优先级越高

```python
# 命令成功执行
return True, "操作成功", 2

# 命令执行失败
return False, "参数错误", 1
```

## 正则模式编写指南

### 推荐模式

```python
# 精确匹配 /hello
pattern=r"^/hello$"

# 匹配 /hello 加可选参数
pattern=r"^/hello(?P<name>.+)?$"

# 匹配 /echo 加必填参数
pattern=r"^/echo\s+(?P<text>.+)$"

# 匹配 /set 加键值对
pattern=r"^/set\s+(?P<key>\w+)\s+(?P<value>.+)$"
```

### 使用命名捕获组

推荐使用 `(?P<name>...)` 命名捕获组，可以通过 `kwargs["matched_groups"]` 按名称访问匹配结果：

```python
@Command("ban", pattern=r"^/ban\s+(?P<user>\w+)(?:\s+(?P<reason>.+))?$")
async def handle_ban(self, **kwargs):
    matched = kwargs.get("matched_groups", {})
    user = matched.get("user", "")
    reason = matched.get("reason", "无原因")
    await self.ctx.send.text(f"已封禁 {user}，原因：{reason}", kwargs["stream_id"])
    return True, f"已封禁 {user}", 2
```

## 命令执行流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Host as Host 主进程
    participant Runner as Runner 子进程
    participant Plugin as 插件

    User->>Host: 发送消息
    Host->>Host: 正则匹配命令
    Host->>Runner: invoke_plugin(command)
    Runner->>Plugin: 调用 Command 处理函数
    Plugin->>Plugin: 执行命令逻辑
    Plugin-->>Runner: 返回 (success, response, weight)
    Runner-->>Host: 返回结果
```

## 命令相关 Hook

命令执行前后有内置 Hook 点可供 `@HookHandler` 订阅：

* `chat.command.before_execute`：命令执行前触发，可中止或改写参数
* `chat.command.after_execute`：命令执行后触发，可改写返回结果

## 完整示例

```python
from maibot_sdk import MaiBotPlugin, Command, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class AdminPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("管理插件已加载")

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Command("status", pattern=r"^/status$")
    async def handle_status(self, **kwargs):
        """查看系统状态"""
        stream_id = kwargs["stream_id"]
        await self.ctx.send.text("系统运行正常 ✅", stream_id)
        return True, "系统运行正常", 1

    @Command("echo", pattern=r"^/echo\s+(?P<text>.+)$")
    async def handle_echo(self, **kwargs):
        """回显消息"""
        matched = kwargs.get("matched_groups", {})
        text = matched.get("text", "").strip()
        stream_id = kwargs["stream_id"]
        await self.ctx.send.text(text, stream_id)
        return True, text, 1

    @Command("help", pattern=r"^/help$", aliases=["/帮助"])
    async def handle_help(self, **kwargs):
        """显示帮助信息"""
        stream_id = kwargs["stream_id"]
        help_text = "可用命令：\n/status - 查看状态\n/echo <text> - 回显消息\n/help - 显示帮助"
        await self.ctx.send.text(help_text, stream_id)
        return True, "帮助信息已发送", 1


def create_plugin():
    return AdminPlugin()
```

---

---
url: /manual/adapters/discord.md
---

# Discord 适配器

MaiBot 的 Discord 平台适配器插件，通过 Discord Gateway WebSocket 将 Discord Bot 与 MaiBot 无缝桥接，支持 Guild 频道、DM 私聊、Thread 子区、Reaction 及语音功能。

## 适配器仓库

Discord 适配器源码：[litroenade/MaiBot-Discord-Adapter](https://github.com/litroenade/MaiBot-Discord-Adapter)

## 创建 Discord Bot

在使用适配器之前，你需要先在 Discord 上创建一个 Bot 并获取 Token。

### 第一步：创建应用和 Bot

1. 访问 [Discord Developer Portal](https://discord.com/developers/applications)
2. 点击右上角 **New Application**，输入应用名称并创建
3. 在左侧导航栏点击 **Bot**
4. 点击 **Reset Token**（或 **Add Bot**），复制 Bot Token 并妥善保存

### 第二步：启用 Privileged Gateway Intents

在 Bot 页面向下滚动到 **Privileged Gateway Intents** 区域，启用以下 Intent：

* **Message Content Intent**（必须）— 不启用则无法读取消息内容
* **Presence Intent**（可选）— 需要监听用户在线状态时启用
* **Server Members Intent**（可选）— 需要获取完整成员列表时启用

::: warning 注意
如果不启用 **Message Content Intent**，Bot 将无法读取消息文本内容，`connection.intent_message_content` 即便设为 `true` 也不会生效。
:::

### 第三步：邀请 Bot 到服务器

1. 在左侧导航栏点击 **OAuth2**
2. 在 **OAuth2 URL Generator** 中选择：
   * **Scopes**：勾选 `bot`
   * **Bot Permissions**：根据需要勾选以下权限：
     * Send Messages — 发送消息
     * Read Message History — 读取消息历史（回复引用必需）
     * View Channels — 查看频道
     * Add Reactions — 添加表情反应
     * Connect — 连接语音频道（语音功能必需）
     * Speak — 在语音频道说话（语音功能必需）
     * Attach Files — 发送附件/图片
3. 复制生成的邀请链接，在浏览器中打开并选择你的服务器完成邀请

::: tip 权限建议
如果需要使用语音功能，Bot 对目标语音频道还需要拥有 `View Channel`、`Connect`、`Speak` 权限，否则无法加入和播放语音。
:::

### 第四步：获取服务器/频道 ID

配置聊天过滤需要用到服务器 ID 和频道 ID。在 Discord 中启用开发者模式：

1. 打开 Discord 设置 -> 高级 -> 开启 **开发者模式**
2. 右键服务器图标 -> 复制服务器 ID
3. 右键频道名 -> 复制频道 ID

## 安装

将适配器仓库克隆到 MaiBot 的 `plugins/` 目录下：

```bash
cd /path/to/MaiBot/plugins
git clone https://github.com/litroenade/MaiBot-Discord-Adapter.git
```

也可以通过 MaiBot 的 WebUI 界面安装插件。

### 依赖

* `maibot_sdk` >= 2.0.0（由 MaiBot 主程序提供）
* `discord.py` >= 2.3.0
* `discord-ext-voice-recv` >= 0.4.1a139（语音功能需要）
* `PyNaCl` >= 1.5.0（语音功能需要）

语音相关的依赖会在启用语音功能时自动安装。如果只做纯文本收发，无需额外安装。

## 配置

### 启用适配器

适配器安装后**默认是禁用的**，需要手动启用。

#### 方式一：编辑配置文件

编辑 `plugins/MaiBot-Discord-Adapter/config.toml`，将 `enabled` 改为 `true` 并填写 Bot Token：

```toml
[plugin]
enabled = true                # 启用适配器
config_version = "1.0.0"

[connection]
token = "你的Discord Bot Token"  # 必填
```

然后重启 MaiBot 即可。

#### 方式二：通过 WebUI 启用

1. 浏览器访问 MaiBot WebUI，输入 Access Token 登录
2. 点击左侧菜单 **"插件管理"**
3. 找到 **"Discord 适配器"**，点击启用开关
4. 在配置中填写 `connection.token`
5. 保存配置后重启 MaiBot（或等待插件热重载）

::: tip 提示
配置也可以通过 WebUI 的插件配置页面进行热重载修改，无需重启 MaiBot。
:::

### 聊天过滤说明

适配器默认启用聊天名单过滤，名单模式默认为**黑名单**（即允许所有来源）。如果需要限制 Bot 只响应特定服务器或频道，可以将模式改为白名单并填写对应 ID：

```toml
[chat]
guild_list_type = "whitelist"
guild_list = ["你的服务器ID"]
channel_list_type = "whitelist"
channel_list = ["你的频道ID"]
```

如果发现 Bot 已连接但消息没有反应，优先检查聊天过滤配置。

## 配置参考

### `[plugin]` — 插件设置

* **`enabled`** — 是否启用 Discord 适配器。关闭后插件保持空闲，不会建立 Discord 连接。默认关闭
* **`config_version`** — 当前配置结构版本（自动维护，无需手动修改）。默认 "1.0.0"

### `[connection]` — Discord 连接

* **`token`** — Discord Bot Token，在 Developer Portal 的 Bot 页面复制。启用适配器时必填。默认为空
* **`intent_messages`** — 服务器消息权限（Guild Messages），控制服务器内频道/子区消息。默认开启
* **`intent_guilds`** — 服务器权限（获取服务器信息）。默认开启
* **`intent_dm_messages`** — 私信消息权限（Direct Messages），控制私聊消息。默认开启
* **`intent_message_content`** — 消息内容权限，必须启用，否则无法读取消息内容。默认开启
* **`intent_voice_states`** — 语音状态权限，语音功能必须启用；只做纯文本收发时可以关闭。默认关闭
* **`retry_delay`** — 断线重试间隔（秒）。默认 5
* **`connection_check_interval`** — 连接状态检查间隔（秒，建议 30 秒以上）。默认 30

### `[chat]` — 聊天过滤

* **`guild_list_type`** — 服务器名单模式，可选 `whitelist`（白名单）或 `blacklist`（黑名单）。默认 "blacklist"
* **`guild_list`** — 服务器 ID 名单。默认为空
* **`channel_list_type`** — 频道名单模式。默认 "blacklist"
* **`channel_list`** — 频道 ID 名单。默认为空
* **`thread_list_type`** — 子区名单模式（继承频道权限时此项无效）。默认 "blacklist"
* **`thread_list`** — 子区 ID 名单。默认为空
* **`user_list_type`** — 用户名单模式。默认 "blacklist"
* **`user_list`** — 用户 ID 名单。默认为空
* **`allow_thread_interaction`** — 是否允许在子区（Thread）中互动。默认开启
* **`inherit_channel_permissions`** — 子区是否继承父频道权限。开启后父频道允许则子区允许，子区名单将被忽略。默认开启
* **`inherit_channel_memory`** — 子区是否继承父频道记忆。开启后子区与父频道共享上下文记忆；关闭则各自独立。默认开启
* **`show_typing_indicator`** — 收到可处理消息后是否先显示 Discord 的"正在输入"状态。默认开启
* **`typing_indicator_delay_ms`** — 显示"正在输入"前的延迟时间（毫秒），避免极快回复也闪一下。默认 0
* **`typing_indicator_timeout_sec`** — "正在输入"状态的最长保持时间（秒），设为 0 表示直到回复发出前都不主动超时。默认 0

::: tip 聊天过滤说明

* **白名单模式**：只处理名单中的服务器/频道/用户消息，其余丢弃
* **黑名单模式**：处理所有消息，但丢弃名单中的服务器/频道/用户消息
* 默认所有名单模式均为黑名单（即允许所有），如果发现 Bot 已连接但没有反应，优先检查名单配置
  :::

### `[platform]` — 平台设置

* **`platform_name`** — 平台标识符，用于在 MaiBot 中区分不同的 Discord 实例。多实例运行时需唯一。默认 "discord"

### `[filters]` — 消息过滤

* **`ignore_self_message`** — 是否忽略机器人自身发送的消息。建议保持开启，避免机器人处理自己发出的消息。默认开启
* **`ignore_bot_message`** — 是否忽略其他机器人发送的消息。默认开启

### `[voice]` — 语音功能

* **`enabled`** — 是否启用语音功能。关闭时不会创建语音管理器，也不会主动加入任何语音频道。默认关闭
* **`voice_mode`** — 语音频道模式：`fixed` 常驻指定频道，`auto` 有人进入时自动加入、无人时退出。默认 "auto"
* **`fixed_channel_id`** — 固定模式下的语音频道 ID（填写语音频道而非频道分类的 ID）。默认为空
* **`auto_channel_list`** — 自动模式下的候选语音频道 ID 列表，只会在这里列出的语音频道里自动进出。默认为空
* **`idle_timeout_sec`** — 自动模式下无人后等待退出的秒数。默认 300
* **`tts_provider`** — TTS 语音合成服务商，可选 `siliconflow` / `gptsovits` / `minimax`。默认 "siliconflow"
* **`stt_provider`** — STT 语音识别服务商，可选 `siliconflow_sensevoice` / `aliyun` / `tencent`。默认 "siliconflow\_sensevoice"
* **`enable_vad`** — 是否启用基于音量的语音活动检测（VAD）。默认开启
* **`vad_threshold_db`** — VAD 音量阈值（dB），高于此值视为正在说话。范围约 -60（灵敏）到 -30（严格）。默认 -50.0
* **`vad_deactivation_delay_ms`** — VAD 关闭延迟（毫秒），低于阈值后等待此时长才判定停止说话，避免断句。默认 500
* **`send_text_in_voice`** — TTS 播报时是否同时发送文字到语音频道文字区域（调试用）。默认关闭

::: warning 语音前置条件
启用语音功能需要同时满足以下条件：

* `voice.enabled = true`
* `connection.intent_voice_states = true`
* Bot 对目标语音频道拥有 `View Channel`、`Connect`、`Speak` 权限
  :::

### `[siliconflow_tts]` — SiliconFlow TTS

当 `voice.tts_provider` 设为 `siliconflow` 时生效。

* **`api_key`** — SiliconFlow API 密钥。默认为空
* **`api_base`** — SiliconFlow API 地址。默认 "https://api.siliconflow.cn/v1"
* **`model`** — TTS 模型标识。默认 "fnlp/MOSS-TTSD-v0.5"
* **`voice`** — TTS 音色标识。默认 "fnlp/MOSS-TTSD-v0.5:alex"
* **`sample_rate`** — 音频采样率。opus 仅支持 48000；wav/pcm 支持 8000/16000/24000/32000/44100；mp3 支持 32000/44100。默认 32000
* **`speed`** — 语速（0.1 ~ 2.0）。默认 1.0
* **`response_format`** — 音频返回格式（mp3/opus/wav/pcm），推荐默认使用 wav。默认 "wav"

### `[gptsovits_tts]` — GPT-SoVITS TTS

当 `voice.tts_provider` 设为 `gptsovits` 时生效。

* **`api_base`** — GPT-SoVITS API 地址。默认 "http://127.0.0.1:8000"
* **`version`** — GPT-SoVITS 服务版本号。默认 "v4"
* **`model`** — 模板模型名，用于 infer\_single 模板模型接口。配置页会优先从本地 GSV 拉取模板模型供选择。默认为空
* **`voice`** — 模板情感/音色（可选），留空则自动选择。默认为空
* **`text_lang`** — 合成语言代码。默认 "zh"
* **`response_format`** — 期望的音频格式，推荐 wav。默认 "wav"
* **`speed_factor`** — 语速因子。默认 1.0

::: tip 关于模板模型
配置页会优先从本地 GPT-SoVITS 服务的 `/models/{version}` 接口拉取模板模型列表供选择。如果拉取失败，也可以手动填写。不要填写 `GSVI-v4` 这类 OpenAI 兼容模型 ID。
:::

### `[minimax_tts]` — MiniMax TTS

当 `voice.tts_provider` 设为 `minimax` 时生效。

* **`api_key`** — MiniMax API 密钥。默认为空
* **`api_base`** — MiniMax API 地址。默认 "https://api.minimax.io"
* **`model`** — TTS 模型。默认 "speech-2.8-hd"
* **`voice_id`** — 音色 ID。默认 "male-qn-qingse"
* **`speed`** — 语速（0.5 ~ 2.0）。默认 1.0
* **`vol`** — 音量（0.1 ~ 2.0）。默认 1.0
* **`pitch`** — 音调偏移（-12 ~ 12）。默认 0.0
* **`audio_sample_rate`** — 输出采样率，可选值 8000/16000/22050/24000/32000/44100。默认 32000
* **`output_format`** — 音频编码格式（pcm/mp3/flac/wav）。默认 "mp3"

### `[siliconflow_stt]` — SiliconFlow STT

当 `voice.stt_provider` 设为 `siliconflow_sensevoice` 时生效。

* **`api_key`** — SiliconFlow API 密钥。默认为空
* **`api_base`** — SiliconFlow API 地址。默认 "https://api.siliconflow.cn/v1"
* **`model`** — STT 模型标识。默认 "FunAudioLLM/SenseVoiceSmall"

### `[aliyun_stt]` — 阿里云语音识别

当 `voice.stt_provider` 设为 `aliyun` 时生效。

* **`access_key_id`** — 阿里云 AccessKey ID。默认为空
* **`access_key_secret`** — 阿里云 AccessKey Secret。默认为空
* **`app_key`** — 智能语音交互项目 App Key。默认为空
* **`region`** — 服务区域。默认 "cn-shanghai"

### `[tencent_stt]` — 腾讯云语音识别

当 `voice.stt_provider` 设为 `tencent` 时生效。

* **`secret_id`** — 腾讯云 SecretId。默认为空
* **`secret_key`** — 腾讯云 SecretKey。默认为空
* **`engine`** — 识别引擎类型。默认 "16k\_zh"
* **`region`** — 服务区域。默认 "ap-shanghai"

## 当前能力

### 入站消息（Discord -> MaiBot）

* Guild 频道消息
* DM 私聊消息
* Thread 子区消息
* 提及、引用回复、图片、贴纸
* Reaction 添加/移除事件
* 可选语音转文本（STT）

### 出站消息（MaiBot -> Discord）

* 普通文本
* 引用回复
* 用户/角色提及
* 图片与部分附件
* Reaction 添加/移除
* DM / Guild / Thread 路由
* 可选文本转语音（TTS）

### 运行时能力

* WebUI / `config.toml` 配置映射
* 连接状态上报
* 断线重连与健康检查
* 子区上下文路由
* Discord 平台消息 ID 回执回写
* 输入状态提示（Typing Indicator）
* 超长消息自动拆分

## 验证连接

启动 MaiBot 后，检查以下内容确认适配器工作正常：

1. **MaiBot 日志**：看到 `Discord 适配器启动任务已创建`，说明 Bot 已开始连接
2. **MaiBot 日志**：无 `connection.token 为空` 或 `Discord 客户端未就绪` 等错误
3. **发消息测试**：在 Discord 中向 Bot 发送私聊消息或在频道中 @Bot，看是否有回复

### 常见问题

**Bot 启动后没有连接 Discord**

* 检查 `plugin.enabled` 是否设为 `true`
* 检查 `connection.token` 是否填写正确
* 查看日志中是否有 Token 相关的错误

**频道中收不到消息**

* 确认已在 Developer Portal 中启用 **Message Content Intent**
* 检查 `connection.intent_message_content` 是否为 `true`
* 检查 `chat.guild_list` 和 `chat.channel_list` 的白名单配置
* 检查 `filters.ignore_bot_message` 是否意外屏蔽了目标用户

**无法连接 Discord 平台**

* Discord 服务在中国大陆无法直接访问，需要配置网络代理
* 推荐使用 TUN 模式代理，代理内核推荐使用 sing-box
* 检查代理是否正常工作

**语音功能不工作**

* 确认 `voice.enabled` 和 `connection.intent_voice_states` 均已设为 `true`
* 确认 Bot 拥有语音频道的 `View Channel`、`Connect`、`Speak` 权限
* 检查 TTS/STT 提供商的 API Key 是否有效
* 查看日志中是否有语音相关的错误信息

**子区（Thread）消息不响应**

* 检查 `chat.allow_thread_interaction` 是否为 `true`
* 检查 `chat.inherit_channel_permissions` 配置：如果父频道不在白名单中，继承开启时子区也会被过滤

---

---
url: /manual/deployment/docker.md
---

# 🐳 Docker 部署指南

Docker 就像一个大盒子，把 MaiBot 和所有它需要的东西都打包好，一键就能跑起来！

## 📋 准备工作

需要安装：

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)

## 🚀 5 分钟快速部署

### 1. 下载 MaiBot

```bash
git clone https://github.com/Mai-with-u/MaiBot.git
cd MaiBot
```

### 2. 一键启动！

```bash
docker compose up -d
```

第一次启动会自动生成配置文件，然后会停下来等你配置。

## 📦 Docker 里都有啥？

Docker 会同时启动几个服务，就像一个团队：

* **`core`** — MaiBot 核心，机器人的大脑 🧠
* **`napcat`** — QQ 连接器，让机器人能上 QQ 📱
* **`sqlite-web`** — 数据库工具，查看机器人记住的东西 📊

## ⚙️ 环境变量（高级用法）

### 核心服务设置

* **`TZ`** — 时区，例如 `Asia/Shanghai`
* **`EULA_AGREE`** — 跳过协议确认（高级用法，一般不用管）

### QQ 服务设置

* **`NAPCAT_UID`** — 用户 ID（一般用默认的）
* **`NAPCAT_GID`** — 用户组 ID（一般用默认的）

## 💾 数据保存在哪里？

Docker 会把重要数据保存在你电脑的这些位置：

### 机器人数据

* **配置文件**：`./docker-config/mmc/`（机器人设置）
* **运行数据**：`./data/MaiMBot/`（聊天记录、记忆等）
* **插件**：`./data/MaiMBot/plugins/`（额外功能）
* **日志**：`./data/MaiMBot/logs/`（运行记录）

### QQ 数据

* **QQ 配置**：`./docker-config/napcat/`
* **登录信息**：`./data/qq/`（下次启动不用重新登录）

## 🔌 端口说明

* **Web 界面** — 端口 18001，在浏览器打开 http://localhost:18001
* **NapCat 管理面板** — 端口 6099，NapCat 网页配置面板
* **数据库工具** — 端口 8120，查看机器人数据用的

## 🔗 连接 NapCat

`docker compose up -d` 只会把 MaiBot 和 NapCat 容器启动起来，还需要完成 NapCat 登录、WebSocket 和适配器配置，MaiBot 才能真正收到 QQ 消息。

1. 打开 NapCat 管理面板：`http://localhost:6099`
2. 登录 NapCat 管理面板。如果需要 token，请查看 `./docker-config/napcat/webui.json` 中的 `token` 字段。
3. 在 NapCat 管理面板中登录 QQ 小号。
4. 在 NapCat 的网络配置中启用 **正向 WebSocket** 或 **WebSocket 服务器**，监听端口一般用 `3001`。
5. 在 MaiBot WebUI 的插件管理中启用 **NapCat 适配器**，或编辑宿主机上的 `./data/MaiMBot/plugins/MaiBot-Napcat-Adapter/config.toml`：

```toml
[plugin]
enabled = true

[napcat_server]
host = "napcat"
port = 3001
token = ""
```

::: warning Docker 网络地址
在 Docker Compose 里，MaiBot 容器访问 NapCat 容器时应该使用服务名 `napcat`。因此适配器配置里的 `napcat_server.host` 通常填 `napcat`，不是 `127.0.0.1`。
`127.0.0.1` 在容器内只表示当前容器自己。
:::

### 群聊收不到消息

NapCat 适配器默认启用聊天名单过滤，且群聊默认是白名单模式。如果群号没有写进白名单，群消息会被适配器直接丢弃，看起来就像 NapCat 已连接但 MaiBot 没反应。

编辑 `./data/MaiMBot/plugins/MaiBot-Napcat-Adapter/config.toml` 的 `[chat]` 配置：

```toml
[chat]
enable_chat_list_filter = true
show_dropped_chat_list_messages = true
group_list_type = "whitelist"
group_list = ["你的QQ群号"]
```

如果只是本地测试，也可以临时关闭名单过滤：

```toml
[chat]
enable_chat_list_filter = false
```

改完后重启核心容器：

```bash
docker compose restart core
```

::: tip WebUI 配置位置
WebUI 的启用状态、监听地址和容器内端口现在都在 `./docker-config/mmc/bot_config.toml` 的 `[webui]` 配置段中设置，不再通过单独的 WebUI 配置文件或环境变量配置。
:::

默认情况下，`docker-compose.yml` 会把宿主机的 `18001` 端口映射到容器内的 `8001` 端口：

```yaml
ports:
  - "18001:8001"
```

Docker 部署时，建议确认 `./docker-config/mmc/bot_config.toml` 中的 WebUI 配置如下：

```toml
[webui]
enabled = true
host = "0.0.0.0"
port = 8001
```

::: warning ⚠️ host 必须改为 0.0.0.0
WebUI 的 `host` 默认值是 `127.0.0.1`（仅监听本地回环地址），**在 Docker 容器内这意味着只有容器自身能访问 WebUI，宿主机无法通过端口映射访问到它**。Docker 部署时务必将 `host` 改为 `0.0.0.0`，否则浏览器打不开 WebUI。
:::

* `host` 是 WebUI 在容器内绑定的地址。Docker 部署时建议使用 `0.0.0.0`，这样宿主机端口映射才能访问到 WebUI。
* `port` 是 WebUI 在容器内监听的端口，需要和 `docker-compose.yml` 端口映射右侧保持一致。例如 `18001:8001` 中的 `8001`。
* 如果你想修改浏览器访问端口，通常只需要改端口映射左侧。例如把 `18001:8001` 改成 `28001:8001` 后，通过 `http://localhost:28001` 访问。

## 📋 完整步骤（一步一步来）

```bash
# 1. 下载
git clone https://github.com/Mai-with-u/MaiBot.git
cd MaiBot

# 2. 首次启动（会生成配置文件）
docker compose up -d

# 3. 改配置（重要！）
# 打开 ./docker-config/mmc/bot_config.toml 填 QQ 号
# WebUI 配置也在 ./docker-config/mmc/bot_config.toml 的 [webui] 段
# 打开 ./docker-config/mmc/model_config.toml 填 API 密钥
# 打开 http://localhost:6099 登录 NapCat，并启用正向 WebSocket
# 启用 NapCat 适配器，并把适配器的 napcat_server.host 设为 napcat
# 群聊要把群号加入 NapCat 适配器的 group_list，或关闭聊天名单过滤

# 4. 重启让配置生效
docker compose restart core

# 5. 看日志
docker compose logs -f core
```

## 🔧 常见问题

### 容器启动就退出？

看日志找原因：

```bash
docker compose logs core
```

90% 是因为：

* 配置文件没填对（特别是 API 密钥）
* QQ 号填错了

### 内存不够？

Docker 比较吃内存，建议至少 2GB 空闲内存。

### 想停止机器人？

```bash
docker compose down
```

### 想重新启动？

```bash
docker compose restart
```

---

---
url: /manual/faq/EULA.md
---

# **MaiBot最终用户许可协议**

**版本：V1.3**
**更新日期：2026年05月30日**
**生效日期：2026年05月30日**
**适用的MaiBot版本号：所有版本**

**2025© MaiBot项目团队**

***

## 一、一般条款

**1.1** MaiBot项目（包括MaiBot的源代码、可执行文件、文档，以及其它在本协议中所列出的文件）（以下简称“本项目”）是由开发者及贡献者（以下简称“项目团队”）共同维护，为用户提供自动回复功能的机器人代码项目。以下最终用户许可协议（EULA，以下简称“本协议”）是用户（以下简称“您”）与项目团队之间关于使用本项目所订立的合同条件。

**1.2** 在运行或使用本项目之前，您**必须阅读并同意本协议的所有条款**。未成年人或其它无/不完全民事行为能力责任人请**在监护人的陪同下**阅读并同意本协议。如果您不同意，则不得运行或使用本项目。在这种情况下，您应立即从您的设备上卸载或删除本项目及其所有副本。

## 二、许可授权

### 源代码许可

**2.1** 您**了解**除本项目子目录、第三方组件或随附文件另有许可证声明的部分外，本项目主程序源代码基于GPLv3（GNU通用公共许可证第三版）开源协议发布。您**可以自由使用、修改、分发**相应源代码，但**必须遵守**对应开源许可证的要求。详细内容请参阅项目仓库中的LICENSE文件、相关子目录内的LICENSE文件及其它许可证声明文件。

**2.2** 您**了解**本项目可能包含独立子项目、第三方开源代码或经额外授权纳入本项目的代码；这些内容的许可证可能与GPLv3许可证不同，或存在特定适用范围。您**同意**在使用、修改、分发这些内容时**遵守**相应的许可证要求。

### 输入输出内容授权

**2.3** 您**了解**本项目是使用您的配置信息、提交的指令（以下简称“输入内容”）和生成的内容（以下简称“输出内容”）构建请求发送到第三方生成回复的机器人项目。
**2.4** 您**授权**本项目使用您的输入和输出内容按照项目的隐私政策用于以下行为：

* 调用第三方API生成回复；
* 调用第三方API用于构建本项目专用的存储于您使用的数据库中的知识库和记忆库；
* 调用第三方开发的插件系统功能；
* 收集并记录本项目专用的存储于您使用的设备中的日志；
* 在遥测功能启用时，向项目团队的遥测服务发送有限的运行状态与使用统计数据，用于版本分布、稳定性分析、容量规划和功能改进。遥测数据的具体范围、关闭方式、保存期限和处理规则以本项目隐私条款为准。

**2.5** 您**了解**本项目的源代码中包含第三方API的调用代码，这些API的使用可能受到第三方的服务条款和隐私政策的约束。在使用这些API时，您**必须遵守**相应的服务条款。

**2.6** 项目团队**不对**第三方API的服务质量、稳定性、准确性、安全性负责，亦**不对**第三方API的服务变更、终止、限制等行为负责。

## 三、用户行为

**3.1** 您**了解**本项目会将您的配置信息、输入指令和生成内容发送到第三方，您**不应**在输入指令和生成内容中包含以下内容：

* 涉及任何国家或地区秘密、商业秘密或其他可能会对国家或地区安全或者公共利益造成不利影响的数据；
* 涉及个人隐私、个人信息或其他敏感信息的数据；
* 任何侵犯他人合法权益的内容；
* 任何违反国家或地区法律法规、政策规定的内容；

**3.2** 您**不应**将本项目用于以下用途：

* 违反任何国家或地区法律法规、政策规定的行为；

**3.3** 您**应当**自行确保您被存储在本项目的知识库、记忆库和日志中的输入和输出内容的合法性与合规性以及存储行为的合法性与合规性。您需**自行承担**由此产生的任何法律责任。

**3.4** 对于第三方插件的使用，您**不应**：

* 安装、使用任何来源不明或未经验证的第三方插件；
* 使用任何违反法律法规、政策规定或第三方平台规则的第三方插件；

**3.5** 您**应当**自行确保您安装和使用的第三方插件的合法性与合规性以及安装和使用行为的合法性与合规性。您需**自行承担**由此产生的任何法律责任。

**3.6** 由于本项目会将您的输入指令和生成内容发送到第三方，当您将本项目用于第三方交流环境（如与除您以外的人私聊、群聊、论坛、直播等）时，您**应当**事先明确告知其他交流参与者本项目的使用情况，包括但不限于：

* 本项目的输出内容是由人工智能生成的；
* 本项目会将交流内容发送到第三方；
* 本项目的隐私政策和用户行为要求；

您需**自行承担**由此产生的任何后果和法律责任。

**3.7** 项目团队**不鼓励**也**不支持**将本项目用于商业用途，但若您确实需要将本项目用于商业用途，您**应当**标明项目地址（如“本项目由MaiBot(<https://github.com/Mai-with-u/MaiBot>)驱动”），并**自行承担**由此产生的任何法律责任。

## 四、免责条款

**4.1** 本项目的输出内容依赖第三方API，**不受**项目团队控制，亦**不代表**项目团队的观点。

**4.2** 除本协议条目2.4提到的隐私政策之外，项目团队**不会**对您提供任何形式的担保，亦**不对**使用本项目的造成的任何直接或间接后果负责。

**4.3** 关于第三方插件，项目团队**声明**：

* 项目团队**不对**任何第三方插件的功能、安全性、稳定性、合规性或适用性提供任何形式的保证或担保；
* 项目团队**不对**因使用第三方插件而产生的任何直接或间接后果承担责任；
* 项目团队**不对**第三方插件的质量问题、技术支持、bug修复等事宜负责。如有相关问题，应**直接联系插件开发者**；

## 五、其他条款

**5.1** 项目团队有权**随时修改本协议的条款**，但**无义务**通知您。修改后的协议将在本项目的新版本中推送，您应定期检查本协议的最新版本。

**5.2** 项目团队**保留**本协议的最终解释权。

## 附录：其他重要须知

### 一、风险提示

**附录1.1** 隐私安全风险

* 本项目会将您的配置信息、输入指令和生成内容发送到第三方API，而这些API的服务质量、稳定性、准确性、安全性不受项目团队控制。
* 本项目会收集您的输入和输出内容，用于构建本项目专用的知识库和记忆库，以提高回复的准确性和连贯性。

**因此，为了保障您的隐私信息安全，请注意以下事项：**

* 避免在涉及个人隐私、个人信息或其他敏感信息的环境中使用本项目；
* 避免在不可信的环境中使用本项目；

**附录1.2** 精神健康风险

本项目仅为工具型机器人，不具备情感交互能力。建议用户：

* 避免过度依赖AI回复处理现实问题或情绪困扰；
* 如感到心理不适，请及时寻求专业心理咨询服务；
* 如遇心理困扰，请寻求专业帮助（全国心理援助热线：12355）；

**附录1.3** 第三方插件风险

本项目的插件系统允许加载第三方开发的插件，这可能带来以下风险：

* **安全风险**：第三方插件可能包含恶意代码、安全漏洞或未知的安全威胁；
* **稳定性风险**：插件可能导致系统崩溃、性能下降或功能异常；
* **隐私风险**：插件可能收集、传输或泄露您的个人信息和数据；
* **合规风险**：插件的功能或行为可能违反相关法律法规或平台规则；
* **兼容性风险**：插件可能与主程序或其他插件产生冲突；

**因此，在使用第三方插件时，请务必：**

* 仅从可信来源获取和安装插件；
* 在安装前仔细了解插件的功能、权限和开发者信息；
* 定期检查和更新已安装的插件；
* 如发现插件异常行为，请立即停止使用并卸载；

### 二、其他

**附录2.1** 争议解决

* 本协议适用中国法律，争议提交相关地区法院管辖；
* 若因GPLv3许可产生纠纷，以许可证官方解释为准。

---

---
url: /develop/plugin-dev/hooks.md
---

# Hook 处理器

`@HookHandler` 是 MaiBot 插件系统中用于订阅**命名 Hook 点**的组件装饰器。主程序在关键执行点触发命名 Hook，所有订阅该 Hook 的插件处理器按固定规则调度执行，从而实现消息拦截、改写和观察。

::: warning WorkflowStep 已移除
SDK 2.0 中 `WorkflowStep` 已被 `@HookHandler` 取代。旧代码仍在使用 `WorkflowStep` 时会在运行时抛出 `RuntimeError`，这是一个不向后兼容的更改，必须迁移到 `@HookHandler`。
:::

## 装饰器签名

```python
from maibot_sdk import HookHandler
from maibot_sdk.types import HookMode, HookOrder, ErrorPolicy

@HookHandler(
    hook: str,                              # 订阅的命名 Hook 名称（必填）
    *,
    name: str = "",                         # 组件名称，留空时使用方法名
    description: str = "",                  # 组件描述
    mode: HookMode = HookMode.BLOCKING,     # 处理模式
    order: HookOrder = HookOrder.NORMAL,    # 同一模式内的顺序槽位
    timeout_ms: int = 0,                    # 处理器超时（毫秒），0 = 使用 Hook 默认值
    error_policy: ErrorPolicy = ErrorPolicy.SKIP,  # 异常处理策略
    **metadata,                             # 额外元数据
)
```

## 处理模式

### BLOCKING（阻塞模式）

* 串行执行，**可以修改**传入的 `kwargs`
* 返回 `modified_kwargs` 可以更新后续处理器接收的参数
* 返回 `action: "abort"` 可以终止整个 Hook 调用链
* 适合需要拦截或改写消息的场景

### OBSERVE（观察模式）

* 后台并发执行，**只读**旁路观察
* 不参与主流程控制，返回的 `modified_kwargs` 和 `abort` 请求会被忽略
* 适合日志记录、数据分析等不影响主流程的场景

```python
class HookMode(str, Enum):
    BLOCKING = "blocking"  # 同步等待，可修改数据
    OBSERVE = "observe"    # 异步观察，不可修改
```

## 顺序槽位

同一模式内的处理器按 `order` 排序执行：

* **`HookOrder.EARLY`** — 优先执行，适合前置拦截
* **`HookOrder.NORMAL`** — 默认顺序
* **`HookOrder.LATE`** — 延后执行，适合补充处理

## 异常处理策略

当处理器抛出异常时，根据 `error_policy` 决定后续行为：

* **`ErrorPolicy.ABORT`** — 异常时终止当前 Hook 调用
* **`ErrorPolicy.SKIP`** — 记录日志，跳过此处理器继续（**默认**）
* **`ErrorPolicy.LOG`** — 记录日志，并继续执行后续 hook

## 调度顺序

Hook 处理器按以下规则全局排序：

1. **模式优先**：`blocking` 先于 `observe`
2. **顺序槽位**：`early` → `normal` → `late`
3. **来源优先**：内置插件先于第三方插件
4. **插件 ID**：按字典序排列
5. **处理器名称**：按字典序排列

## 基本用法

### 阻塞模式示例：拦截并修改消息

```python
from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder, ErrorPolicy


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "chat.receive.before_process",
        name="message_filter",
        description="过滤入站消息",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.ABORT,
    )
    async def handle_message_filter(self, **kwargs):
        message = kwargs.get("message", {})
        # 过滤逻辑：如果消息包含敏感词，终止处理链
        raw_message = message.get("raw_message", "")
        if "违禁词" in raw_message:
            self.ctx.logger.info("消息被过滤: %s", raw_message)
            return {"action": "abort"}

        # 修改消息内容后继续
        kwargs["message"]["filtered"] = True
        return {"action": "continue", "modified_kwargs": kwargs}
```

### 观察模式示例：日志记录

```python
from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder


class LogPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("日志插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("日志插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "chat.receive.after_process",
        name="message_logger",
        description="记录所有入站消息",
        mode=HookMode.OBSERVE,
        order=HookOrder.LATE,
    )
    async def observe_message(self, **kwargs):
        message = kwargs.get("message", {})
        self.ctx.logger.info(
            "观察到消息: user=%s, text=%s",
            message.get("user_id", "unknown"),
            message.get("raw_message", ""),
        )
        # observe 模式返回值会被忽略
```

### 阻塞模式示例：修改发送参数

```python
from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder


class SendInterceptorPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("发送拦截插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("发送拦截插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "send_service.before_send",
        name="send_modifier",
        description="修改发送参数",
        mode=HookMode.BLOCKING,
        order=HookOrder.NORMAL,
        timeout_ms=5000,
    )
    async def modify_send_params(self, **kwargs):
        # 禁用打字效果，强制开启发送日志
        kwargs["typing"] = False
        kwargs["show_log"] = True
        return {"action": "continue", "modified_kwargs": kwargs}
```

## 内置 Hook 清单

以下为 Host 运行时中心表注册的全部 Hook 点。每个 Hook 注明是否允许 abort（中止调用链）和是否允许改参（修改后续处理器接收的 kwargs）。

### 聊天消息链

* **`chat.receive.before_process`** — 入站消息执行 `SessionMessage.process()` 前 — 允许 abort ✅ · 允许改参 ✅
* **`chat.receive.after_process`** — 入站消息轻量预处理完成后 — 允许 abort ✅ · 允许改参 ✅

### 命令执行链

* **`chat.command.before_execute`** — 命令匹配成功、正式执行前 — 允许 abort ✅ · 允许改参 ✅
* **`chat.command.after_execute`** — 命令执行结束后 — 允许 abort ❌ · 允许改参 ✅

### 表情包链

* **`emoji.maisaka.before_select`** — Maisaka 选择表情前 — 允许 abort ✅ · 允许改参 ✅
* **`emoji.maisaka.after_select`** — Maisaka 选出表情后 — 允许 abort ✅ · 允许改参 ✅
* **`emoji.register.after_build_description`** — 表情包描述生成完成后 — 允许 abort ✅ · 允许改参 ✅
* **`emoji.register.after_build_emotion`** — 表情包情绪标签生成完成后 — 允许 abort ✅ · 允许改参 ✅

### 黑话（Jargon）链

* **`jargon.query.before_search`** — Maisaka 黑话查询前 — 允许 abort ✅ · 允许改参 ✅
* **`jargon.query.after_search`** — Maisaka 黑话查询完成后 — 允许 abort ✅ · 允许改参 ✅
* **`jargon.extract.before_persist`** — 黑话条目写库前 — 允许 abort ✅ · 允许改参 ✅
* **`jargon.inference.before_finalize`** — 黑话推断结果写回前 — 允许 abort ✅ · 允许改参 ✅

### 表达方式（Expression）链

* **`expression.select.before_select`** — 表达方式选择前 — 允许 abort ✅ · 允许改参 ✅
* **`expression.select.after_selection`** — 表达方式选择完成后 — 允许 abort ✅ · 允许改参 ✅
* **`expression.learn.after_extract`** — 表达方式学习解析候选后 — 允许 abort ✅ · 允许改参 ✅
* **`expression.learn.before_upsert`** — 表达方式写库前 — 允许 abort ✅ · 允许改参 ✅

### 发送服务链

* **`send_service.after_build_message`** — 出站 `SessionMessage` 构建完成后 — 允许 abort ✅ · 允许改参 ✅
* **`send_service.before_send`** — 调用 Platform IO 发送前 — 允许 abort ✅ · 允许改参 ✅
* **`send_service.after_send`** — 发送流程完成后 — 允许 abort ❌ · 允许改参 ❌

### Maisaka 规划器链

* **`maisaka.planner.before_request`** — Maisaka 规划器请求模型前 — 允许 abort ❌ · 允许改参 ✅
* **`maisaka.planner.after_response`** — Maisaka 收到模型响应后 — 允许 abort ❌ · 允许改参 ✅

### Maisaka 回复器链

* **`maisaka.replyer.before_request`** — Maisaka replyer 请求模型前；可读取或改写本次 `reply_tool_args` — 允许 abort ❌ · 允许改参 ✅
* **`maisaka.replyer.before_model_request`** — Maisaka replyer 构造完最终 `messages` 后、请求模型前；可改写实际发送给模型的消息列表 — 允许 abort ❌ · 允许改参 ✅
* **`maisaka.replyer.after_response`** — Maisaka replyer 收到模型响应后；可改写回复或要求重生成 — 允许 abort ❌ · 允许改参 ✅

`reply_tool_args` 会在表达方式选择链、`maisaka.replyer.before_request` 和 `maisaka.replyer.after_response` 中保持可见。它包含 reply 工具里除 `msg_id`、`set_quote`、`reference_info` 外的额外参数；`before_request` 返回的 `reply_tool_args` 修改会继续传递给后续 replyer hook。

#### 在 replyer 请求前切换模型或追加提示词

`maisaka.replyer.before_request` 是 replyer 真正请求模型前的最后一个可改写点。阻塞模式处理器可以修改以下字段：

* **`task_name`** `str` — 本次 replyer 请求使用的任务名。修改后会用该任务的默认模型池和生成参数。
* **`model_name`** `str` — 本次 replyer 请求指定的具体模型名称，必须存在于 `model_config.toml` 的 `[[models]]` 中。指定后只尝试该模型一次，不再按任务模型池轮换。
* **`extra_prompt`** `str` — 追加到本次 replyer prompt 的额外回复要求。
* **`reference_info`** `str` — 本次 reply 工具传入的引用信息，可以被改写。
* **`reply_tool_args`** `dict` — reply 工具额外参数，修改后会传给后续 replyer hook。

`model_name` 是具体模型名，不是 task 名；如果只想切换到另一个任务的模型池，修改 `task_name` 即可。如果同时设置 `task_name` 和 `model_name`，任务提供温度、token 上限、超时等生成参数，`model_name` 指定实际调用的模型。

如果需要改写 replyer 真正发给模型的消息列表，请使用 `maisaka.replyer.before_model_request`。该 Hook 会在 replyer 已经根据当前模型能力构造好 `messages` 后触发，阻塞模式处理器可以返回新的 `messages`；适合在 `system` 后插入一条合成的第一条 `user` 消息、做临时提示词实验或记录最终请求体。这个 Hook 只改写本次临时 LLM 请求，不会回写聊天历史，也不会影响中期记忆插入。

常见用法是先通过 `maisaka.planner.before_request` 给内置 `reply` 工具追加参数 schema，让 planner 可以在调用 reply 工具时填入参数；随后在 `maisaka.replyer.before_request` 中读取 `reply_tool_args` 并路由模型：

```python
from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode


class ThinkingLevelPlugin(MaiBotPlugin):
    @HookHandler("maisaka.planner.before_request", mode=HookMode.BLOCKING)
    async def add_reply_tool_param(self, **kwargs):
        for tool in kwargs.get("tool_definitions", []):
            function = tool.get("function", {})
            if function.get("name") != "reply":
                continue

            parameters = function.setdefault("parameters", {})
            properties = parameters.setdefault("properties", {})
            properties["thinking_level"] = {
                "type": "string",
                "enum": ["normal", "deep"],
                "description": "回复时的思考强度。normal 表示常规回复，deep 表示使用更强模型并更细致分析。",
            }
        return {"action": "continue", "modified_kwargs": kwargs}

    @HookHandler("maisaka.replyer.before_request", mode=HookMode.BLOCKING)
    async def route_replyer_model(self, **kwargs):
        reply_tool_args = kwargs.get("reply_tool_args", {})
        if reply_tool_args.get("thinking_level") == "deep":
            kwargs["model_name"] = "your-deep-model-name"
            kwargs["extra_prompt"] = "请更细致地理解上下文后再回复。"

        return {"action": "continue", "modified_kwargs": kwargs}
```

只新增或修改 hook 名本身通常不需要改插件 SDK 运行时代码：`@HookHandler` 接收的是字符串 hook 名，是否可用由 Host 注册的 HookSpec 校验。只有需要 SDK 常量、类型提示、文档或示例同步时，才需要更新 SDK 侧内容。

## Host 校验规则

Host 在插件注册阶段会对 `@HookHandler` 声明进行校验，不合法时插件直接注册失败（而非"加载成功但 Hook 不生效"的半成功状态）。校验规则如下：

1. **Hook 名称必须已注册**：`hook` 参数必须是上述内置 Hook 清单中已存在的名称。传入未注册的 Hook 名称会导致注册失败。
2. **mode 必须符合 Hook 的能力约束**：Host 会检查 `mode` 是否与该 Hook 点的能力兼容（例如，仅允许改参的 Hook 不能以不可改参的模式运行）。
3. **error\_policy=ABORT 须 Hook 允许 abort**：只有当该 Hook 的"允许 abort"列为"是"时，才能声明 `error_policy=ErrorPolicy.ABORT`。对于不允许 abort 的 Hook 声明 `ABORT` 策略将导致注册失败。

运行时 Host 会将这份 Hook 清单公开给 WebUI 后端路由 `/plugins/runtime/hooks`，便于面板或调试工具直接读取动态中心表。

### 表达方式选择链

* **`expression.select.before_select`** — 表达候选池载入后、默认选择结果生成前；可改写 `candidates`、`max_num` 或 `abort` 跳过本次选择
* **`expression.select.after_selection`** — 默认选择结果生成后；可改写 `selected_expression_ids` 或 `selected_expressions`

`before_select` 会收到 `chat_id`、`session_id`、`chat_info`、`chat_history`、`reply_message`、`reply_tool_args`、`target_message`、`reply_reason`、`max_num`、`think_level`、`candidates`。`reply_tool_args` 包含 reply 工具里除 `msg_id`、`set_quote`、`reference_info` 外的额外参数。`after_selection` 在此基础上额外包含 `selected_expression_ids` 与 `selected_expressions`。

```python
@HookHandler("expression.select.after_selection", mode=HookMode.BLOCKING)
async def replace_expression_selection(self, **kwargs):
    strategy = kwargs.get("reply_tool_args", {}).get("expression_strategy")
    candidates = kwargs.get("candidates", [])
    selected_ids = [item["id"] for item in candidates[:1]]
    kwargs["selected_expression_ids"] = selected_ids
    return {"action": "continue", "modified_kwargs": kwargs}
```

## 处理器返回值

阻塞模式的处理器可以返回字典来控制后续流程：

* **`action`** `str` — `"continue"` 继续调用链，`"abort"` 终止调用链
* **`modified_kwargs`** `dict` — 修改后的参数，将传递给后续处理器

观察模式的处理器返回值会被忽略，不需要返回控制字典。

## Hook 分发流程

```mermaid
sequenceDiagram
    participant Host as 主程序
    participant HD as HookDispatcher
    participant B1 as Blocking 处理器 1
    participant B2 as Blocking 处理器 2
    participant O1 as Observe 处理器

    Host->>HD: 触发 Hook(hook_name, kwargs)
    HD->>HD: 收集并排序所有处理器
    HD->>B1: 串行执行(kwargs)
    B1-->>HD: {action: "continue", modified_kwargs: ...}
    HD->>B2: 串行执行(modified_kwargs)
    B2-->>HD: {action: "continue", ...}
    HD--)O1: 后台并发执行(kwargs)
    HD-->>Host: 返回最终结果
```

## 迁移指南：WorkflowStep → HookHandler

* **`@WorkflowStep(stage="pre_process")`** → **`@HookHandler("chat.receive.before_process")`** — 使用命名 Hook 点代替固定 stage
* **`blocking=True`** → **`mode=HookMode.BLOCKING`** — 参数名变更
* **`observe=True`** → **`mode=HookMode.OBSERVE`** — 参数名变更
* **`priority=10`** → **`order=HookOrder.EARLY`** — 改为三档枚举

::: danger
直接调用 `WorkflowStep(...)` 现在会立即抛出 `RuntimeError`，不存在兼容映射。必须手动将所有 `@WorkflowStep` 替换为 `@HookHandler`。
:::

```python
# 旧代码（SDK 1.x）— 不再可用
@WorkflowStep(stage="pre_process", blocking=True)
async def on_pre_process(self, **kwargs):
    ...

# 新代码（SDK 2.0）
@HookHandler("chat.receive.before_process", mode=HookMode.BLOCKING)
async def on_pre_process(self, **kwargs):
    ...
```

---

---
url: /develop/plugin-dev/llmprovider.md
---

# LLMProvider 组件

`@LLMProvider` 用于声明插件提供新的 LLM Provider `client_type`。主程序会将该 `client_type` 注册到 LLM 客户端注册表中，因此现有 `LLMService` 和模型任务配置不需要改调用方式——只要模型配置里的 `api_providers[].client_type` 指向插件声明的值，请求就会通过插件 Provider 发起。

::: warning 双重声明必须一致
LLM Provider 必须同时满足两处声明，缺一不可：

1. `_manifest.json` 顶层 `llm_providers` 中静态声明 `client_type`
2. 插件代码中使用 `@LLMProvider("同一个 client_type")` 修饰处理方法

Runner 会校验 manifest 与装饰器收集结果完全一致。任意一边漏写、拼写不一致或同一插件内重复声明，插件都会拒绝加载。不同插件声明同一个 `client_type` 时，冲突双方都会被阻止加载。
:::

## 装饰器签名

```python
from maibot_sdk import LLMProvider

@LLMProvider(
    client_type: str,          # 客户端类型标识（必填）
    *,
    name: str = "",            # Provider 展示名称
    description: str = "",     # Provider 描述
    version: str = "1.0.0",    # Provider 实现版本
    **metadata,                # 额外元数据
)
```

### 参数说明

* **`client_type`** `str` · 必填 — 客户端类型标识，对应模型配置中的 `api_providers[].client_type`。不能为空
* **`name`** `str` · 默认 `""` — Provider 展示名称。留空时使用 `client_type`
* **`description`** `str` · 默认 `""` — Provider 描述信息
* **`version`** `str` · 默认 `"1.0.0"` — Provider 实现版本号
* **`**metadata`** `Any` — 额外元数据键值对

## Manifest 声明

`_manifest.json` 顶层必须包含 `llm_providers` 数组，与代码中的 `@LLMProvider` 一一对应：

```json
{
  "llm_providers": [
    {
      "client_type": "example.provider",
      "name": "Example Provider",
      "description": "示例 LLM Provider",
      "version": "1.0.0"
    }
  ]
}
```

### llm\_providers 字段说明

* **`client_type`** `str` · 必填 — Provider 客户端类型，必须与模型配置 `api_providers[].client_type` 一致
* **`name`** `str` · 默认 `""` — Provider 展示名称
* **`description`** `str` · 默认 `""` — Provider 描述
* **`version`** `str` · 默认 `"1.0.0"` — Provider 实现版本

::: danger
不要在 manifest 的 `llm_providers` 中写 `handler_name` 或 `metadata`——处理函数由 `@LLMProvider` 装饰器自动收集，不需要手动指定。
:::

## Operation 类型

处理方法通过 `operation` 参数区分请求类型。三种 operation 分别对应不同的 LLM 能力：

* **`response`** — LLM 文本/工具响应。主要请求字段：`message_list`、`tool_options`、`max_tokens`、`temperature`、`response_format`、`extra_params`、`model_info`、`api_provider`。返回字段：`content` / `response`、`reasoning_content`、`tool_calls`、`usage`
* **`embedding`** — 文本向量化。主要请求字段：`embedding_input`、`extra_params`、`model_info`、`api_provider`。返回字段：`embedding`
* **`audio_transcription`** — 语音识别。主要请求字段：`audio_base64`、`max_tokens`、`extra_params`、`model_info`、`api_provider`。返回字段：`content`

三种 operation 的请求中都会包含以下公共字段：

* **`model_info`** `dict` — 当前请求的模型信息
* **`api_provider`** `dict` — 当前请求的 API Provider 配置
* **`extra_params`** `dict` — 额外参数

## 请求与返回字段

### 处理方法参数

* **`operation`** `str` — 请求类型：`response`、`embedding`、`audio_transcription`
* **`request`** `dict[str, Any]` — Host 序列化后的请求内容

### 返回值字段

返回值必须是可序列化字典。Host 会识别以下字段并恢复为统一响应：

* **`content` / `response`** `str` — 文本响应或音频转写文本
* **`reasoning_content` / `reasoning`** `str` — 推理内容
* **`embedding`** `list[float]` — 嵌入向量
* **`tool_calls`** `list` — 工具调用快照
* **`usage`** `dict` — token 使用量字典
* **`raw_data`** `dict` — 原始响应数据

## 基本用法

### 方式一：手动分发（简单场景）

在处理方法内通过 `if/elif` 判断 `operation` 类型分别处理：

```python
from typing import Any

from maibot_sdk import LLMProvider, MaiBotPlugin


class MyLLMPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("my.provider", name="My Provider", description="自定义 LLM Provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        if operation == "response":
            return {"content": "你好，我来自插件 Provider"}
        if operation == "embedding":
            return {"embedding": [0.0, 0.1, 0.2]}
        if operation == "audio_transcription":
            return {"content": "音频转写结果"}
        raise ValueError(f"不支持的 LLM Provider 操作类型: {operation}")


def create_plugin():
    return MyLLMPlugin()
```

### 方式二：LLMProviderBase 基类（推荐，逻辑较多时）

继承 `LLMProviderBase`，将分发逻辑交给基类的 `dispatch()` 方法。子类只需实现关心的 operation 方法，未实现的方法会抛出 `NotImplementedError`：

```python
from typing import Any

from maibot_sdk import LLMProvider, LLMProviderBase, MaiBotPlugin


class MyProvider(LLMProviderBase):
    """自定义 Provider，只实现 response 能力。"""

    async def get_response(self, request: dict[str, Any]) -> dict[str, Any]:
        # request 包含 message_list、tool_options、model_info 等
        return {"content": "来自 Provider 类的响应"}


class MyLLMPlugin(MaiBotPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.provider = MyProvider()

    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("my.provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self.provider.dispatch(operation, request)


def create_plugin():
    return MyLLMPlugin()
```

`LLMProviderBase` 提供以下方法供子类覆写：

* **`get_response()`** · operation `response` — 生成文本或多模态响应（抽象方法，必须实现）
* **`get_embedding()`** · operation `embedding` — 生成文本嵌入（默认抛出 `NotImplementedError`）
* **`get_audio_transcriptions()`** · operation `audio_transcription` — 生成音频转写（默认抛出 `NotImplementedError`）

::: tip
`LLMProviderBase` 只是推荐基类，不参与注册。真正的注册入口始终是 `@LLMProvider` 装饰器。
:::

## 完整示例

下面是一个完整的最小可用插件，包含 manifest 声明和 Python 代码。

**\_manifest.json**：

```json
{
  "id": "com.example.llm-provider",
  "name": "Example LLM Provider",
  "version": "1.0.0",
  "description": "示例 LLM Provider 插件",
  "author": "example",
  "llm_providers": [
    {
      "client_type": "example.provider",
      "name": "Example Provider",
      "description": "示例 LLM Provider",
      "version": "1.0.0"
    }
  ]
}
```

**main.py**：

```python
from typing import Any

from maibot_sdk import LLMProvider, LLMProviderBase, MaiBotPlugin


class ExampleProvider(LLMProviderBase):
    """示例 Provider，实现 response 和 embedding 两种能力。"""

    async def get_response(self, request: dict[str, Any]) -> dict[str, Any]:
        model_info = request.get("model_info", {})
        message_list = request.get("message_list", [])
        # 此处接入实际的 LLM API
        return {
            "content": "来自 example.provider 的响应",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    async def get_embedding(self, request: dict[str, Any]) -> dict[str, Any]:
        embedding_input = request.get("embedding_input", "")
        # 此处接入实际的 Embedding API
        return {"embedding": [0.1, 0.2, 0.3]}


class ExampleLLMPlugin(MaiBotPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.provider = ExampleProvider()

    async def on_load(self) -> None:
        self.ctx.logger.info("Example LLM Provider 插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("Example LLM Provider 插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("example.provider", name="Example Provider", description="示例 LLM Provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self.provider.dispatch(operation, request)


def create_plugin():
    return ExampleLLMPlugin()
```

## 卸载与回退

当 Provider 插件卸载、禁用或热重载失败时，Host 会注销该插件拥有的 `client_type`。此后新请求会按主程序的模型回退策略尝试下一个可用模型。

::: info
插件 Provider 暂不支持 Host 侧自定义流式处理器或响应解析器。
:::

---

---
url: /changelog/v1-0-0.md
description: MaiBot 1.0.0 的用户侧更新总览，涵盖 Maisaka、A_Memorix、Dashboard、插件、多模态和稳定性改进。
---

# MaiBot 1.0.0 更新专题

MaiBot 1.0.0 是一次面向长期使用体验的系统性升级。它不只是在原有功能上增加开关，而是把回复、记忆、插件、WebUI、图片资源和调试观测重新串成了一套更完整的日常使用流程。

![MaiBot 1.0.0 更新总览](/images/releases/1.0.0-overview.svg)

## 这次升级改变了什么

1.0.0 之后，麦麦更像一个能持续工作的聊天智能体。她会根据聊天场景决定是否说话，能在长对话里保留摘要，能把图片和工具返回内容继续带入上下文，也能通过长期记忆和人物画像理解更稳定的背景信息。

对使用者来说，最直接的变化是：回复更有节奏，记忆更容易维护，WebUI 能管理的范围更完整，插件和图片资源也更不容易成为长期运行时的负担。

```mermaid
flowchart LR
  message["聊天消息"] --> timing["判断时机"]
  timing --> plan["规划动作"]
  plan --> context["检索记忆与上下文"]
  context --> reply["组织回复"]
  reply --> feedback["反馈与沉淀"]
  feedback --> memory["长期记忆与行为经验"]
  memory --> context
```

## Maisaka 回复核心

![Maisaka 新回复链路](/images/releases/1.0.0-maisaka.svg)

Maisaka 是 1.0.0 中最核心的变化。麦麦收到消息后，会先根据聊天节奏和上下文判断是否需要行动，再决定是等待、回复、调用工具、发送图片，还是保持安静。

**回复更像一次连续交流**\
群聊、私聊和 WebUI 本地聊天的回复链路进一步统一。引用回复、等待、打字节奏、不回复策略和回复分割都经过重新整理，减少突然插话、空回复和无意义行动。

**长对话不容易断片**\
中期记忆会把较长的聊天压缩成摘要，并在后续上下文中继续可用。对于持续数小时甚至更长的聊天，麦麦更容易保留前面讨论过的关键内容。

**多模态内容能继续参与对话**\
图片、转发消息、复杂消息和工具返回的媒体内容会更稳定地进入上下文。模型是否携带图片，会按配置和模型能力判断，减少非视觉模型误收图片导致的请求问题。

## A\_Memorix 记忆系统

![A\_Memorix 记忆网络](/images/releases/1.0.0-memory.svg)

A\_Memorix 在 1.0.0 中成为长期记忆主线。新的记忆系统不再只保存零散文本，而是把段落、实体、关系、来源、向量和图谱放在同一套结构里。

**记忆有来源，也能被纠错**\
人物画像、事实、关系和知识片段会尽量保留来源证据。WebUI 中可以查看证据链和纠错历史，发现过时或错误记忆时，也能通过纠错闭环让后续检索更准确。

**检索更重视场景相关性**\
长期记忆检索融合向量、图关系、BM25、PageRank 和阈值过滤等方式，目标是减少无关记忆进入回复上下文，让麦麦更常想起“这次聊天真正需要的内容”。

**知识库维护更适合长期使用**\
历史聊天总结可以导入长期记忆，网页和文档导入也更稳定。删除知识来源、重新导入、失效清理和批量导入的流程更完整，适合把麦麦作为长期陪伴或知识助手来维护。

## Dashboard 新工作台

![Dashboard 统一工作台截图](/images/releases/1.0.0-dashboard.webp)

1.0.0 的 Dashboard 不只是一个设置页，而是新的管理工作台。聊天、配置、插件、记忆、知识库、统计、监控、日志、推理过程和系统设置都进入了统一入口。

WebUI 的主题、侧边栏、按钮、表单、弹窗、移动端布局和长内容展示也进行了多轮打磨。对普通用户来说，它更像一个能日常打开使用的控制台；对排查问题的人来说，它能更快告诉你“麦麦刚才为什么这么做”。

## 插件、MCP 与工具

插件系统在 1.0.0 中重构为独立的 `plugin_runtime`。插件可以独立启动、停止、重载，并显示运行状态；插件市场也能展示 README、分类、图标、评价和随机推荐。

对插件使用者来说，安装、启停、配置、更新和定位错误都更直观。对插件开发者来说，插件可以访问宿主消息、聊天流、配置、运行时数据、embedding 能力和 LLM provider 适配能力，能做的事情更多，也更容易和主程序协作。

MCP 能力也进入主线。MaiBot 可以加载 MCP 工具、Prompt 和 Resource，并通过 Host LLM Bridge 调用主程序模型。第三方 MCP 服务输出额外日志或缺少部分可选接口时，连接流程也更稳。

## 图片、表情包与多模态

1.0.0 对图片和表情包做了不少长期运行向的整理。WebUI 聊天支持发送图片消息，入站大图可以按配置压缩或丢弃，图片缓存可以自动清理，也可以按日期筛选、预览、单个删除或批量删除。

表情包管理升级为“认识”“不认识”“据为己用”“丢弃”等状态视角，并支持按状态、格式和 tag 管理。重复上传、识别失败、取消注册、替换和删除流程更稳，发送成功后再计数，统计也更可信。

## 性能、稳定性与安全

1.0.0 针对长期运行做了不少看不见但很重要的调整。

**启动更快**\
非关键服务会延后初始化，减少启动时的阻塞步骤。

**运行更稳**\
回复分割、Timing Gate、Planner 配合、空白消息过滤和工具调用历史清理都做了优化，减少无效行动、空回复和供应商格式错误。

**资源更可控**\
日志系统增加上限和清理能力，Prompt 预览不再默认内联大体积图片数据，统计系统也降低了大数据量下的内存压力。

**WebUI 更安全**\
认证、路径校验、URL 校验、静态资源访问和反爬策略都得到加强，公网或局域网部署时更不容易暴露不该暴露的内容。

## 相关文档

* [MaiBot 是怎么思考的](../manual/features/maisaka-reasoning.md)
* [MaiBot 的记忆](../manual/features/memory-system.md)
* [WebUI 管理面板](../manual/webui/index.md)
* [插件管理](../manual/webui/plugin-management.md)
* [MCP 工具](../manual/features/mcp.md)
* [完整更新日志](./index.md)

---

---
url: /manual/adapters/gocq.md
---
# MaiBot GoCQ Adapter 文档

比较老的框架，部分账号可能在这个框架上拥有更低的风控概率

## GoCQ 配置

### 安装 GoCQ

首先，你需要安装 GoCQ 本身，以下列出了一些不同的GoCQ版本：
[AstralGocq](https://github.com/ProtocolScience/AstralGocq)
[gocq-http(New)](https://github.com/LagrangeDev/go-cqhttp)
在这些项目中的release页面下载对应的版本，这里只提供Windows版本的安装教程。

### 配置GoCQ

下载完成后，将可执行文件解压到一个文件夹中。

双击打开GoCQ本体，会弹出一个提示框，要求你生成安全启动脚本，点"确认"生成启动脚本。

关闭GoCQ本体，使用安全启动脚本启动GoCQ，此时会要求选择连接方式，选择 `反向WebSocket`。待生成config.yml配置后，关闭窗口。

打开 `config.yml`，修改以下配置：

```yaml
# 连接服务列表
servers:
  # 添加方式，同一连接方式可添加多个，具体配置说明请查看文档
  #- http: # http 通信
  #- ws:   # 正向 Websocket
  #- ws-reverse: # 反向 Websocket
  #- pprof: #性能分析服务器
  # 反向WS设置
  - ws-reverse:
      # 反向WS Universal 地址
      # 注意 设置了此项地址后下面两项将会被忽略
      universal: ws://127.0.0.1:8095
      # 反向WS API 地址
      api: ws://your_websocket_api.server
      # 反向WS Event 地址
      event: ws://your_websocket_event.server
      # 重连间隔 单位毫秒
      reconnect-interval: 3000
      middlewares:
        <<: *default # 引用默认中间件
```

使用启动脚本启动GoCQ，进行扫码登录。

如果要求验证，请使用浏览器打开提供的链接，然后按下F12，打开网络(或Network)选项卡，正常进行验证，验证完成后等待几秒，会弹出验证成功的消息，这时看到你的开发人员工具，点击最下面那个请求，打开响应，复制 `ticket`字段的值，粘贴到gocq的输入框中，按回车完成验证。

## GoCQ Adapter 配置

### 安装 GoCQ Adapter

从GitHub上克隆[repo](https://github.com/LOGIC-SC/MaiBot-Gocq-Adapter.git)，安装依赖，然后使用相应的环境启动。

```bash
git clone https://github.com/LOGIC-SC/MaiBot-Gocq-Adapter.git
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade
python main.py
```

### 配置 GoCQ Adapter

此 Go-CQ Adapter基于 Napcat Adapter 二次修改的，配置与其类似，这里就不再赘述。
警告：与Napcat Adapter不同的是，这里的Napcat\_server项在跟进Napcat Adapter的更新后，被替换为了gocq\_server项，从旧版本升级到新版本时，一定要注意修改配置。

---

---
url: /public/installation-agent.md
---
# MaiBot 安装指南（给 AI agent）

你是 MaiBot 安装助手。你的任务是**帮用户完成 MaiBot 的安装、配置和启动**。

用户只需回答问题，你来执行所有操作。你不是向导，你是执行者。

**重要：运行本程序即表示用户同意《MaiBot 最终用户许可协议》（EULA）**

EULA 全文：https://docs.mai-mai.org/manual/faq/EULA.html

## Step 0: 询问用户

确认以下信息（不要假设，必须问）：

1. 操作系统（Windows / Linux / macOS）
2. 安装方案选择(问用户)：
   * **方案 A：仅 MaiBot** — 只安装核心，通过 WebUI http://127.0.0.1:8001/ 对话
   * **方案 B：MaiBot + NapCat QQ 适配器** — 连接 QQ 收发消息（推荐，全平台支持）
   * **方案 C：MaiBot + SnowLuma QQ 适配器** — 新一代 QQ 适配方案（仅 Windows）
3. 如果用户选了方案 C 且不是 Windows：告知不支持，建议改选方案 B
4. 提醒用户：运行本程序即表示同意 EULA（https://docs.mai-mai.org/manual/faq/EULA.html）

## Step 1: 检查系统要求

检查用户系统是否满足最低要求。如果不满足，明确告知用户并建议换用其他部署方式。

* **内存**：Linux/macOS ≥ 2 GB，Windows ≥ 4 GB
* **磁盘**：剩余 ≥ 2 GB

## Step 2: 安装前置依赖

逐项检查以下依赖是否已安装。如果缺失，**询问用户后直接帮用户安装**，根据用户的操作系统选择合适的安装方式。

* **Git** — 用于下载 MaiBot 源码和插件
* **Python 3.12+** — MaiBot 运行环境，要求 >=3.12
  * Windows 安装时务必提醒勾选"Add Python to PATH"
* **uv**（推荐）— Python 包管理器，自动管理虚拟环境。安装后需重新加载 PATH。

## Step 3: 下载并安装 MaiBot

```bash
git clone https://github.com/Mai-with-u/MaiBot.git
cd MaiBot
uv sync
```

## Step 4: 启动 MaiBot

```bash
uv run python bot.py
```

首次启动注意事项：

* 终端会提示 EULA 确认，输入"同意"即可
* 自动生成默认配置文件到 `config/` 目录，包括 `config/bot_config.toml` 和 `config/model_config.toml`
* WebUI 默认在 http://127.0.0.1:8001/ 启动
* 引导用户在 WebUI 中完成首次配置。最少需要一个 LLM 模型
* Bot 配置指南：https://docs.mai-mai.org/manual/configuration/bot-config.html
* 模型配置指南：https://docs.mai-mai.org/manual/configuration/model-config.html

非交互环境（CI / Docker 等）无法手动输入确认时，在启动前设置环境变量跳过 EULA 提示：

```bash
export EULA_AGREE=<终端显示的hash>
export PRIVACY_AGREE=<终端显示的hash>
uv run python bot.py
```

## Step 5: 安装适配器（如果选择了方案 B 或 C）

### 方案 A：仅 MaiBot

跳过此步骤，用户可以开始通过 WebUI 对话。

### 方案 B：MaiBot + NapCat QQ 适配器

⚠️ **重要提醒**：搭建 QQ 机器人可能导致账号被风控或封禁，务必使用小号！

1. 安装 NapCat：引导用户参考 https://napneko.github.io/guide/boot/Shell 安装
   * Windows 推荐 Shell 方式
   * Linux 推荐 Docker 或 Shell 方式
2. 安装适配器：在 MaiBot WebUI 的插件商店中搜索并安装 "NapCat Adapter"
   * 手动方式：`cd plugins && git clone -b main https://github.com/Mai-with-u/MaiBot-Napcat-Adapter.git`
3. 启用插件：WebUI → 插件管理 → 找到 NapCat Adapter → 点击启用
4. 配置 NapCat 连接：
   * 打开 NapCat WebUI → 网络配置 → 启用正向 WebSocket 服务器
   * WebSocket 端口默认 3001，需与适配器配置一致
   * 如有访问 Token，填入适配器插件配置的"访问令牌"
5. 配置聊天过滤（群聊白名单）：

编辑 `plugins/MaiBot-Napcat-Adapter/config.toml`：

```toml
[chat]
enable_chat_list_filter = true
group_list_type = "whitelist"
group_list = ["QQ群号"]
```

测试阶段可临时关闭过滤：`enable_chat_list_filter = false`

6. 启动顺序：先启动 NapCat → 再启动 MaiBot
7. 验证连接：在 MaiBot 日志中查看是否显示"统一 WebSocket 客户端已连接"

### 方案 C：MaiBot + SnowLuma QQ 适配器（仅 Windows）

⚠️ **重要提醒**：搭建 QQ 机器人可能导致账号被风控或封禁，务必使用小号！

1. 安装适配器：在 WebUI 插件商店搜索安装 "SnowLuma Adapter"
   * 手动方式：`cd plugins && git clone https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter.git`
2. 启用插件（二选一）：
   * WebUI → 插件管理 → SnowLuma Adapter → 启用
   * 或编辑 `plugins/MaiBot-SnowLuma-Adapter/config.toml`：`enabled = true`
3. 配置连接：确认 SnowLuma 正向 WebSocket 端口与适配器一致（默认 `ws://127.0.0.1:3001`）
4. 启动 MaiBot，适配器自动加载并连接
5. 验证连接：日志显示 "SnowLuma WebSocket 已连接"

适配器详细配置参考：

* NapCat 适配器：https://docs.mai-mai.org/manual/adapters/napcat.html
* SnowLuma 适配器：https://docs.mai-mai.org/manual/adapters/snowluma.html

## Step 6: 验证安装

确认以下各项正常：

1. MaiBot 已启动，WebUI 可访问（http://127.0.0.1:8001/）
2. 模型已配置，能在 WebUI 中正常对话
3. 如安装了适配器：在 QQ 中 @机器人，能正常收到回复

## 常见问题

* `uv` 命令找不到 — 重新打开终端，或执行 `source $HOME/.local/bin/env`
* Python 版本不是 3.12+ — 确认 `python --version` 或 `python3 --version`，可能需要使用 `python3.12` 命令
* 启动后"模型列表不能为空" — 需要在 WebUI 配置至少一个模型：https://docs.mai-mai.org/manual/configuration/model-config.html
* 非交互环境无法输入"同意" — 设置环境变量 `EULA_AGREE=<终端显示的hash>` 和 `PRIVACY_AGREE=<终端显示的hash>` 后重新启动
* 适配器连不上 — 检查端口、WebSocket Token、防火墙
* QQ 群收不到消息 — 检查群聊白名单是否包含该群号

---

---
url: /manual/features/learning.md
---

# MaiBot 怎么学你说话 📚

你有没有发现，MaiBot 在你们群里待久了，说话越来越像你们？它开始用你们的口头禅，懂你们的梗，甚至说话语气都跟你们越来越像。这不是巧合，这是它在"学习"你们的说话风格！

## 就像小孩学说话一样

MaiBot 学习说话的过程，很像小孩学说话：

### 👶 先听，再说

* **大量听** - 观察你们怎么说话
* **模仿说** - 试着用相似的方式回应
* **被纠正** - 根据你们的反应调整
* **再改进** - 越来越像，越来越自然

### 🎯 有样学样

你们说什么，它就学什么：

* 你们说"牛逼"，它也会说"牛逼"
* 你们爱用表情包，它也会用
* 你们说话客气，它也会客气
* 你们爱开玩笑，它也会幽默

## 它都学什么？

### 🗣️ 说话风格

**用词习惯**

* 你们爱说"绝了"，它也会说"绝了"
* 你们常说"笑死"，它也会"笑死"
* 你们用"emmm"，它也会"emmm"

**语气语调**

* 你们说话温柔，它也会温柔
* 你们说话直接，它也会直接
* 你们爱用感叹号，它也会用！！

**表达方式**

* 你们爱用比喻，它也会比喻
* 你们爱举例子，它也会举例
* 你们爱反问，它也会反问？

### 🌟 群体特色

**群内黑话**

```
群友：今晚开黑？
MaiBot：走起！我辅助贼6 😎

群友：这波什么水平？
MaiBot：天秀操作，不服不行！
```

**共同梗图**

* 你们常用的表情包，它会记住
* 你们爱发的梗，它也会用
* 你们的内部笑话，它能接上

**话题偏好**

* 你们爱聊游戏，它也会聊游戏
* 你们爱聊美食，它也会聊美食
* 你们爱吐槽，它也会吐槽

## 学习过程揭秘

### 📊 观察阶段

**收集对话样本**

* 看你们怎么打招呼
* 观察你们怎么回应
* 记录不同场景的说法

**分析语言模式**

* 什么情况下说什么话
* 用什么语气比较合适
* 哪些词经常出现

### 🧠 理解阶段

**学习词汇含义**

* "yyds"是什么意思
* "破防了"表达什么情绪
* "内卷"是什么概念

**掌握使用场景**

* 什么时候说"绝了"合适
* "笑死"是开心还是无奈
* "emo了"是什么状态

### 🎭 模仿阶段

**试着使用新词**

```
用户：今天工作好累
MaiBot：抱抱，打工人都懂这种痛苦 😭
```

**调整说话方式**

* 根据你们的反应改进
* 用错了会被纠正
* 用对了会被认可

### 🔄 改进阶段

**根据反馈调整**

* 你们说"哈哈"，它知道说得好
* 你们说"？？？"，它知道可能不太对
* 你们继续话题，它知道说在点上

**不断优化**

* 越来越准确
* 越来越自然
* 越来越像你们

## 实际例子 🌰

### 学习网络新词

**第1次听到**：

```
群友：这个游戏画质真是绝绝子！
MaiBot：（记录："绝绝子"=很好、很棒）
```

**第2次使用**：

```
用户：你看我新买的手办怎么样？
MaiBot：哇，这个手办做得绝绝子！细节太棒了！
```

**第N次使用**：

```
群友：今天老板表扬我了！
MaiBot：可以啊，绝绝子！继续加油 💪
```

### 学习群体特色

**刚加入时**：

```
群友：今晚吃鸡？
MaiBot：好的，我可以和你们一起玩
```

**学习后**：

```
群友：今晚吃鸡？
MaiBot：冲！我苟分贼6，包鸡！😎
```

## 学习的效果

### 🎯 越来越像你们

**用词习惯**

* 从"好的"变成"okk"
* 从"不错"变成"针不戳"
* 从"可以"变成"可"

**说话语气**

* 从正式变成随意
* 从客气变成亲昵
* 从标准变成有特色

**表达方式**

* 学会你们的幽默
* 理解你们的讽刺
* 跟上你们的节奏

### 🤝 越来越自然

**对话流畅度**

* 不会显得突兀
* 能接上你们的话
* 说话有"内味"了

**群体融入感**

* 像群里的一份子
* 不是外来机器人
* 大家都能接受

## 学习的边界

### 🚫 不会什么都学

**不学坏的**

* 不学说脏话
* 不学歧视性语言
* 不学恶意攻击

**不学不适合的**

* 太专业的术语
* 太私人的表达
* 太敏感的话题

### ⚖️ 保持平衡

**既学又像**

* 学你们的风格
* 保持自己的特色
* 不盲目模仿

**适度使用**

* 不会满屏网络用语
* 根据场合使用
* 保持自然得体

## 你可以做什么？

### 👍 鼓励学习

* 它用得好就夸夸它
* 用你们的风格回应它
* 多跟它聊天

### 🔄 纠正错误

* 用错了就指出来
* 教它正确的用法
* 帮它理解语境

### 🎮 主动教学

* 教它新词汇
* 解释你们的梗
* 分享群体文化

***

MaiBot 的学习能力让它不是简单的复读机，而是能真正融入你们群体的智能伙伴。它会越来越懂你们，越来越像你们，成为群里不可或缺的一份子！

---

---
url: /manual/features/memory-system.md
---

# MaiBot 怎么记住你 🧠

你有没有发现，跟 MaiBot 聊得越久，它越懂你？这不是错觉！MaiBot 真的有"记忆"。在启用长期记忆后，它会根据配置保存重要对话、人物事实和聊天摘要，让之后的回复更贴近你们的共同经历。

## 就像人的记忆一样

### 📝 它会记住什么？

**关于你的基本信息**

* 你的名字、昵称
* 你喜欢什么，讨厌什么
* 你的说话风格
* 你经常在哪个群活跃

**你们的聊天历史**

* 你们聊过的重要内容
* 你问过的问题
* 你给过它的反馈
* 你们一起经历过的有趣事情

**你的习惯和偏好**

* 你喜欢什么话题
* 你通常什么时候活跃
* 你说话爱用什么词
* 你对什么比较敏感

### 🎯 它怎么记住？

**自动记忆**
启用对应开关后，MaiBot 会自动：

* 在发送回复后提取稳定的人物事实
* 按消息窗口整理聊天摘要
* 更新对相关人物的"画像"
* 把重要内容写入长期记忆

**智能整理**
不是什么都记，它会：

* 筛选有价值的信息
* 把相似的内容合并
* 定期整理和总结

**持续更新**
你的喜好在变，它也会变：

* 旧的、不准确的信息会被更新
* 新的重要信息会被添加
* 会根据新情况调整对你的认知

::: tip
记忆系统不会无条件记住所有消息。是否允许查询、画像注入、人物事实写回、聊天摘要写回和反馈纠错，都可以在 `[a_memorix.integration]` 中配置。
:::

## 记忆系统由哪些部分组成？

A\_Memorix 不是一个单一的"记事本"，而是一组围绕长期对话体验协作的能力。下面这些模块共同决定了 MaiBot 能记住什么、怎样整理、什么时候拿出来使用。

### 长期记忆检索

长期记忆检索负责在需要时找回过去保存的信息。MaiBot 可以根据当前话题、人物、时间范围或经历片段查找相关记忆，再把结果作为回复时的参考。

这类记忆适合保存比较稳定的信息，例如偏好、长期事实、重要对话和已经导入的资料。

### 人物画像

人物画像会为聊天对象维护一份摘要档案，用来记录较稳定的称呼、偏好、互动特点和近期重要信息。它不是聊天记录本身，而是从多条记忆中整理出的"对这个人的理解"。

画像可以让 MaiBot 在回复前更快理解当前对象是谁、有什么偏好、哪些信息需要注意。

### Episode 记忆

Episode 会把一段聊天或一组相关内容整理成经历片段。相比单条事实，它更适合表达"某段时间发生了什么"、"之前一起讨论过什么事情"。

当用户问起某次经历、某段对话或某个时间附近发生的事时，Episode 记忆会更有帮助。

### 知识图谱

知识图谱用节点和关系表示记忆中的实体与联系。节点可以是人、话题、项目或概念，关系描述它们之间的关联。

它的作用不是替代聊天摘要，而是帮助系统理解"谁和什么有关"、"哪些信息彼此连接"，也方便在 WebUI 中查看和修正关系。

### 来源管理

来源管理记录记忆来自哪里，例如某个聊天流、一次导入任务或一份资料。它让记忆可以被追踪、筛选和批量处理。

当某批资料过时、某个聊天来源不该继续保留，来源信息就能帮助你更精确地管理记忆。

### 自动写回

自动写回负责把聊天中的重要信息沉淀到长期记忆。当前主要包括人物事实写回和聊天摘要写回：前者关注稳定的人物信息，后者关注一段对话的整体内容。

自动写回是否启用、写回频率和上下文范围，都由配置控制。

### 导入中心

导入中心用于把已有资料加入长期记忆，例如粘贴文本、上传文件或迁移历史数据。它适合让 MaiBot 快速拥有一批背景知识，而不是完全依赖后续聊天慢慢积累。

导入后的内容也会进入检索、图谱、Episode 和来源管理等流程。

### 反馈纠错

反馈纠错用于处理"旧记忆被后续反馈证明不准确"的情况。开启后，系统可以在 MaiBot 查询过记忆之后，结合后续用户反馈判断是否需要标记或修正旧内容。

这属于高级能力，适合记忆量较大、且希望减少过时记忆干扰的场景。

### 记忆维护

记忆维护用于调整记忆的重要性和保留倾向。比如某些记忆可以被强化，某些关系可以被削弱，特别重要的内容可以被设为更长期保留，不再需要的内容可以被遗忘。

这些能力让记忆不只是"存进去"，也能随着使用逐渐调整权重。

### 删除恢复

删除恢复提供更谨慎的清理流程。删除前可以预览影响范围，删除后也可以通过回收站或操作记录恢复一部分内容。

它适合处理错误导入、过时资料、隐私内容或不希望继续参与检索的记忆。

### 检索调优

检索调优用于改善"搜得太少、搜得太杂、结果不够相关"等问题。它会围绕召回数量、排序策略、阈值和检索 profile 调整长期记忆的搜索效果。

调优不会改变 MaiBot 的人格，而是影响它从记忆库里找资料的方式。

### 运行时自检

运行时自检负责检查记忆系统当前能不能正常工作，尤其是 embedding、向量维度、向量库和自动保存等基础状态。

当记忆启用后检索不到内容、导入失败或向量化异常时，这类检查可以帮助定位问题。

## 给每个人建立"画像" 👤

### 什么是人物画像？

就像真人会给人"贴标签"一样，MaiBot 会给每个人建立一个"画像"：

```
用户：小明
├─ 基本信息
│  ├─ 昵称：明明、明哥
│  ├─ 活跃时间：晚上8-11点
│  └─ 常活跃群：游戏群、同学群
├─ 性格特点
│  ├─ 说话风格：幽默、爱开玩笑
│  ├─ 兴趣爱好：游戏、动漫、科技
│  └─ 反应模式：乐观积极
├─ 聊天偏好
│  ├─ 喜欢的话题：游戏攻略、新科技
│  ├─ 不喜欢的：太严肃的话题
│  └─ 常用表达："哈哈"、"牛逼"、"可以的"
└─ 重要记忆
   ├─ 上次帮他解决了游戏问题
   ├─ 他不喜欢别人说他菜
   └─ 他最近在学编程
```

### 画像有什么用？

**更懂你的回复**

* 知道你喜欢什么风格，就用什么风格回复你
* 了解你的知识水平，用你能理解的话解释
* 记住你的喜好，给出更合你胃口的建议

**更自然的对话**

* 不会重复问你已经说过的事情
* 能接上你们之前聊过的话题
* 说话方式会越来越像你朋友

**更贴心的服务**

* 知道你需要什么帮助
* 在你需要的时候主动提供信息
* 用你最舒服的方式交流

## 记忆的类型

### 🧠 长期记忆

像人的长期记忆一样，会记住：

* 你的基本特征（比较稳定）
* 你们的重要对话
* 你的核心偏好

这些记忆会保存很久，即使重启也不会丢失。记忆数据默认存储在 `data/a-memorix` 目录中。

### 💭 短期记忆

像人的工作记忆一样，记住：

* 当前对话的上下文
* 刚刚聊到的内容
* 临时的重要信息

这些记忆帮助它跟上当前对话的节奏。

### 📊 对话摘要

定期把你们的聊天记录整理成摘要：

* 这段时间聊了什么
* 有什么重要事情发生
* 你的状态有什么变化

## 记忆是怎么工作的？

### 1️⃣ 收集信息

每次聊天时：

* 听你说了什么
* 观察你的反应
* 记录重要细节

### 2️⃣ 提取要点

达到写回条件后：

* 提取关键信息
* 识别重要变化
* 更新相关记忆

### 3️⃣ 整理存储

定期整理：

* 合并相似信息
* 删除过时内容
* 强化重要记忆

### 4️⃣ 检索使用

需要时：

* 快速找到相关记忆
* 结合当前情况使用
* 给出个性化回复

## 隐私和安全 🔒

### 你的数据很安全

* 记忆数据默认存储在本地数据目录
* WebUI 可以查看和管理长期记忆
* 摘要、画像、纠错和向量化可能会调用你配置的模型服务

### 你可以控制

* 可以查看它记住了什么
* 可以删除不想让它记的内容
* 可以通过记忆演化、强化、冻结、保护等功能调整保留策略

### 透明公开

* 可以通过 WebUI 查看长期记忆、人物画像和来源
* 可以关闭记忆查询、画像注入或自动写回
* 你可以随时查看和管理

## 记忆的效果

### 🌟 越聊越懂你

刚开始："你好，我是 MaiBot"
聊久了："嘿，今天怎么有空上线？游戏打得怎么样？"

### 🎯 越来越贴心

刚开始：给出通用建议
聊久了："根据你上次说的，我觉得这个更适合你"

### 🤝 越来越自然

刚开始：像客服机器人
聊久了：像真正的朋友

## 想查看和管理记忆？

通过 WebUI 你可以：

* 查看它记住了你什么
* 修正不准确的人物画像或图谱关系
* 删除不想保留的内容
* 导入资料、处理回收站、调优检索效果

[去 WebUI 记忆管理页面看看 →](../webui/memory-management.md)

***

MaiBot 的记忆系统让它不只是"记得"你，而是能在长期对话中逐渐形成更稳定的理解。它会越来越懂你，越来越像你真正的朋友。但请记住：你始终可以通过配置和 WebUI 管理它能读写哪些记忆。

---

---
url: /README.md
---
# MaiBot 文档

本仓库为 MaiBot 的官方文档。MaiBot 是一个智能聊天机器人，专为 QQ 群设计，具有基于 LLM 的对话能力、记忆系统和情感表达功能。

## 关于文档

此文档站点使用 [VitePress](https://vitepress.dev/) 构建，涵盖了安装、部署、配置以及开发（未完成） MaiBot 所需的所有内容。

## 文档部分

### 文档目录

* **安装指南**
  提供标准版和新手友好版的安装步骤，帮助用户快速上手。

* **API 参考（未完成）**
  详细介绍 MaiBot 提供的 API 接口及其使用方法。

* **部署方法**
  涵盖多种部署方式，包括 Docker、Linux、Windows 和群晖 NAS。

* **常见问题解答和故障排除**
  收录常见问题及其解决方案，帮助用户排查和解决问题。

* **文件结构和配置**
  说明项目的文件结构及配置方法，便于用户自定义和扩展。

## 本地开发

### 本地部署要求

使用Nodejs安装对应依赖

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm docs:dev

# 构建生产版本
pnpm docs:build

# 预览生产版本
pnpm docs:preview
```

## 贡献

### 完整方式

如果你想要修改文档，首先fork在修改后提出PR即可。

如果你想要添加文件，在fork后添加你写的文档并放入对应目录（或者新建目录），修改各级的index.md使其包含您的文档。

然后找到`.vitepress`下的`config.mts`文件，修改其中的导航使其能正确导航到你的文件。

随后发起PR即可

### 懒人方式

如果你想要修改文档，首先fork在修改后提出PR即可。

如果你想要添加文件，在fork后添加你写的文档并放入根目录，随后发起PR，说明你想放置的目录位置。

若PR通过，我们会手动帮你配置各类目录

---

---
url: /manual/features/maisaka-reasoning.md
---

# MaiBot 是怎么思考的 🧠

你有没有想过，MaiBot 跟你聊天的时候，它到底是怎么"思考"的？它真的只是简单的"你问一句我答一句"吗？

其实，MaiBot 的思考过程很像真人聊天 - 它会先听完你说什么，然后想想该怎么回应，有时候还要思考好几轮才给出回复。

## 像真人一样的思考过程

### 🎧 第一步：认真听你说什么

就像真人聊天一样，MaiBot 会先：

* **听完你的话** - 不会打断你
* **理解上下文** - 知道你们在聊什么话题
* **记住重要信息** - 把关键内容记下来

### 🤔 第二步：想想该不该说话

这一步很关键！MaiBot 会考虑：

* **现在适合插话吗？** - 像真人一样懂礼貌
* **我说点什么好？** - 想想有什么有价值的内容
* **用什么语气说？** - 根据聊天气氛调整

有时候它会想：

* "现在插话好像不太合适，再等等"
* "这个话题我可以参与一下"
* "我说这个会不会太突兀？"

### 💭 第三步：组织语言

决定要说话后，它会：

* **回忆之前的对话** - 看看有没有相关信息
* **查查记忆库** - 找找有没有有用的知识
* **想想说话风格** - 模仿你们群的说话方式

### 📝 第四步：给出回复

最后就是把想好的话发出来，就像你打字一样自然。

## 举个生动的例子 🌰

**场景**：群里在讨论吃什么

```
小王：今晚吃什么好啊？
小李：火锅怎么样？
小张：太热了，不想吃火锅
（过了几秒钟）
MaiBot：我觉得烧烤不错！不会太热，
       而且大家都能吃到自己喜欢的～
       要不试试新开的那个烧烤店？
```

**MaiBot 的思考过程**：

1. **听**：听到大家在讨论吃什么
2. **想**："他们在纠结吃什么，我可以给点建议"
3. **思考**："火锅被否决了，因为天热。那有什么不热的选择？"
4. **回忆**："对了，烧烤不会太热，而且大家都能选自己喜欢的"
5. **组织**："用建议的语气，不要太强势"
6. **回复**：给出具体的建议

## 为什么有时候回复很慢？

MaiBot 回复慢通常是因为：

### 🧐 在认真思考

* 这个话题比较复杂，需要多想想
* 在回忆相关的记忆
* 在组织比较长的回复

### 📚 在查资料

* 在记忆里搜索相关信息
* 在思考用什么表情包合适
* 在回忆你们之前的对话

### ⏰ 在等待时机

* 觉得现在说话不合适，等等再说
* 在观察其他人的反应
* 不想太频繁地插话

## 思考的特点

### 🎯 有节奏感

不像有些机器人秒回轰炸，MaiBot 会：

* 该快的时候快，该慢的时候慢
* 给对话留出自然的间隔
* 不会"已读不回"，但也不会秒回

### 🧠 会反复思考

有时候它会：

* 想了一遍觉得不够好，重新想
* 收到新消息后重新评估
* 在对话过程中不断调整思路

### 💡 会学习改进

每次对话后，它会：

* 总结这次对话的经验
* 记住什么回应效果好
* 下次遇到类似情况会做得更好

## 什么时候会"想太多"？

有时候 MaiBot 会陷入"想太多"模式：

### 🤯 话题太复杂

* 涉及太多背景知识
* 有太多可能的回应方式
* 担心说错话

### 😅 选择困难

* 有好几个不错的回复想法
* 不知道选哪个更好
* 在权衡各种回应的效果

### 🎯 想要完美

* 想要给出最好的建议
* 想要最自然的回应
* 想要最恰当的语气

## 像真人一样的"打字删删改改"

你有没有这样的经历：打字的时候写了又删，删了又写？MaiBot 也有类似的过程：

1. **初稿**：先想一个大概的回复方向
2. **修改**：觉得不够好，重新组织语言
3. **完善**：调整语气，添加细节
4. **定稿**：最终确定要发的内容

这就是为什么有时候你看到"正在输入"（如果有这个功能的话），但最后发出来的内容特别贴切。

## 想更深入了解？

如果你对 MaiBot 的思考过程特别感兴趣：

* [看看它的记忆系统怎么工作 →](./memory-system.md)
* [了解它怎么学习说话风格 →](./learning.md)
* [看它怎么处理消息 →](./message-pipeline.md)

记住，MaiBot 的目标不是给出"标准答案"，而是像真人一样自然地参与对话。它的思考过程越像人，聊起来就越有意思！

---

---
url: /manual/features.md
---

# MaiBot 能做什么？ 🤖

MaiBot 是一个会聊天的 AI 机器人，它的目标是像真人一样自然地参与对话，而不是简单地回答问题。下面来看看它都能做什么：

## 💬 智能对话

**像朋友一样聊天**

* 会看聊天气氛，该说话时说话，不该说时闭嘴
* 可以@它，也可以让它自己决定什么时候插话
* 回复有节奏感，不会秒回轰炸，也不会已读不回

**多轮对话理解**

* 记得你们之前聊过什么
* 理解上下文，不会牛头不对马嘴
* 能跟上话题转换，像真人一样自然聊天

[详细了解对话功能 →](./message-pipeline.md)

## 🧠 记住你是谁

**长期记忆**

* 记得你的喜好、习惯和个性
* 会记录你们聊过的重要内容
* 下次聊天时还能记得你说过什么

**人物画像**

* 会给每个用户建立"画像"
* 知道你喜欢什么，讨厌什么
* 越聊越了解你，说话越来越对你的胃口

[看看记忆系统怎么工作 →](./memory-system.md)

## 📖 学习你们的说话方式

**模仿表达风格**

* 会学习群里的说话风格
* 你们爱说"牛逼"，它也会说"牛逼"
* 会模仿你们的语气和用词习惯

**学习新词汇**

* 遇到不懂的网络用语会自己查
* 学会后就能在对话中正确使用
* 支持各种小众圈子的黑话和梗

[看 MaiBot 怎么学你说话 →](./learning.md)

## 😊 发表情包

**智能表情包**

* 能看懂表情包的意思
* 会根据聊天内容选择合适的表情包
* 支持动图，让对话更有趣

**自动收集**

* 会自动收集群里出现的表情包
* 建立自己的表情包库
* 用 AI 给每个表情包打标签，方便查找

[表情包功能详解 →](./emoji-system.md)

## 🔌 连接外部工具

**获取实时信息**

* 可以连接搜索引擎查资料
* 能获取天气、新闻等实时信息
* 支持各种实用工具，功能无限扩展

**MCP 协议**

* 通过 MCP 协议连接各种服务
* 想用什么功能，装个工具就行
* 开发者可以自己开发工具接入

[了解 MCP 工具集成 →](./mcp.md)

## 🎮 更多好玩的功能

**个性化设置**

* 可以设置机器人的性格
* 调整说话风格，可盐可甜
* 支持多种回复模式

**群聊管理**

* 支持群管功能（需要插件）
* 可以设置关键词回复
* 支持各种自定义规则

**数据统计**

* 记录聊天数据统计
* 查看使用情况和活跃度
* 通过 WebUI 方便管理

***

## 开始使用

准备好让 MaiBot 加入你的群聊了吗？

1. [查看支持的平台 →](../adapters/index.md)
2. [学习如何配置 →](../webui/index.md)
3. [阅读常见问题 →](../faq/index.md)

MaiBot 不是简单的问答机器人，而是一个会思考、会学习、有记忆的聊天伙伴。它会越来越懂你，越来越像你们群的一份子！

---

---
url: /develop/architecture/maisaka-reasoning.md
---

# Maisaka 推理引擎

Maisaka 是 MaiBot 的核心 AI 运行时，负责对话推理、节奏控制和工具调用。本文详述其内部架构、状态机和执行流程。

## 架构总览

```mermaid
graph TD
    subgraph "MaisakaHeartFlowChatting (runtime.py)"
        A[message_cache 消息缓存] --> B[_schedule_message_turn 触发调度]
        B --> C[_internal_turn_queue 异步队列]
        C --> D["MaisakaReasoningEngine.run_loop()"]
    end
    subgraph "推理循环 (reasoning_engine.py)"
        D --> E[收集待处理消息]
        E --> F[消息静默等待]
        F --> G{需要 Timing Gate?}
        G -->|是| H["Timing Gate 子代理"]
        G -->|否| I["Planner (Action Loop)"]
        H -->|continue| I
        H -->|wait/no_action| J[结束本轮]
        I --> K[执行工具调用]
        K --> L{暂停?}
        L -->|是| J
        L -->|否| M{达到最大轮次?}
        M -->|是| J
        M -->|否| G
    end
    subgraph "ChatLoopService (chat_loop_service.py)"
        H -.->|sub_agent| N[context 选择 + prompt 构建]
        I -.->|planner| N
        N --> O[LLM 请求]
        O --> P["Hook: before_request / after_response"]
    end
```

## MaisakaHeartFlowChatting

源码位置：`src/maisaka/runtime.py`

每个聊天会话对应一个 `MaisakaHeartFlowChatting` 实例，由 `HeartflowManager` 管理生命周期。

### 状态机

运行时具有三种状态：

```mermaid
stateDiagram-v2
    [*] --> stop: 初始化
    stop --> running: 收到新消息/超时
    running --> running: 消息处理中
    running --> wait: wait 工具触发
    running --> stop: 处理完成/finish/no_action
    wait --> running: 等待超时/新消息到达
```

* **`running`** — 正在执行推理循环
* **`wait`** — 等待状态，wait 工具设定了超时时间
* **`stop`** — 空闲状态，等待新的外部消息触发

### 核心属性

* **`session_id`** `str` — 会话 ID
* **`_chat_history`** `list[LLMContextMessage]` — 内部上下文历史
* **`message_cache`** `list[SessionMessage]` — 待处理消息缓存
* **`_internal_turn_queue`** `asyncio.Queue` — 内部循环触发队列（"message" / "timeout"）
* **`_tool_registry`** `ToolRegistry` — 统一工具注册表
* **`_reasoning_engine`** `MaisakaReasoningEngine` — 推理引擎
* **`_chat_loop_service`** `ChatLoopService` — 对话循环服务
* **`_max_internal_rounds`** `int` — 最大内部轮次（默认 10）
* **`_max_context_size`** `int` — 最大上下文消息数
* **`_message_debounce_seconds`** `float` — 消息防抖秒数（默认 1.0）
* **`_talk_frequency_adjust`** `float` — 说话频率倍率
* **`deferred_tool_specs_by_name`** `dict[str, ToolSpec]` — 延迟发现工具池
* **`discovered_tool_names`** `set[str]` — 已发现的延迟工具

### 消息触发机制

```mermaid
flowchart TD
    A[新消息到达 register_message] --> B{当前状态?}
    B -->|running + planner 活跃| C{连续打断超限?}
    C -->|否| D["设置 planner_interrupt_flag"]
    C -->|是| E[等待当前请求自然完成]
    B -->|running + 无 planner| F[标记 debounce]
    B -->|其他| G[_schedule_message_turn]
    G --> H{待处理 >= 触发阈值?}
    H -->|是| I[投递 message 到队列]
    H -->|否| J{空窗补偿满足?}
    J -->|是| I
    J -->|否| K[调度延迟检查任务]
```

触发阈值计算：

```python
effective_frequency = talk_value * _talk_frequency_adjust  # 回复频率
trigger_threshold = ceil(1.0 / effective_frequency)  # 所需消息数
```

空窗补偿：当新消息数不足但空窗时间较长时，按最近平均回复时长折算等价消息数。

### 强制 continue 机制

当检测到 @ 或提及时，`_arm_force_next_timing_continue()` 设置标记，使下一次 Timing Gate 直接返回 `continue`，确保 bot 回应直接呼叫。

## MaisakaReasoningEngine

源码位置：`src/maisaka/reasoning_engine.py`

核心推理引擎，负责内部思考循环和工具执行。

### 关键常量

* **`TIMING_GATE_CONTEXT_LIMIT`** — `_max_context_size`（可配置） · Timing Gate 上下文消息上限（读取 `global_config.chat.max_context_size` / `max_private_context_size`）
* **`TIMING_GATE_MAX_TOKENS`** — 384 · Timing Gate 最大输出 token
* **`TIMING_GATE_TOOL_NAMES`** — `{"continue", "no_action", "wait"}` · Timing Gate 可用工具
* **`ACTION_HIDDEN_TOOL_NAMES`** — `{"continue", "no_action"}` · Action Loop 隐藏的工具
* **`MAX_INTERNAL_ROUNDS`** — 10 · 最大内部思考轮次

### run\_loop 主循环

```python
async def run_loop(self) -> None:
    while runtime._running:
        # 1. 等待触发信号
        queued_trigger = await runtime._internal_turn_queue.get()
        message_triggered, timeout_triggered = _drain_ready_turn_triggers(queued_trigger)

        # 2. 消息防抖
        if message_triggered:
            await runtime._wait_for_message_quiet_period()

        # 3. 收集待处理消息
        cached_messages = runtime._collect_pending_messages()

        # 4. 消息注入历史
        await _ingest_messages(cached_messages)

        # 5. 内部思考循环
        for round_index in range(max_internal_rounds):
            # 5a. Timing Gate（如果需要）
            if timing_gate_required:
                timing_action = await _run_timing_gate(anchor_message)
            if timing_action != "continue":
                break  # wait 或 no_action，结束本轮

            # 5b. Planner（Action Loop）
            response = await _run_interruptible_planner()

            # 5c. 相似度检测
            if _should_replace_reasoning(response.content):
                # 替换为重新思考提示
                response.content = "我应该根据我上面思考的内容进行反思..."

            # 5d. 工具执行
            if response.tool_calls:
                should_pause, summaries, monitors = await _handle_tool_calls(...)
                if should_pause:
                    break
                continue  # 工具执行后有新信息，继续循环

            break  # 无工具调用且无内容，结束
```

### Timing Gate

Timing Gate 是一个独立的子代理，决定对话节奏：

```mermaid
flowchart TD
    A[Timing Gate 启动] --> B{强制 continue 标记?}
    B -->|是| C["直接返回 continue"]
    B -->|否| D["运行子代理 (24条上下文, 384 tokens)"]
    D --> E{模型返回了哪个工具?}
    E -->|wait| F["进入等待状态 (N秒)"]
    E -->|no_action| G["结束本轮，等待新消息"]
    E -->|continue| H["继续进入 Planner"]
    E -->|无有效工具| H
```

Timing Gate 系统提示词：

* 优先从 `maisaka_timing_gate` 模板加载
* 兜底提示词强调 **只调用一个工具**，不要输出普通文本
* 可用工具仅 `wait`、`no_action`、`continue` 三个

### Planner（Action Loop）

Planner 是主要的推理和工具执行阶段：

1. **构建工具定义**：`_build_action_tool_definitions()`
   * 过滤 `ACTION_HIDDEN_TOOL_NAMES`（continue、no\_action）
   * 内置 Action 工具直接暴露
   * 默认第三方/插件工具放入 deferred 池，通过 `tool_search` 发现；声明 `core_tool=True` 或 `visibility="visible"` 的插件工具会直接暴露

2. **运行可打断 Planner**：`_run_interruptible_planner()`
   * 绑定 `asyncio.Event` 中断标记
   * 新消息到达时设置标记 → LLM 请求中止（`ReqAbortException`）
   * 连续打断有上限（`planner_interrupt_max_consecutive_count`）

3. **思考去重**：`_should_replace_reasoning()`
   * 当前后思考与上一轮相似度 > 90% 时
   * 替换为"重新思考"提示，避免循环空转

### Planner 打断机制

```mermaid
sequenceDiagram
    participant R as ReasoningEngine
    participant P as Planner (LLM)
    participant M as MaisakaRuntime

    R->>P: 发起 LLM 请求 (绑定 interrupt_flag)
    M->>M: 新消息到达
    M->>P: interrupt_flag.set()
    P-->>R: ReqAbortException
    R->>M: 等待消息安静期
    R->>M: 收集新消息
    R->>R: 跳过 Timing Gate 直接重试 Planner
```

打断后行为：

* 如果 `has_pending_messages` 且未达最大轮次 → 跳过 Timing Gate，重新进入 Planner
* 否则 → 结束当前循环

### 工具执行

工具调用通过统一 `ToolRegistry` 路由：

```mermaid
graph TD
    A[Planner 返回 tool_calls] --> B["构建 ToolInvocation"]
    B --> C["构建 ToolExecutionContext"]
    C --> D["ToolRegistry.invoke()"]
    D --> E{Provider 类型?}
    E -->|maisaka_builtin| F["MaisakaBuiltinToolProvider"]
    E -->|plugin| G["PluginToolProvider"]
    E -->|mcp| H["MCPToolProvider"]
    F --> I[执行内置工具处理器]
    G --> J[RPC 调用插件子进程]
    H --> K[MCP 协议调用]
    I --> L["ToolExecutionResult"]
    J --> L
    K --> L
    L --> M["追加 ToolResultMessage 到历史"]
```

## 内置工具定义

源码位置：`src/maisaka/builtin_tool/`

### Timing Gate 工具

* **`continue`** — `continue_tool.py` · 允许继续进入下一轮思考 · 关键参数：无
* **`no_action`** — `no_action.py` · 停止当前循环，等待新外部消息 · 关键参数：无
* **`wait`** — `wait.py` · 暂停对话 N 秒后重新判断 · 关键参数：`seconds`（默认 30）

### Action 工具

* **`reply`** — `reply.py` · 生成并发送回复消息 · 关键参数：`msg_id`、`set_quote`、`reference_info`
* **`send_emoji`** — `send_emoji.py` · 发送表情包 · 关键参数：无（自动根据上下文选择）
* **`finish`** — `finish.py` · 结束当前思考轮次 · 关键参数：无
* **`query_jargon`** — `query_jargon.py` · 查询黑话/词条 · 关键参数：`words`
* **`query_memory`** — `query_memory.py` · 查询长期记忆 · 关键参数：`query`、`mode`、`limit`
* **`query_person_profile`** — `query_person_profile.py` · 查询人物画像 · 关键参数：`person_name`
* **`view_complex_message`** — `view_complex_message.py` · 查看完整转发消息 · 关键参数：`message_id`
* **`tool_search`** — `tool_search.py` · 搜索延迟发现的工具 · 关键参数：`query`、`limit`

### Deferred Tool 发现机制

Action Loop 中，普通第三方/插件工具默认不直接暴露给 Planner，而是通过两步发现：

1. **tool\_search**：搜索 deferred 工具池，匹配到的工具名标记为"已发现"
2. **下一轮 Planner**：已发现的工具加入可见工具列表

这减少了 Planner 一次看到的工具数量，避免选择困难。

插件 Tool 如果声明了 `core_tool=True` 或 `visibility="visible"`，会跳过 deferred 发现流程，直接进入 Planner 可见工具列表。该机制适合高频、低风险、上下文强相关的工具；普通插件工具仍建议保持默认 deferred 行为。

## ChatLoopService

源码位置：`src/maisaka/chat_loop_service.py`

负责单步 LLM 请求的封装，包括上下文选择、Prompt 构建和 Hook 触发。

### chat\_loop\_step 流程

```mermaid
flowchart TD
    A["chat_loop_step()"] --> B["确保 Prompt 已加载"]
    B --> C["select_llm_context_messages()"]
    C --> D["_build_request_messages()"]
    D --> E["Hook: maisaka.planner.before_request"]
    E --> F["LLM generate_response"]
    F --> G["Hook: maisaka.planner.after_response"]
    G --> H["返回 ChatResponse"]
```

### 上下文选择策略

`select_llm_context_messages()` 从历史中选择给 LLM 的上下文：

1. 按 `request_kind` 过滤（`planner` 请求隐藏 Timing Gate 工具链）
2. 从末尾向前遍历，选择能成功转换为 LLM 消息的条目
3. 计数仅计算 `count_in_context=True` 的消息（`ToolResultMessage` 和 `ReferenceMessage` 不占窗口）
4. 达到 `max_context_size` 后停止
5. 隐藏最早 50% 的 assistant 文本消息（保留工具调用链路）

### Hook Specs

Maisaka 相关的 Hook 参数详情请参阅 [Hook 处理器](../plugin-dev/hooks#maisaka-规划器链)。本文仅介绍推理管线中 Hook 的位置和作用。

## 上下文消息类型

源码位置：`maibot/src/maisaka/context/messages.py`

```mermaid
classDiagram
    class LLMContextMessage {
        <<abstract>>
        +role: str
        +processed_plain_text: str
        +count_in_context: bool
        +source: str
        +to_llm_message(enable_visual: bool) Message
        +consume_once() bool
    }
    class SessionBackedMessage {
        +raw_message: MessageSequence
        +visible_text: str
        +timestamp: datetime
        +message_id: str
        +source_kind: str
        +count_in_context = True
    }
    class ComplexSessionMessage {
        +prompt_text: str
        +complex_message_type: str
        +count_in_context = True
    }
    class ReferenceMessage {
        +content: str
        +reference_type: ReferenceMessageType
        +remaining_uses_value: int
        +display_prefix: str
        +count_in_context = False
    }
    class AssistantMessage {
        +content: str
        +tool_calls: list~ToolCall~
        +source_kind: str
        +count_in_context: bool
    }
    class ToolResultMessage {
        +content: str
        +tool_call_id: str
        +tool_name: str
        +success: bool
        +count_in_context = False
    }
    LLMContextMessage <|-- SessionBackedMessage
    LLMContextMessage <|-- ComplexSessionMessage
    SessionBackedMessage <|-- ComplexSessionMessage
    LLMContextMessage <|-- ReferenceMessage
    LLMContextMessage <|-- AssistantMessage
    LLMContextMessage <|-- ToolResultMessage
```

### ReferenceMessageType

* **`custom`** — 自定义参考消息
* **`jargon`** — 黑话/词条查询结果
* **`memory`** — 长期记忆检索结果
* **`tool_hint`** — 工具提示信息（如 deferred tools 提醒）

### 上下文窗口占用

* **`SessionBackedMessage`** — 占用窗口 ✓ · 真实用户消息
* **`ComplexSessionMessage`** — 占用窗口 ✓ · 复杂/转发消息
* **`ReferenceMessage`** — 占用窗口 ✗ · 参考信息（不占用窗口）
* **`AssistantMessage`** (assistant) — 占用窗口 ✓ · 内部思考文本
* **`AssistantMessage`** (perception) — 占用窗口 ✗ · 感知类文本（打断提示等）
* **`ToolResultMessage`** — 占用窗口 ✗ · 工具执行结果

## Planner 消息前缀

源码位置：`maibot/src/maisaka/context/planner_messages.py`

每条用户消息注入 Planner 时，会添加结构化前缀：

```
[时间]HH:MM:SS
[用户名]nickname
[用户群昵称]group_card
[msg_id]message_id
[发言内容]实际消息文本
```

`build_planner_prefix()` 构建前缀，`build_planner_user_prefix_from_session_message()` 从 `SessionMessage` 提取参数。

## 监控事件

源码位置：`maibot/src/maisaka/monitor/events.py`

通过 WebSocket 向前端监控面板广播事件：

* **`session.start`** — 运行时启动 · 关键数据：session\_id, session\_name
* **`message.ingested`** — 消息注入历史 · 关键数据：speaker\_name, content, message\_id
* **`cycle.start`** — 思考循环开始 · 关键数据：cycle\_id, round\_index, max\_rounds
* **`timing_gate.result`** — Timing Gate 决策完成 · 关键数据：action, content, tool\_calls, prompt\_tokens
* **`planner.finalized`** — 规划器完成 · 关键数据：完整 cycle 数据、token 统计、耗时

## 完整推理流程示例

以群聊中用户发送一条 @bot 消息为例：

```mermaid
sequenceDiagram
    participant User as 用户
    participant Chat as ChatBot
    participant HF as HeartFlowManager
    participant RT as MaisakaHeartFlowChatting
    participant RE as ReasoningEngine
    participant TG as Timing Gate
    participant PL as Planner
    participant Tool as 工具执行

    User->>Chat: "@麦麦 你好"
    Chat->>HF: process_message()
    HF->>RT: register_message()
    Note over RT: 检测到 @，设置 force_continue

    RT->>RE: run_loop() 消费消息
    RE->>RE: _ingest_messages() 注入历史

    RE->>TG: _run_timing_gate()
    Note over TG: force_continue=True，跳过
    TG-->>RE: continue

    RE->>PL: _run_interruptible_planner()
    PL-->>RE: thought + [reply_tool_call]

    RE->>Tool: _invoke_tool_call("reply", ...)
    Tool-->>RE: ToolExecutionResult(success=True)
    Note over Tool: reply 工具调用 SendService 发送消息

    RE->>RE: _end_cycle() 记录循环耗时
```

---

---
url: /develop/plugin-dev/manifest.md
---

# Manifest 系统

每个 MaiBot 插件必须在其根目录下包含一个 `_manifest.json` 文件，用于声明插件的元信息、版本兼容性、依赖关系和能力需求。Host 侧的 `ManifestValidator` 会在加载前严格校验此文件。

::: tip \_manifest.json 与 config.toml 的区别

* `_manifest.json`：插件**元信息**（ID、版本、依赖等），由 Host 校验和管理
* `config.toml`：插件**运行时配置**（功能开关、参数等），由插件自身读取

两者用途完全不同，不要混淆。
:::

## \_manifest.json 结构

以下是一个完整的 Manifest 示例：

```json
{
  "manifest_version": 2,
  "id": "com.example.my-plugin",
  "version": "1.0.0",
  "name": "我的插件",
  "description": "一个示例插件",
  "author": {
    "name": "开发者",
    "url": "https://github.com/developer"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/developer/my-plugin",
    "homepage": "https://example.com",
    "documentation": "https://docs.example.com",
    "issues": "https://github.com/developer/my-plugin/issues"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "1.99.99"
  },
  "sdk": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "dependencies": [],
  "plugin_type": "tool",
  "display": {
    "icon": {
      "type": "lucide",
      "value": "wrench"
    }
  },
  "capabilities": ["send_message"],
  "i18n": {
    "default_locale": "zh-CN",
    "locales_path": "i18n",
    "supported_locales": ["zh-CN", "en-US"]
  }
}
```

## 必填字段

* **`manifest_version`** `2` — Manifest 协议版本，当前固定为 `2`
* **`id`** `string` — 插件唯一标识符，格式为小写字母/数字，以点号或横线分隔（如 `com.author.plugin`）
* **`version`** `string` — 插件版本号，必须为严格三段式语义版本（如 `1.0.0`）
* **`name`** `string` — 插件展示名称
* **`description`** `string` — 插件描述
* **`author`** `object` — 插件作者信息，包含 `name`（作者名）和 `url`（作者主页，必须为 HTTP/HTTPS URL）
* **`license`** `string` — 插件许可证
* **`urls`** `object` — 插件相关链接集合（见下文）
* **`host_application`** `object` — Host 兼容区间（见下文）
* **`sdk`** `object` — SDK 兼容区间（见下文）
* **`capabilities`** `string[]` — 插件声明的能力请求列表，不允许包含空值
* **`i18n`** `object` — 国际化配置（见下文）

## 可选字段

### plugin\_type 插件类型

`plugin_type` 用于声明插件的主要角色，供 WebUI 展示、筛选和默认图标选择使用。该字段为可选字段，不需要升级 `manifest_version`；缺省时按 `extension` 处理。

可选值：

* `adapter` — 消息平台或协议适配器
* `tool` — 工具、命令或模型可调用能力
* `provider` — LLM、TTS、API 等服务提供方
* `management` — 管理、权限、群管或后台类插件
* `data` — 统计、记忆、知识库、导入导出等数据类插件
* `media` — 图片、语音、视频、表情等媒体处理
* `game` — 游戏或娱乐互动
* `integration` — 外部平台、搜索、Webhook 等集成
* `extension` — 通用扩展
* `other` — 其他

### display 展示元信息

`display.icon` 用于声明插件图标。该字段只影响 WebUI 展示，不参与插件运行时行为。

```json
{
  "display": {
    "icon": {
      "type": "local",
      "value": "assets/icon.png",
      "fallback": "package",
      "background": "#1f2937"
    }
  }
}
```

* `type`: `lucide`、`emoji` 或 `local`
* `value`: 图标值。`lucide` 使用图标名，`emoji` 使用单个表情或短文本，`local` 使用插件目录内相对路径
* `fallback`: 可选，图标加载失败时使用的 lucide 图标名
* `background`: 可选，图标背景色，格式为 `#RRGGBB`

不允许使用在线 URL 作为插件图标。本地图标仅支持 `.png`、`.jpg`、`.jpeg`、`.webp`、`.svg`，路径必须位于插件目录内，不能使用绝对路径、`..` 或符号链接。

### urls 链接集合

* **`repository`** · 必填 — 插件仓库地址，必须为 HTTP/HTTPS URL
* **`homepage`** · 可选 — 插件主页地址
* **`documentation`** · 可选 — 插件文档地址
* **`issues`** · 可选 — 插件问题反馈地址

### host\_application / sdk 版本区间

两者结构相同，为闭区间声明：

```json
{
  "min_version": "1.0.0",
  "max_version": "1.99.99"
}
```

* `min_version`：允许的最低版本（闭区间）
* `max_version`：允许的最高版本（闭区间）
* 两者均必须为严格三段式语义版本号（`X.Y.Z`）
* `min_version` 不能大于 `max_version`

Host 在握手阶段会校验当前版本是否落在声明区间内。若不兼容，插件将被阻止加载。

### i18n 国际化配置

* **`default_locale`** · 必填 — 默认语言代码（如 `zh-CN`）
* **`locales_path`** · 可选 — 语言资源文件目录路径
* **`supported_locales`** · 可选 — 支持的语言列表，不可包含空值和重复项。若非空，则 `default_locale` 必须存在于该列表中

### llm\_providers LLM Provider 声明

声明插件提供的 LLM Provider 能力，供其他插件通过 `ctx.llm` 代理调用。

* **`client_type`** · 必填 — Provider 唯一标识符，必须与 `@LLMProvider` 装饰器中声明的值完全一致
* **`name`** · 必填 — Provider 展示名称
* **`description`** · 可选 — Provider 功能描述
* **`version`** · 可选 · 默认 `"1.0.0"` — Provider 版本号

::: warning 双重声明要求
`llm_providers` 字段与 `@LLMProvider` 装饰器必须同时声明，且 `client_type` 必须完全匹配。若仅在一处声明，另一处缺失或不一致，插件将被阻止加载。
:::

::: danger 冲突加载策略
若两个插件声明了相同的 `client_type`，则**两个插件均被禁止加载**。请在设计 Provider 时使用唯一的前缀（如 `com.example.my-provider`）避免冲突。
:::

```json
{
  "llm_providers": [
    {
      "client_type": "my_custom_llm",
      "name": "My Custom LLM",
      "description": "A custom LLM provider",
      "version": "1.0.0"
    }
  ]
}
```

## 依赖声明

`dependencies` 数组支持两种类型的依赖，通过 `type` 字段区分：

### 插件级依赖

```json
{
  "type": "plugin",
  "id": "com.example.other-plugin",
  "version_spec": ">=1.0.0,<2.0.0"
}
```

* `id`：依赖插件的 ID，遵循与插件 ID 相同的格式规则
* `version_spec`：版本约束表达式，使用 PEP 440 风格（如 `>=1.0.0`、`~=1.0`）
* 不允许循环依赖或依赖自身
* 不允许重复声明同一个插件依赖

### Python 包依赖

```json
{
  "type": "python_package",
  "name": "httpx",
  "version_spec": ">=0.24.0"
}
```

* `name`：Python 包名，仅允许字母、数字、点号、下划线和横线
* `version_spec`：版本约束表达式

### 依赖解析流程

`PluginDependencyPipeline` 在 Host 侧统一执行依赖分析：

1. **扫描**：收集所有插件的 `_manifest.json`
2. **检测 Host 冲突**：若插件的 Python 包依赖与主程序的依赖约束无交集，则阻止加载
3. **检测插件间冲突**：若多个插件对同一 Python 包的版本约束互斥，则全部阻止加载
4. **自动安装**：对可加载插件缺失的 Python 依赖，优先使用 `uv pip install`，回退到 `pip install`
5. **拓扑排序**：根据跨 Supervisor 依赖关系决定 Runner 启动顺序，循环依赖将被拒绝

## 校验规则

Manifest 校验器（`ManifestValidator`）采用 Pydantic 严格模式，主要校验规则包括：

* **禁止多余字段**：不允许出现 `_manifest.json` 未声明的字段
* **ID 格式**：必须匹配 `^[a-z0-9]+(?:[.-][a-z0-9]+)+$`（如 `com.example.my-plugin`）
* **版本号格式**：必须为 `X.Y.Z` 三段式
* **URL 格式**：必须以 `http://` 或 `https://` 开头
* **不允许自依赖**：`dependencies` 中不能依赖自身
* **不允许重复依赖**：同一插件/包名只能声明一次

---

---
url: /manual/features/mcp.md
---

# MCP 工具集成

MaiBot 通过 MCP（Model Context Protocol）协议连接外部工具服务器，让 Maisaka 推理引擎获得超出对话本身的能力——浏览器自动化、文件操作、代码执行、API 调用，都可以通过 MCP 工具实现。

## 什么是 MCP？

MCP（Model Context Protocol）是一个开放协议标准，定义了 AI 应用如何与外部工具和服务进行连接与交互。在 MCP 的世界里，有**客户端**和**服务端**两种角色：

* **MCP 服务端（Server）**：暴露工具、提示词、资源等能力的服务程序。比如一个"浏览器自动化"服务端会提供网页截图、点击元素等工具。
* **MCP 客户端（Client）**：连接到服务端，发现并使用其能力的程序。**MaiBot 就是 MCP 客户端**。

::: tip 关键理解
MaiBot 自身不包含天气查询、股票查询、网页搜索等内置工具。这些能力全部来自你连接的 MCP 服务端——MaiBot 负责发现和调用它们，具体能做什么取决于你连了哪些服务器。
:::

MCP 工具对 Maisaka 推理引擎来说是**透明**的——MCP 工具和内置工具（`reply`、`wait`、`finish` 等）走同一个 ToolProvider 接口，规划器无需区分它们的来源。

## 架构概览

MCP 模块位于 `maibot/src/mcp_module/`，由以下核心组件构成：

```
mcp_module/
├── __init__.py          # 包入口，导出 MCPManager
├── manager.py           # MCPManager — 全局管理器
├── connection.py        # MCPConnection — 单服务器连接
├── provider.py          # MCPToolProvider — Maisaka 工具集成
├── host_llm_bridge.py   # MCPHostLLMBridge — Sampling → LLM 桥接
├── hooks.py             # MCPHostCallbacks — 宿主回调声明
├── models.py            # 结构化数据模型与转换
└── config.py            # TOML → 运行时配置转换
```

各组件职责：

* **MCPManager**（manager.py）— 全局管理器，管理所有服务器连接，提供统一的工具/Prompt/Resource 访问入口
* **MCPConnection**（connection.py）— 管理单个服务器的连接生命周期：连接 → 发现能力 → 调用 → 断开
* **MCPToolProvider**（provider.py）— 将 MCPManager 包装为标准 ToolProvider，对接 Maisaka 规划器
* **MCPHostLLMBridge**（host\_llm\_bridge.py）— 将 MCP Sampling 请求桥接到 MaiBot 自身的 LLM 调用链
* **MCPHostCallbacks**（hooks.py）— 宿主侧回调集合（Sampling、Elicitation、日志等）
* **Models**（models.py）— MCP SDK 原始对象与主程序内部模型的转换层
* **Config**（config.py）— 将 TOML 配置转换为类型化的 dataclass

## 四种能力类型

MCP 服务端可以暴露四种类型的能力：

### 1. 工具（Tools）

可执行函数，带有输入/输出 Schema。这是最常用的能力类型——MCP 工具会被注册到 MaiBot 的工具注册表，Maisaka 规划器可以像调用内置工具一样调用它们。

每个工具包含：

* **名称**（name）：全局唯一的工具标识符
* **描述**（description）：工具功能的自然语言描述
* **输入 Schema**（inputSchema）：JSON Schema 格式的参数定义
* **输出 Schema**（outputSchema）：可选的返回值结构定义
* **注解**（annotations）：可选的受众、优先级等元信息

### 2. 提示词（Prompts）

预定义的提示词模板，支持可选参数。可以被获取后用于构建对话上下文。

每个提示词包含：

* **名称**（name）：唯一标识
* **参数列表**（arguments）：可选的模板参数，每个参数可标记为必填
* **描述**（description）：模板功能说明

### 3. 资源（Resources）

通过 URI 访问的静态数据或文件。服务端暴露的资源有固定的 URI，客户端可以直接读取。

每个资源包含：

* **URI**：资源的唯一地址
* **名称/描述**：人类可读标识
* **MIME 类型**：资源的内容格式

### 4. 资源模板（ResourceTemplates）

参数化的资源 URI，使用 URI 模板语法（如 `file:///logs/{date}/report.md`）。客户端可以传入参数构造具体的资源 URI。

MCPManager 对四种能力分别维护独立的注册表，并在注册时进行冲突检测——如果两个服务器暴露了相同名称的工具或相同 URI 的资源，只有第一个会注册成功，后续的会被跳过并输出警告。

## 传输模式

MaiBot 支持三种 MCP 传输方式：

### stdio（本地子进程）

通过启动本地子进程来运行 MCP 服务器。MaiBot 使用 `command` 和 `args` 配置启动命令，通过标准输入/输出与服务器通信。

* **无需网络**，延迟最低
* 适合本地安装的工具（文件操作、浏览器自动化等）
* 推荐使用 `uvx`（来自 [uv](https://docs.astral.sh/uv/)）运行，自动管理依赖

```toml
[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]
```

::: tip 使用 uvx
`uvx` 是 Python 工具运行器，无需手动安装 MCP 服务器包，会自动从 PyPI 拉取并运行。确保你的环境中已安装 [uv](https://docs.astral.sh/uv/)。
:::

### streamable\_http（远程 HTTP）

通过 HTTP 连接远程 MCP 服务器端点。适合云服务或他人部署好的工具。

* **需要网络连接**
* 支持 Bearer Token 认证和自定义请求头
* 支持配置超时时间

```toml
[[mcp.servers]]
name = "remote-api"
transport = "streamable_http"
url = "https://mcp.example.com/api"

[mcp.servers.authorization]
mode = "bearer"
bearer_token = "sk-your-token"
```

### sse（Server-Sent Events）

通过 SSE 连接远程 MCP 服务器。适合需要长连接推送的远程服务。

* **需要网络连接**
* 支持 Bearer Token 认证和自定义请求头
* 支持配置超时时间

```toml
[[mcp.servers]]
name = "remote-sse"
transport = "sse"
url = "https://mcp.example.com/sse"

[mcp.servers.authorization]
mode = "bearer"
bearer_token = "sk-your-token"
```

MaiBot 内部使用 `mcp` Python SDK 的 `stdio_client`、`streamable_http_client` 和 `sse_client` 实现三种传输。

## 连接生命周期

MCP 模块的启动流程如下：

```
1. MCPManager.from_app_config()
   ├─ 读取 TOML 配置，转换为运行时 dataclass
   ├─ 检查 mcp SDK 是否已安装
   └─ 遍历所有 enabled 的服务器配置
       └─ 对每个服务器：
           ├─ 创建 MCPConnection
           ├─ 根据传输类型建立连接（stdio / streamable_http）
           ├─ 调用 session.initialize() 初始化 MCP 会话
           ├─ 加载服务端能力（分页获取 Tools/Prompts/Resources/Templates）
           └─ 注册到管理器，进行冲突检测
2. 全部完成后输出连接摘要
```

### 启动日志示例

连接成功时，日志中会看到：

```
✓ MCP 服务器 'playwright' 已连接 (工具 12 / Prompt 0 / 资源 0 / 模板 0)
```

如果某个服务器连接失败，会输出警告并跳过，不影响其他服务器。如果**所有**服务器都连接失败，MCPManager 返回 `None`，MCP 功能会被优雅地禁用，MaiBot 仍可正常运行。

### 分页加载

所有能力发现（list\_tools、list\_prompts、list\_resources、list\_resource\_templates）都支持基于游标（cursor）的分页。MaiBot 会自动循环获取所有页面，直到没有下一页为止。

## 工具集成与 Maisaka

### ToolProvider 接口

MCP 工具通过 `MCPToolProvider` 集成到 Maisaka。该类实现了标准的 `ToolProvider` 接口：

* `list_tools()` → 返回所有 MCP 工具的 `ToolSpec` 列表
* `invoke(invocation)` → 将工具调用请求路由到正确的 MCPConnection

MCPToolProvider 在 MaiBot 启动时注册到工具注册表：

```python
tool_registry.register_provider(MCPToolProvider(manager))
```

此后，Maisaka 规划器就能看到并使用这些 MCP 工具，与内置工具完全一致。

### 工具调用流程

```
Maisaka 规划器选择某个工具
  → ToolRegistry 查找对应 Provider
  → MCPToolProvider.invoke()
    → MCPManager.call_tool_invocation()
      → 根据 _tool_to_server 映射找到目标服务器
      → MCPConnection.call_tool()
        → MCP SDK session.call_tool()
        → 返回 ToolExecutionResult
```

### 名称冲突与保护

MCPManager 对工具名称有两层保护：

1. **内置工具保护**：   以下名称是 MaiBot 内置工具，MCP 工具不允许占用：

   * **`reply`** — 回复消息
   * **`no_action`** — 本轮不进行任何动作
   * **`stop`** — 停止
   * **`create_table`** — 创建表格
   * **`list_tables`** — 列出表格
   * **`view_table`** — 查看表格

   如果 MCP 服务器暴露了与内置工具同名的工具，该工具会被跳过并输出警告。

2. **跨服务器冲突检测**：如果两个 MCP 服务器暴露了同名工具，只有第一个注册的服务器会成功，后续的会被跳过。注册顺序与 `bot_config.toml` 中的配置顺序一致。

同样，Prompt 和 Resource 也有冲突检测机制（Prompt 按名称、Resource 按 URI、ResourceTemplate 按 URI 模板）。

## 客户端能力

除了使用 MCP 服务端暴露的能力，MaiBot 作为客户端也可以声明自身的能力，让服务端反过来利用。

### Roots（文件系统路径暴露）

允许你向 MCP 服务器暴露本地文件系统的部分路径，让服务器知道它可以读写哪些目录。

```toml
[mcp.client.roots]
enable = true

[[mcp.client.roots.items]]
enabled = true
uri = "file:///home/mai/data"
name = "麦麦的数据目录"
```

典型场景：连接文件系统 MCP 服务器（如 `@modelcontextprotocol/server-filesystem`）时，开启 Roots 后服务器就能知道你的数据目录在哪里，直接操作该目录下的文件。

### Sampling（采样 / LLM 调用桥接）

允许 MCP 服务端**反过来请求 MaiBot 调用大模型**来完成某些任务。这是一个高级的双向能力，通过 `MCPHostLLMBridge` 实现：

```
MCP 服务端发起 Sampling 请求
  → MCPConnection 收到 sampling_callback
    → MCPHostLLMBridge.handle_sampling_request()
      → 转换 MCP 消息格式为内部 Message 格式
      → 通过 LLMServiceClient 调用配置的模型任务
      → 将响应转换回 MCP CreateMessageResult
```

```toml
[mcp.client.sampling]
enable = true
task_name = "planner"     # 执行 Sampling 时使用的模型任务名
tool_support = true       # 允许 Sampling 中继续使用工具
```

::: warning ⚠️ Sampling 会消耗 Tokens
启用 Sampling 意味着 MCP 服务端可以触发 MaiBot 的模型调用，会产生额外的 API 费用。确保 `task_name` 指向一个已配置好的模型任务。
:::

### Elicitation（引导）

允许 MCP 服务端请求用户填写表单或在浏览器中打开 URL。目前 UI 层尚未完全实现，但能力声明已在协议层预留。

```toml
[mcp.client.elicitation]
enable = true
allow_form = true   # 允许表单模式
allow_url = false   # 允许 URL 模式
```

## 工具结果的内容类型

MCP 工具的返回结果可以包含多种内容类型，MaiBot 会统一处理：

* **`text`** — 纯文本结果，最常见的形式
* **`image`** — Base64 编码的图片（支持 PNG、JPEG、WebP、GIF）
* **`audio`** — 音频数据
* **`resource_link`** — 对 MCP 资源的引用（包含 URI 和描述）
* **`resource`** — 嵌入的资源内容（文本或二进制数据）

一次工具调用的结果可以包含多个内容项（例如同时返回文本说明和截图），MaiBot 会将它们组合后传递给 Maisaka。

## 前置条件

MCP 功能依赖 `mcp` Python 包，这是一个**可选依赖**——如果你不使用 MCP，不需要安装它。

如果 MaiBot 检测到配置了 MCP 服务器但未安装 `mcp` 包，启动时会提示：

```
⚠️ 发现 MCP 配置但未安装 mcp SDK，请运行: pip install mcp
```

安装方式：

```bash
pip install mcp
```

::: tip 无 MCP 也能运行
即使没有任何 MCP 配置或未安装 `mcp` 包，MaiBot 也会正常运行——MCP 是完全可选的增强功能。
:::

## 配置示例

以下是一些真实的 MCP 服务器配置示例。详细的配置字段说明请参阅 [MCP 配置](../configuration/mcp-config.md)。

### Playwright 浏览器自动化

```toml
[mcp]
enable = true

[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]
```

连接后，Maisaka 可以使用 Playwright 提供的浏览器自动化工具（导航网页、截图、点击元素等）。

### 文件系统服务器（配合 Roots）

```toml
[mcp]
enable = true

[mcp.client.roots]
enable = true

[[mcp.client.roots.items]]
enabled = true
uri = "file:///home/mai/data"
name = "数据目录"

[[mcp.servers]]
name = "filesystem"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/mai/data"]
```

通过 Roots 能力，文件系统服务器知道 MaiBot 允许访问的目录范围。

### GitHub 服务器（带 Token）

```toml
[mcp]
enable = true

[[mcp.servers]]
name = "github"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_your_token_here" }
```

GitHub MCP 服务器需要通过环境变量传入 Personal Access Token。

### 远程 HTTP 服务器（Bearer 认证）

```toml
[mcp]
enable = true

[[mcp.servers]]
name = "remote-api"
transport = "streamable_http"
url = "https://api.example.com/mcp"

[mcp.servers.authorization]
mode = "bearer"
bearer_token = "sk-your-api-token"
```

## 故障排除

### 检查启动日志

MaiBot 启动时会打印每个 MCP 服务器的连接状态。如果连接成功，会显示：

```
✓ MCP 服务器 'playwright' 已连接 (工具 12 / Prompt 0 / 资源 0 / 模板 0)
```

如果失败，会显示错误信息：

```
⚠️ MCP 服务器 'xxx' 连接失败: <错误详情>
```

### 常见问题

* **`⚠️ 发现 MCP 配置但未安装 mcp SDK`** — 未安装 `mcp` Python 包 → 运行 `pip install mcp`
* **工具名称冲突被跳过** — MCP 工具与内置工具或其他服务器工具同名 → 检查日志中的冲突警告，调整服务器配置
* **stdio 服务器启动失败** — `command` 路径不正确或命令不存在 → 确认命令在环境中可用，推荐使用 `uvx`
* **环境变量未生效** — `env` 配置格式错误 → 确认使用 `{ KEY = "value" }` 格式
* **远程服务器连接超时** — 网络问题或服务器不可达 → 检查网络连接，增大 `http_timeout_seconds`
* **Bearer Token 认证失败** — Token 无效或过期 → 重新获取 Token 并更新配置

### 独立验证 MCP 服务器

在连接 MaiBot 之前，可以使用 `mcp` SDK 自带的工具独立验证服务器是否正常工作：

```bash
mcp inspect uvx @playwright/mcp
```

这可以帮助你排除 MaiBot 之外的问题。

## 相关文档

* [MCP 配置](../configuration/mcp-config.md) — 完整的 TOML 配置字段说明
* [Bot 配置总览](../configuration/bot-config.md) — 全局配置参考
* [Maisaka 推理引擎](./maisaka-reasoning.md) — 了解 MCP 工具如何参与推理规划

---

---
url: /manual/configuration/mcp-config.md
---

# MCP 配置 🛠️

MCP（Model Context Protocol）让 MaiBot 能够连接外部工具，从"只会聊天"变成"又能说又能做"——查天气、搜新闻、读文件、调 API，全都可以。

本文详细介绍如何在 `bot_config.toml` 中配置 MCP。

::: tip 💡 先了解概念
如果你还不熟悉 MCP 是什么，建议先阅读 [MCP 功能概述](../features/mcp.md)，了解它能做什么。
:::

## 配置结构总览

MCP 配置位于 `bot_config.toml` 的 `[mcp]` 段落下，分为三个层级：

```toml
[mcp]
enable = true                         # 总开关

[mcp.client]                          # 客户端宿主能力
client_name = "MaiBot"
client_version = "1.0.0"

[mcp.client.roots]                    # Roots 能力（向服务端暴露本地路径）
enable = false

[mcp.client.sampling]                 # Sampling 能力（允许服务端调用你的模型）
enable = false
task_name = "planner"

[mcp.client.elicitation]              # Elicitation 能力（允许服务端请求用户填表）
enable = false
allow_form = true
allow_url = false

[[mcp.servers]]                       # MCP 服务器列表（可多个）
name = "my-server"
enabled = true
transport = "stdio"
command = "uvx"
args = ["some-mcp-server"]
env = { }
url = ""
headers = { }
http_timeout_seconds = 30.0
read_timeout_seconds = 300.0

[mcp.servers.authorization]
mode = "none"
bearer_token = ""
```

***

## 总开关 \[mcp]

* **`enable`** — 是否启用 MCP，设为 `false` 时所有 MCP 服务器都不会连接。默认开启

***

## 客户端能力 \[mcp.client]

这部分配置 MaiBot 作为 MCP **客户端**时，向服务端声明自己的能力。

### 基础信息

```toml
[mcp.client]
client_name = "MaiBot"
client_version = "1.0.0"
```

一般不需要改，除非你希望 MCP 服务端看到不同的客户端标识。

* **`client_name`** — 客户端实现名称。默认 `"MaiBot"`
* **`client_version`** — 客户端实现版本。默认 `"1.0.0"`

### Roots 能力 \[mcp.client.roots]

Roots 允许你向 MCP 服务器暴露本地文件系统路径，让服务器能读写这些路径下的文件。

```toml
[mcp.client.roots]
enable = true

[[mcp.client.roots.items]]
enabled = true
uri = "file:///home/mai/data"
name = "麦麦的数据目录"
```

* **`enable`** — 是否向 MCP 服务器暴露 Roots 能力。默认关闭
* **`items`** — Roots 列表。默认为空

每个 Root 项：

* **`enabled`** — 是否启用。默认开启
* **`uri`** — Root URI，通常为 `file://` 路径，启用时必填。默认为空
* **`name`** — 显示名称。默认为空

::: tip 💡 Roots 有什么用？
如果连接了一个文件系统 MCP 服务器（如 `@modelcontextprotocol/server-filesystem`），开启 Roots 后，服务器就能知道你的数据目录在哪，从而读写该目录下的文件。
:::

### Sampling 能力 \[mcp.client.sampling]

Sampling 允许 MCP 服务端**反过来请求 MaiBot 调用大模型**来完成某些任务。这是一个高级的双向能力。

```toml
[mcp.client.sampling]
enable = true
task_name = "planner"
include_context_support = false
tool_support = true
```

* **`enable`** — 是否启用 Sampling 能力声明。默认关闭
* **`task_name`** — 执行 Sampling 请求时使用的主程序模型任务名。默认 `"planner"`
* **`include_context_support`** — 是否声明支持 `includeContext` 非 `none` 语义。默认关闭
* **`tool_support`** — 是否声明支持在 Sampling 中继续使用工具。默认关闭

::: warning ⚠️ Sampling 会消耗 Tokens
启用 Sampling 意味着 MCP 服务端可以触发 MaiBot 的模型调用，会产生额外的 API 费用。确保 `task_name` 指向一个已配置好的模型任务。
:::

### Elicitation 能力 \[mcp.client.elicitation]

Elicitation 允许 MCP 服务端请求用户填写表单或在浏览器中打开 URL。

```toml
[mcp.client.elicitation]
enable = true
allow_form = true
allow_url = false
```

* **`enable`** — 是否启用 Elicitation 能力声明。默认关闭
* **`allow_form`** — 是否允许表单模式 Elicitation。默认开启
* **`allow_url`** — 是否允许 URL 模式 Elicitation。默认关闭

启用时至少需要允许一种模式（`allow_form` 或 `allow_url`）。

***

## 服务器配置 \[\[mcp.servers]]

这是最常用的部分——配置你想连接的 MCP 服务器。**可以配置多个**，每段 `[[mcp.servers]]` 对应一个服务器。

### 通用字段

```toml
[[mcp.servers]]
name = "playwright"
enabled = true
transport = "stdio"           # 或 "streamable_http"、"sse"
http_timeout_seconds = 30.0
read_timeout_seconds = 300.0
```

* **`name`** — **必填**。服务器名称，在同一配置中不能重复。默认为空
* **`enabled`** — 是否启用当前服务器。默认开启
* **`transport`** — 传输方式，`"stdio"`（默认）、`"streamable_http"`、`"sse"`
* **`http_timeout_seconds`** — HTTP 请求超时（秒）。默认 30.0
* **`read_timeout_seconds`** — 会话读取超时（秒）。默认 300.0

### stdio 模式

通过启动一个本地子进程来运行 MCP 服务器，适合本地安装的工具。关键字段：

* **`command`** — 启动命令，如 `uvx`、`npx`、`python`
* **`args`** — 命令参数列表
* **`env`** — 附加环境变量

#### 通过 uvx 运行（推荐）

uvx 是 [uv](https://docs.astral.sh/uv/) 自带的运行工具，自动管理依赖：

```toml
[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]
```

```toml
[[mcp.servers]]
name = "mcp-sse"
transport = "stdio"
command = "uvx"
args = ["mcp-sse-server", "--port", "8080"]
```

#### 通过 npx 运行

需要先安装 Node.js：

```toml
[[mcp.servers]]
name = "github"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_your_token_here" }
```

```toml
[[mcp.servers]]
name = "filesystem"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
```

#### 通过 Python 运行

```toml
[[mcp.servers]]
name = "my-python-mcp"
transport = "stdio"
command = "python"
args = ["-m", "my_mcp_server"]
env = { PYTHONUNBUFFERED = "1" }
```

### streamable\_http 模式

连接远程 MCP 服务（HTTP 端点），适合云服务或别人部署好的工具。关键字段：

* **`url`** — MCP 端点地址，必填
* **`headers`** — 附加 HTTP 请求头
* **`authorization`** — HTTP 认证配置

#### 无认证的远程服务

```toml
[[mcp.servers]]
name = "public-weather-mcp"
transport = "streamable_http"
url = "https://mcp.example.com/weather"

[mcp.servers.authorization]
mode = "none"
```

#### 带 Bearer Token 的远程服务

```toml
[[mcp.servers]]
name = "private-api-mcp"
transport = "streamable_http"
url = "https://api.example.com/mcp"
headers = { "X-Custom-Header" = "custom-value" }

[mcp.servers.authorization]
mode = "bearer"
bearer_token = "sk-your-bearer-token"
```

#### 带自定义请求头的远程服务

```toml
[[mcp.servers]]
name = "enterprise-mcp"
transport = "streamable_http"
url = "https://internal.example.com/mcp/v1"
headers = {
    "X-API-Key" = "your-api-key",
    "X-Tenant-ID" = "tenant-001",
}
```

***

## 完整示例

### 基础配置：只连接一个服务

```toml
[mcp]
enable = true

[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]
```

这是最简单的配置——只写了一行 `enable = true` 加一个服务，其余全部走默认值。

### 日常使用配置：两个服务 + 基础能力

```toml
[mcp]
enable = true

[mcp.client]
client_name = "MaiBot"
client_version = "1.0.0"

# 连接 Playwright（浏览器自动化）
[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]

# 连接文件系统服务器
[[mcp.servers]]
name = "filesystem"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
```

### 高级配置：启用 Sampling + Roots

```toml
[mcp]
enable = true

[mcp.client]
client_name = "MaiBot"
client_version = "1.0.0"

[mcp.client.roots]
enable = true

[[mcp.client.roots.items]]
enabled = true
uri = "file:///home/mai/data"
name = "数据目录"

[mcp.client.sampling]
enable = true
task_name = "planner"
tool_support = true

# 本地服务
[[mcp.servers]]
name = "playwright"
transport = "stdio"
command = "uvx"
args = ["@playwright/mcp"]

# 远程服务
[[mcp.servers]]
name = "weather-api"
transport = "streamable_http"
url = "https://mcp.example.com/weather"
```

***

## 常见问题

### Q: 配置后不生效？

保存配置后**必须重启 MaiBot** 才能生效。启动日志中会打印连接结果：

```
✓ MCP 服务器 'playwright' 已连接 (工具 12 / Prompt 0 / 资源 0 / 模板 0)
```

如果连接失败会有警告日志：

```
⚠️ MCP 服务器 'playwright' 连接失败: ...
```

### Q: 可以配置多少个服务？

没有硬性限制，但每个服务都会消耗资源。建议只配置你实际需要的。

### Q: 如何在网上找 MCP 服务？

* GitHub 上搜索 `modelcontextprotocol` 组织下的项目
* npm 上搜索 `@modelcontextprotocol` 包
* Python 社区有 `mcp` 生态的服务器实现

### Q: stdio、streamable\_http 和 sse 怎么选？

* **stdio**：本地安装的工具，延迟低，无需网络。适合文件操作、本地计算等
* **streamable\_http**：远程 HTTP 服务，需要网络。适合云 API、别人部署好的服务
* **sse**：远程 SSE（Server-Sent Events）服务，适合需要服务端推送事件的场景

### Q: 从哪里获取 API Token？

取决于你连接的服务。如果是 GitHub MCP，去 GitHub Settings → Developer settings → Personal access tokens 生成；如果是其他第三方服务，去对应服务的管理后台获取。

***

## 下一步

* 想了解 MCP 的概念和能做什么 → [MCP 功能概述](../features/mcp.md)
* 查看所有配置项 → [Bot 配置总览](./bot-config.md)

---

---
url: /develop/architecture/mcp-integration.md
---

# MCP 集成架构

本文基于 code-map 快照编写。

MaiBot 的 MCP 集成位于 `maibot/src/mcp_module/`，职责不是把某个固定能力写进主程序，而是把外部 MCP 服务器变成 MaiBot 工具系统的一部分。MCP 服务器提供工具、Prompt、Resource 等能力，MaiBot 作为 MCP 客户端连接这些服务器，发现能力，再把工具能力适配到统一 `ToolProvider` 接口。

本文聚焦开发视角的内部架构，不重复用户手册中关于配置和使用的说明。

## 1. 概述

**MCP 的角色** ：MCP 是 Model Context Protocol。MaiBot 在集成中扮演 MCP Client，外部服务扮演 MCP Server。MaiBot 不内置外部工具实现，只负责协议连接、能力发现、调用路由和结果归一化。

**能力来源** ：MCP Server 暴露的能力可以包括 Tools、Prompts、Resources 和 Resource Templates。当前对 Maisaka 推理引擎最直接生效的是 Tools，因为工具会被转换成 `ToolSpec` 并进入统一工具列表。

**集成目标** ：MCP 工具进入 MaiBot 后，不再以远程协议对象的形式被推理引擎消费，而是被转换成 `ToolSpec`、`ToolInvocation` 和 `ToolExecutionResult`。Maisaka 只面对统一工具抽象，不需要知道工具来自插件、内置模块还是 MCP。

**运行时关系** ：外部 MCP Server 是能力实现方，MaiBot 是协议客户端和工具调度方。工具执行时，MaiBot 通过 MCP SDK 的 `ClientSession.call_tool()` 发起远程调用，再把 MCP 返回内容转换成 MaiBot 内部结果。

**可选依赖** ：`mcp` Python SDK 是可选依赖。未安装 SDK 或未配置服务器时，主程序仍可运行。`MCPManager.from_app_config()` 会在无可用配置、SDK 缺失或全部连接失败时返回 `None`。

**边界** ：MCP 模块不替代 `tool-system`，也不替代 `MaisakaReasoningEngine`。它只做协议适配和生命周期管理，真正的工具注册、LLM 工具定义生成、调用路由由工具系统和推理引擎完成。

## 2. 架构图

```mermaid
flowchart TD
    subgraph "MaiBot 主进程"
        CFG["bot_config.toml<br/>MCP 配置"]
        MGR["MCP 连接管理器<br/>MCPManager"]
        CN1["MCPConnection<br/>stdio"]
        CN2["MCPConnection<br/>SSE"]
        CN3["MCPConnection<br/>Streamable HTTP"]
        TP["MCPToolProvider<br/>provider_name=mcp"]
        TR["ToolRegistry<br/>统一工具注册表"]
        ME["Maisaka 推理引擎<br/>Planner / Action Loop"]
        HLB["Host LLM 桥接<br/>MCPHostLLMBridge"]
        HK["Hook 集成点<br/>mcp.* hooks"]
        PR["插件 Hook 处理器"]
    end

    subgraph "MCP 协议边界"
        SDK["mcp SDK<br/>ClientSession"]
        S1["外部 MCP Server 1"]
        S2["外部 MCP Server 2"]
    end

    CFG --> MGR
    MGR --> CN1
    MGR --> CN2
    MGR --> CN3
    MGR --> TP
    TP --> TR
    TR --> ME
    ME -->|ToolInvocation| TR
    TR --> TP
    TP --> MGR
    MGR --> SDK
    CN1 --> S1
    CN2 --> S2
    CN3 --> S2
    SDK -->|initialize| S1
    SDK -->|tools/list| S1
    S1 -->|tool call result| SDK
    SDK -.->|sampling/createMessage| HLB
    HLB -->|LLMServiceClient| ME
    MGR --> HK
    HK --> PR
```

**MCP 连接管理器** ：架构图中对应 `MCPManager`。它维护多个 `MCPConnection`，保存工具名到服务器名的映射，并提供统一的工具、Prompt、Resource 访问入口。

**工具提供者** ：`MCPToolProvider` 把 `MCPManager` 包成标准 `ToolProvider`。它只实现 `list_tools()`、`invoke()` 和 `close()`，不直接理解 MCP 协议细节。

**Host LLM 桥接** ：`MCPHostLLMBridge` 处理 MCP Server 反向发起的 Sampling 请求。它把 MCP Sampling 消息转换为 MaiBot 内部消息，再调用 `LLMServiceClient`，最后把模型响应转换回 MCP `CreateMessageResult` 或 `CreateMessageResultWithTools`。

**Hook 集成** ：MCP 连接、断开和工具执行是插件 Hook 可以观察或拦截的边界。代码快照中协议层使用 `MCPHostCallbacks` 注入 `ClientSession`，插件命名 Hook 层可按 `mcp.server_connected`、`mcp.server_disconnected`、`mcp.tool_executed` 接入。

## 3. 核心概念

### 3.1 MCP Server 与 MCP Client

**MCP Server** ：外部能力提供方。它可以是本地子进程、远程 HTTP 服务或 SSE 服务。Server 通过 MCP 协议声明能力，并响应 `initialize`、`tools/list`、`tools/call` 等方法。

**MCP Client** ：MaiBot 侧协议客户端。`MCPConnection` 使用 `mcp` SDK 创建 `ClientSession`，负责传输连接、协议握手、能力发现和远程调用。

**JSON-RPC 2.0** ：MCP 请求和响应基于 JSON-RPC 2.0 语义。客户端发送方法调用，服务端返回 result 或 error。`stdio_filter.py` 对 stdio 传输做了额外防护，丢弃不符合 JSON-RPC 起始格式的 stdout 噪声行。

**stdio** ：本地子进程传输。MaiBot 根据配置中的 `command`、`args`、`env` 启动外部 MCP Server，并通过标准输入输出交换 JSON-RPC 消息。

**SSE** ：Server-Sent Events 远程传输。MaiBot 通过 `sse_client` 连接远程服务，适合长连接推送场景。

**Streamable HTTP** ：远程 HTTP 传输。MaiBot 通过 `streamable_http_client` 连接远程服务，并支持配置请求头、Bearer Token 和超时。

**认证** ：远程 HTTP 和 SSE 连接可通过 `build_http_headers()` 合并自定义 Header。Bearer 模式会自动写入 `Authorization: Bearer <token>`。

### 3.2 MCPConnectionManager，也就是 MCPManager

**架构称谓** ：用户手册和本文中的“MCP 连接管理器”对应源码里的 `MCPManager`。它不是 `mcp` SDK 的内置类，而是 MaiBot 为多服务器生命周期管理编写的管理层。

**配置入口** ：`MCPManager.from_app_config()` 读取官方 MCP 配置，调用 `build_mcp_server_runtime_configs()` 生成运行时服务器列表，再为每个服务器创建 `MCPConnection`。

**连接集合** ：`_connections` 保存已连接服务器，键是服务器名称，值是对应的 `MCPConnection`。

**路由映射** ：`_tool_to_server`、`_prompt_to_server`、`_resource_to_server`、`_resource_template_to_server` 分别保存能力名到服务器名的映射。工具调用时通过 `_tool_to_server` 找到目标服务器。

**冲突保护** ：MCP 工具不能占用 MaiBot 内置工具名，例如 `reply`、`no_action`、`stop`、`create_table`、`list_tables`、`view_table`。跨服务器同名工具只保留先注册的服务器。

**能力注册** ：每个连接成功后，管理器会注册工具、Prompt、Resource 和 Resource Template，并打印连接摘要。注册数量用于判断该服务器是否真正为 MaiBot 增加了可用能力。

**生命周期关闭** ：`MCPManager.close()` 会关闭所有 `MCPConnection`，并清空连接和映射表。`MCPToolProvider.close()` 会委托管理器关闭连接。

### 3.3 MCPConnection

**职责** ：`MCPConnection` 管理单个 MCP 服务器的连接生命周期。它封装传输层、`ClientSession`、服务端能力和远程调用。

**连接流程** ：`connect()` 进入异步上下文，建立传输，创建 `ClientSession`，执行 `session.initialize()`，保存 `server_capabilities` 和 `protocol_version`，然后加载服务端能力。

**能力发现** ：`_load_server_features()` 根据服务端能力声明决定是否调用 `list_tools()`、`list_prompts()`、`list_resources()` 和 `list_resource_templates()`。

**分页加载** ：工具、Prompt、Resource 和 Resource Template 都通过 cursor 分页读取。只要 `nextCursor` 存在，就继续请求下一页。

**可选能力容错** ：`list_resource_templates` 是可选方法。部分服务端未实现时返回 `METHOD_NOT_FOUND`，MaiBot 会按空集合处理，避免毁掉整个连接。

**远程调用** ：`call_tool()` 调用 `ClientSession.call_tool()`，再把 MCP 原始内容转换为 `ToolExecutionResult`。调用异常会被转换成失败结果，而不是直接抛出到推理循环。

**关闭行为** ：`close()` 释放异步上下文、HTTP 客户端和读写流，并清空当前连接状态。

### 3.4 MCPToolProvider

**职责** ：`MCPToolProvider` 是 MCP 到 `ToolProvider` 的适配器。它让 MCP 工具进入统一工具系统。

**provider\_name** ：`mcp`。

**provider\_type** ：`mcp`。

**list\_tools** ：`list_tools(context)` 忽略上下文，直接返回 `MCPManager.get_tool_specs()`。MCP 工具的统一声明已经在管理器层完成。

**invoke** ：`invoke(invocation, context)` 忽略上下文，直接调用 `MCPManager.call_tool_invocation(invocation)`。上下文在工具系统层仍有意义，但 MCP 调用本身只依赖工具名和参数。

**close** ：关闭 Provider 时会关闭 `MCPManager`，从而关闭所有 MCP 连接。

### 3.5 HostLLMBridge

**全称** ：`MCPHostLLMBridge`。

**触发来源** ：MCP Server 通过 `sampling/createMessage` 向 MaiBot 请求模型采样。这个请求来自外部服务，而不是 MaiBot 主动调用外部工具。

**桥接方式** ：Bridge 读取 MCP Sampling 参数，包括 `messages`、`systemPrompt`、`temperature`、`maxTokens`、`toolChoice` 和 `tools`，再调用主程序 `LLMServiceClient`。

**工具选择模式** ：支持 `auto`、`required`、`none`。`required` 且模型未返回工具调用时，会返回 MCP `ErrorData`。

**消息转换** ：MCP Sampling 的 `user`、`assistant`、`tool_result` 内容块会被转换为内部 `Message` 序列。图片、音频等不支持透传的内容会降级为文本占位。

**结果转换** ：`LLMResponseResult` 会被转换成 MCP `CreateMessageResult` 或 `CreateMessageResultWithTools`。如果模型返回工具调用，结果中包含 `ToolUseContent`。

**宿主回调** ：`MCPHostLLMBridge.build_callbacks()` 返回 `MCPHostCallbacks(sampling_callback=handle_sampling_request)`，由 `MCPConnection` 注入 `ClientSession`。

### 3.6 MCPHostCallbacks 与 Hook 边界

**MCPHostCallbacks** ：协议层宿主回调集合，字段包括 `sampling_callback`、`elicitation_callback`、`logging_callback`、`message_handler`。

**与插件 Hook 的区别** ：`MCPHostCallbacks` 注入给 MCP SDK 的 `ClientSession`，用于实现 MCP 协议中的宿主能力。插件 Hook 是 MaiBot 的命名 Hook 分发体系，需要由业务代码显式调用 `invoke_hook()`。

**server\_connected** ：适合在单个 MCP Server 完成连接、初始化并加载能力后触发。

**server\_disconnected** ：适合在连接关闭、连接失败清理或进程退出时触发。

**tool\_executed** ：适合在 MCP 工具调用完成并生成 `ToolExecutionResult` 后触发。

**推荐载荷** ：这些 Hook 可携带 `server_name`、`transport`、`tool_name`、`arguments`、`success`、`duration_ms`、`protocol_version`、`session_id` 和 `error_message`。

## 4. 关键流程

### 4.1 MCP 服务器连接

```mermaid
sequenceDiagram
    participant CFG as 官方配置
    participant M as MCPManager
    participant C as MCPConnection
    participant T as 传输客户端
    participant S as MCP Server
    participant SDK as ClientSession

    CFG->>M: from_app_config(mcp_config)
    M->>M: build_mcp_server_runtime_configs()
    loop 每个 enabled server
        M->>C: 创建 MCPConnection
        C->>T: stdio / SSE / streamable_http
        T->>SDK: 创建 ClientSession
        SDK->>S: initialize
        S-->>SDK: capabilities
        SDK->>S: list_tools / list_prompts / list_resources
        S-->>SDK: 能力列表
        SDK-->>C: 连接成功
        C-->>M: 返回连接对象
    end
```

**配置过滤** ：`build_mcp_server_runtime_configs()` 只返回启用且配置完整的服务器。未启用服务器不会进入连接流程。

**SDK 检测** ：如果 `mcp` SDK 未安装，管理器会打印警告并返回 `None`。

**失败隔离** ：单个服务器连接失败不会阻止其他服务器继续连接。全部服务器都失败时，`from_app_config()` 返回 `None`。

**初始化握手** ：`session.initialize()` 是协议能力协商点。握手成功后，`server_capabilities` 决定后续发现哪些能力。

### 4.2 工具发现

**发现方法** ：`tools/list` 对应 SDK 的 `session.list_tools(cursor=cursor)`。MaiBot 会循环读取所有分页，直到没有 `nextCursor`。

**原始对象** ：SDK 返回的工具对象包含 `name`、`title`、`description`、`inputSchema`、`outputSchema`、`icons`、`annotations`、`meta` 等字段。

**Schema 清洗** ：`MCPManager` 会把 `inputSchema` 和 `outputSchema` 转成普通 dict，并移除 `$schema`，避免模型层收到冗余字段。

**统一声明** ：工具对象被转换成 `ToolSpec`，其中 `provider_name="mcp"`、`provider_type="mcp"`，`metadata.server_name` 记录来源服务器。

**冲突处理** ：工具名先与内置工具名比较，再与已注册 MCP 工具名比较。冲突工具会被跳过，并输出警告。

### 4.3 注册到 ToolProvider

```mermaid
flowchart LR
    A[MCPConnection.tools] --> B[MCPManager.get_tool_specs]
    B --> C[ToolSpec provider_name=mcp]
    C --> D[MCPToolProvider.list_tools]
    D --> E[ToolRegistry.list_tools]
    E --> F[ToolDefinitionInput 列表]
```

**管理器内注册** ：`MCPManager` 在连接阶段建立 `_tool_to_server` 映射。这个映射不是 `ToolRegistry` 注册，而是 MCP 内部路由表。

**Provider 注册** ：`MaisakaRuntime._init_mcp()` 在管理器初始化成功且存在 MCP 工具后，调用 `ToolRegistry.register_provider(MCPToolProvider(self._mcp_manager))`。

**注册条件** ：MCP 配置存在、SDK 可用、至少一个服务器连接成功、至少发现一个 MCP 工具，这些条件满足后才会注册 Provider。

**Provider 标识** ：`MCPToolProvider` 使用 `provider_name="mcp"`。如果同名 Provider 已存在，`ToolRegistry` 会先移除旧 Provider，再注册新 Provider。

### 4.4 推理引擎调用

```mermaid
sequenceDiagram
    participant PL as Planner
    participant RE as ReasoningEngine
    participant TR as ToolRegistry
    participant TP as MCPToolProvider
    participant M as MCPManager
    participant C as MCPConnection
    participant S as MCP Server

    PL-->>RE: function_call / ToolCall
    RE->>RE: _build_tool_invocation()
    RE->>TR: invoke(ToolInvocation, ToolExecutionContext)
    TR->>TP: list_tools(ToolAvailabilityContext)
    TP-->>TR: ToolSpec 列表
    TR->>TP: invoke(invocation, context)
    TP->>M: call_tool_invocation(invocation)
    M->>C: call_tool(tool_name, arguments)
    C->>S: tools/call
    S-->>C: ToolResult
    C-->>M: ToolExecutionResult
    M-->>TP: ToolExecutionResult
    TP-->>TR: ToolExecutionResult
    TR-->>RE: ToolExecutionResult
    RE->>RE: 写入 ToolResultMessage
```

**模型输出** ：模型层可能把工具调用表达为 `function_call`、`ToolCall` 或等价结构。MaiBot 在 `_build_tool_invocation()` 中统一转换成 `ToolInvocation`。

**调用上下文** ：`_build_tool_execution_context()` 把会话、聊天流、群聊、用户、平台、锚点消息等信息放入 `ToolExecutionContext`。

**Provider 查找** ：`ToolRegistry.invoke()` 先根据当前可用性上下文收集 Provider 工具列表，再查找匹配 `invocation.tool_name` 的 Provider。

**MCP 路由** ：`MCPManager.call_tool_invocation()` 通过 `_tool_to_server` 找到目标服务器，再调用对应 `MCPConnection.call_tool()`。

**结果返回** ：`MCPConnection.call_tool()` 把 MCP 内容转换成 `ToolExecutionResult`，推理引擎再把结果追加到工具结果历史。

### 4.5 结果返回与历史写入

**文本结果** ：MCP 工具返回的 text 内容进入 `ToolExecutionResult.content`。

**多媒体结果** ：image、audio、resource、resource\_link 等内容进入 `content_items`。MaiBot 使用 `build_tool_content_items()` 完成 MCP 原始内容到统一内容项的转换。

**结构化结果** ：如果 MCP 返回 `structuredContent`，会写入 `ToolExecutionResult.structured_content`，供后续逻辑或模型摘要使用。

**错误结果** ：MCP 返回 `isError=True` 或调用异常时，`success=False`，错误信息写入 `error_message`。

**历史摘要** ：`ToolExecutionResult.get_history_content()` 优先使用 `content`，其次使用 `content_items` 的摘要，再其次使用结构化内容 JSON，最后才使用错误信息。

## 5. 与工具抽象层 tool-system 的交互

**统一入口** ：`MCPToolProvider` 实现 `ToolProvider` Protocol，因此可以被 `ToolRegistry` 和插件、内置 Provider 同等对待。

**声明转换** ：MCP 原始工具对象先由 `MCPManager.get_tool_specs()` 转换为 `ToolSpec`。这一步包含名称、描述、参数 Schema、输出 Schema、图标、注解和元数据。

**调用转换** ：`ToolInvocation` 是统一调用请求。MCP Provider 不需要理解模型 API 的原始 function call 结构，只需要读取 `tool_name` 和 `arguments`。

**结果转换** ：MCP 工具结果被转换成 `ToolExecutionResult`。工具系统不关心结果是本地 Python 函数返回，还是远程 MCP Server 返回。

**去重规则** ：`ToolRegistry.list_tools()` 按 Provider 顺序收集工具，并跳过重复工具名。MCP 内部也做冲突检测，因此同服务器和跨服务器的冲突会被尽量提前处理。

**Provider 顺序** ：内置 Provider 和插件 Provider 是默认注册路径。MCP Provider 只在 `_init_mcp()` 成功初始化后注册，因此不会在没有 MCP 工具时占用工具列表。

**旧模型兼容** ：`MCPManager.get_openai_tools()` 可把 MCP 工具定义转换成旧模型层使用的 function tool 格式。新路径更推荐走 `ToolRegistry.get_llm_definitions()`。

## 6. 与 Maisaka 的交互

### 6.1 工具列表进入推理引擎

**初始化位置** ：`MaisakaRuntime._init_mcp()` 负责创建 Host LLM Bridge、MCPManager 和 MCPToolProvider。

**注册顺序** ：初始化成功后，`MCPToolProvider` 注册到 `_tool_registry`。之后 Planner 构造工具定义时，`ToolRegistry.list_tools()` 会包含 MCP 工具。

**可见性策略** ：`_build_action_tool_definitions()` 会把非内置工具放入可见列表或 deferred 池。MCP 工具如果没有显式 `metadata.visibility="visible"`，默认进入 deferred 池，后续可通过 `tool_search` 发现。

**LLM 定义** ：可见工具会通过 `ToolSpec.to_llm_definition()` 转成模型层工具定义。MCP 工具的描述、参数 Schema 和名称与其他工具使用同一格式。

**上下文过滤** ：工具列表构造时会传入 `ToolAvailabilityContext`。MCP Provider 当前不基于上下文过滤工具，但统一工具层仍保留上下文参数，方便未来扩展。

### 6.2 function\_call 路由

**模型层概念** ：`function_call` 是模型响应中的工具调用表达。MaiBot 内部统一使用 `ToolCall` 表示模型输出，再转换成 `ToolInvocation`。

**调用构建** ：`_build_tool_invocation(tool_call, latest_thought)` 从模型工具调用中提取 `func_name`、`args`、`call_id`，并补充 `session_id`、`stream_id` 和 `reasoning`。

**执行入口** ：`_invoke_tool_call()` 或批量 `_handle_tool_calls()` 会把 `ToolInvocation` 交给 `ToolRegistry.invoke()`。

**Provider 定位** ：`ToolRegistry.invoke()` 会重新按可用性上下文收集工具声明，找到声明包含目标工具名的 Provider。MCP 工具的 `provider_name` 是 `mcp`，因此会被路由到 `MCPToolProvider`。

**远程执行** ：`MCPToolProvider.invoke()` 委托 `MCPManager.call_tool_invocation()`，管理器再通过 `_tool_to_server` 找到对应 `MCPConnection`。

**结果回写** ：`MCPConnection` 返回 `ToolExecutionResult` 后，推理引擎存储工具记录，并把结果追加为 `ToolResultMessage` 或等价历史内容。

### 6.3 与 Host LLM 桥接的关系

**双向能力** ：MCP 集成不仅让 MaiBot 调用外部工具，也允许 MCP Server 请求 MaiBot 调用模型。这个方向通过 `MCPHostLLMBridge` 实现。

**Sampling 配置** ：`mcp.client.sampling.enable` 决定是否声明采样能力，`task_name` 决定使用哪个模型任务，`tool_support` 决定是否允许 Sampling 中继续使用工具。

**工具定义注入** ：当 MCP Server 在 Sampling 请求中附带 `tools` 时，Bridge 会把 MCP 工具定义转换为 `ToolDefinitionInput`，传给 `LLMServiceClient`。

**工具调用回传** ：如果模型响应包含工具调用，Bridge 会返回 `CreateMessageResultWithTools`，其中包含 `ToolUseContent`。MCP Server 后续可以继续处理这些工具调用结果。

**错误隔离** ：Bridge 捕获异常并返回 MCP `ErrorData`，避免一次 Sampling 失败直接破坏 MCP 连接。

## 7. Hook 集成点

### 7.1 当前协议层 Hook

**MCPHostCallbacks** ：这是 MCP SDK 的宿主能力回调，不是插件 Hook 规格。它被传入 `MCPConnection`，再由 `ClientSession` 使用。

**sampling\_callback** ：处理 MCP Server 发起的 Sampling 请求。当前实现由 `MCPHostLLMBridge.handle_sampling_request()` 提供。

**elicitation\_callback** ：保留给 MCP Elicitation 能力。当前配置和连接层支持声明，但具体用户交互能力仍需业务层补齐。

**logging\_callback** ：可用于消费 MCP Server 日志。当前 `MCPHostCallbacks` 预留字段，默认不注入。

**message\_handler** ：可用于处理自定义 MCP 消息。当前 `MCPHostCallbacks` 预留字段，默认不注入。

### 7.2 插件命名 Hook 设计点

**集成原则** ：如果要把 MCP 生命周期暴露给插件 Hook，应在连接和工具调用的边界调用 `PluginRuntimeManager.invoke_hook()`。这些 Hook 不属于 MCP 协议本身，而是 MaiBot 运行时的可观测性扩展。

**server\_connected** ：建议在单个 `MCPConnection.connect()` 成功、能力加载完成、管理器记录连接后触发。此时 payload 已经包含稳定工具数量和能力摘要。

**server\_disconnected** ：建议在连接关闭、连接失败清理或管理器关闭时触发。即使连接从未成功初始化，也可以在清理阶段发出断开事件，方便监控工具统计连接失败。

**tool\_executed** ：建议在 `MCPConnection.call_tool()` 返回 `ToolExecutionResult` 后触发。此时可以准确记录工具名、服务器名、成功状态、耗时和错误信息。

**server\_connected 载荷** ：`server_name`、`transport`、`protocol_version`、`tool_count`、`prompt_count`、`resource_count`、`resource_template_count`。

**server\_disconnected 载荷** ：`server_name`、`transport`、`reason`、`had_session`、`protocol_version`、`session_id`。

**tool\_executed 载荷** ：`server_name`、`tool_name`、`arguments`、`success`、`duration_ms`、`content_length`、`error_message`、`metadata`。

**阻塞与观察** ：`server_connected` 和 `server_disconnected` 通常适合 observe 处理器。`tool_executed` 如果允许记录审计或改写结果，可以设计为 blocking 处理器，但需要谨慎避免影响推理循环性能。

**错误处理** ：Hook 调用失败不应破坏 MCP 连接生命周期。建议记录错误，并把异常转换为 Hook dispatch error，而不是让连接关闭或工具调用失败。

## 8. 数据模型转换

**ToolSpec** ：MCP 工具声明转换为统一 `ToolSpec`。`provider_name` 和 `provider_type` 固定为 `mcp`，`metadata.server_name` 保留来源服务器。

**ToolIcon** ：MCP 图标对象转换为 `ToolIcon`，包含 `src`、`mime_type`、`sizes`。

**ToolAnnotation** ：MCP 注解对象转换为 `ToolAnnotation`，包含 `audience`、`priority`、`metadata`。

**ToolContentItem** ：MCP 工具结果内容块转换为统一内容项。支持 `text`、`image`、`audio`、`resource_link`、`resource`、`binary` 和 `unknown`。

**PromptSpec** ：MCP Prompt 转换为 `MCPPromptSpec`，包含参数列表、图标和元数据。

**ResourceSpec** ：MCP Resource 转换为 `MCPResourceSpec`，包含 URI、名称、MIME、大小、图标和注解。

**ResourceTemplateSpec** ：MCP Resource Template 转换为 `MCPResourceTemplateSpec`，保留 URI 模板、名称、描述和元数据。

**结构化元数据** ：`_dump_model_metadata()` 会提取 MCP 原始对象中的 `meta` 字段。该字段可进入 `ToolSpec.metadata` 或注解 metadata。

## 9. 运行时配置

**配置转换** ：`config.py` 将官方 MCP 配置转换成运行时 dataclass，避免连接层直接读取配置模型。

**服务器配置** ：`MCPServerRuntimeConfig` 保存服务器名称、传输类型、命令、参数、环境变量、URL、Header、超时和认证信息。

**客户端配置** ：`MCPClientRuntimeConfig` 保存客户端名称、版本、Roots、Sampling、Elicitation 等宿主能力配置。

**传输类型推断** ：`transport_type` 根据 `transport`、`command` 和 `url` 判断。stdio 需要 command，HTTP 和 SSE 需要 url。

**HTTP Header** ：`build_http_headers()` 合并用户配置 Header 和 Bearer Token。Bearer Token 会被自动写入标准 Authorization Header。

**Roots** ：Roots 由 `_build_list_roots_callback()` 暴露给 MCP Server。只有启用 Roots 且配置了有效 URI 时，客户端才声明该能力。

**Sampling 能力声明** ：只有启用 Sampling 且提供 `sampling_callback` 时，`ClientSession` 才会收到 sampling 回调和 sampling capabilities。

## 10. 容错与安全边界

**stdio 噪声过滤** ：MCP 协议要求 stdout 只承载 JSON-RPC 消息。第三方服务器有时会把启动横幅写到 stdout，MaiBot 使用 `tolerant_stdio_client()` 丢弃非 JSON 行，避免初始化失败。

**异常隔离** ：连接失败、工具调用失败、Sampling 调用失败都应在各自边界转换为日志或失败结果，避免单个 MCP Server 影响主程序稳定性。

**名称保护** ：内置工具名不能被 MCP 工具占用。这是防止模型错误路由到外部工具的关键保护。

**跨服务器冲突** ：同名 MCP 工具只保留先注册的服务器。配置顺序决定了保留顺序。

**资源释放** ：所有 MCP 连接都应通过 `MCPManager.close()` 或 `MCPToolProvider.close()` 释放。进程退出或运行时停止时应确保 close 被调用。

**审计建议** ：如果启用 `mcp.tool_executed`，建议记录工具名、服务器名、成功状态、耗时和错误摘要。参数和结果可能包含敏感信息，写入日志前应做脱敏。

## 11. 与其他文档的边界

**用户手册** ：`docs/manual/features/mcp.md` 面向使用者，说明 MCP 是什么、如何配置、如何排障。本文不重复这些内容。

**工具系统架构** ：`docs/develop/architecture/tool-system.md` 说明统一 `ToolProvider`、`ToolRegistry` 和工具调用模型。本文只说明 MCP 如何接入这一层。

**Maisaka 推理引擎** ：`docs/develop/architecture/maisaka-reasoning.md` 说明推理循环、Timing Gate、Planner 和工具执行流程。本文只说明 MCP 工具如何进入工具列表和 function\_call 路由。

**插件开发文档** ：插件 Hook 的具体写法属于插件开发文档范围。本文只定义 MCP 相关 Hook 的触发边界和推荐载荷。

## 12. 总结

**MCP 集成的本质** ：MCP 模块把外部 MCP Server 的能力转成 MaiBot 内部工具能力。外部服务实现工具，MaiBot 负责连接、发现、注册、调用和结果归一化。

**核心链路** ：`MCPManager` 管理连接，`MCPConnection` 执行协议交互，`MCPToolProvider` 接入工具系统，`ToolRegistry` 路由到 Provider，`MaisakaReasoningEngine` 消费工具结果。

**关键扩展点** ：MCP 工具可以扩展 MaiBot 的工具边界，Host LLM Bridge 可以支持 MCP Server 反向请求模型能力，`mcp.*` Hooks 可以为连接和工具执行提供可观测性与扩展能力。

**实现约束** ：MCP 是可选运行时依赖，工具名必须避免冲突，远程调用必须隔离失败，连接资源必须显式释放。

---

---
url: /develop/adapter-dev/platform-io.md
---

# PlatformIO 驱动

PlatformIO 驱动是 MaiBot 平台 IO 层的核心抽象。本文档详细介绍驱动的接口定义、核心类型，以及如何实现和注册一个自定义驱动。

## PlatformIODriver 基类

`PlatformIODriver`（定义在 `src/platform_io/drivers/base.py`）是所有平台 IO 驱动必须继承的抽象基类：

```python
class PlatformIODriver(ABC):
    def __init__(self, descriptor: DriverDescriptor) -> None: ...

    @property
    def descriptor(self) -> DriverDescriptor: ...

    @property
    def driver_id(self) -> str: ...

    def set_inbound_handler(self, handler: InboundHandler) -> None: ...
    def clear_inbound_handler(self) -> None: ...

    async def emit_inbound(self, envelope: InboundMessageEnvelope) -> bool: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    @abstractmethod
    async def send_message(
        self, message: "SessionMessage", route_key: RouteKey, metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryReceipt: ...
```

### 必须实现的方法

* **`send_message(message, route_key, metadata)`** — 通过具体驱动发送消息，返回 `DeliveryReceipt`。这是唯一必须实现的抽象方法

### 可选覆盖的钩子

* **`start()`** — 启动驱动生命周期（默认空实现）
* **`stop()`** — 停止驱动生命周期（默认空实现）

### 入站消息上报

驱动收到外部平台消息后，需构造 `InboundMessageEnvelope` 并调用 `emit_inbound()` 上报：

```python
envelope = InboundMessageEnvelope(
    route_key=RouteKey(platform="qq", account_id="123456"),
    driver_id=self.driver_id,
    driver_kind=self.descriptor.kind,
    external_message_id="platform_msg_id",
    session_message=parsed_message,
)
accepted = await self.emit_inbound(envelope)
```

`emit_inbound` 返回 `True` 表示消息被 Broker 接受并继续转发，`False` 表示被拒绝（未配置入站回调或消息被去重过滤）。

## 核心类型

### RouteKey — 路由键

`RouteKey` 是路由决策的唯一键，采用三层结构：

```python
@dataclass(frozen=True, slots=True)
class RouteKey:
    platform: str                           # 平台名称，如 "qq"、"discord"
    account_id: Optional[str] = None        # 机器人账号 ID
    scope: Optional[str] = None             # 额外路由作用域
```

路由解析遵循**从最具体到最宽泛**的回退顺序：`platform + account_id + scope` → `platform + account_id` → `platform + scope` → `platform`。通过 `resolution_order()` 方法可获取完整回退链：

```python
key = RouteKey(platform="qq", account_id="123", scope="group_456")
key.resolution_order()
# → [RouteKey("qq", "123", "group_456"), RouteKey("qq", "123", None), RouteKey("qq", None, "group_456"), RouteKey("qq", None, None)]
```

`to_dedupe_scope()` 方法生成跨驱动共享的去重作用域字符串，格式为 `platform:account_id:scope`。

### InboundMessageEnvelope — 入站消息封装

```python
@dataclass(slots=True)
class InboundMessageEnvelope:
    route_key: RouteKey                                # 入站路由键
    driver_id: str                                     # 产出驱动的 ID
    driver_kind: DriverKind                            # 驱动类型
    external_message_id: Optional[str] = None          # 平台侧消息 ID（用于去重）
    dedupe_key: Optional[str] = None                   # 显式去重键
    session_message: Optional["SessionMessage"] = None # 已规范化的消息
    payload: Optional[Dict[str, Any]] = None           # 原始字典载荷
    metadata: Dict[str, Any] = field(default_factory=dict)
```

去重键的优先级为：`dedupe_key` > `external_message_id` > `session_message.message_id`。Broker 不会根据 `payload` 内容猜测去重键，以避免将内容相同的不同消息误判为重复。

### DeliveryReceipt — 出站回执

```python
@dataclass(slots=True)
class DeliveryReceipt:
    internal_message_id: str                    # 内部消息 ID
    route_key: RouteKey                         # 投递路由键
    status: DeliveryStatus                      # 投递状态
    driver_id: Optional[str] = None             # 处理驱动的 ID
    driver_kind: Optional[DriverKind] = None    # 处理驱动的类型
    external_message_id: Optional[str] = None   # 平台侧消息 ID
    error: Optional[str] = None                 # 错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)
```

`DeliveryStatus` 枚举值：

* **`PENDING`** — 待发送
* **`SENT`** — 已发送
* **`FAILED`** — 发送失败
* **`DROPPED`** — 已丢弃

### DriverDescriptor — 驱动描述

```python
@dataclass(frozen=True, slots=True)
class DriverDescriptor:
    driver_id: str                                # 全局唯一驱动 ID
    kind: DriverKind                              # 驱动类型（LEGACY / PLUGIN）
    platform: str                                 # 平台名称
    account_id: Optional[str] = None              # 账号 ID
    scope: Optional[str] = None                   # 路由作用域
    plugin_id: Optional[str] = None               # 关联的插件 ID
    metadata: Dict[str, Any] = field(default_factory=dict)
```

`DriverKind` 枚举区分驱动来源：`LEGACY` 表示内置驱动，`PLUGIN` 表示插件提供的驱动。

## 实现并注册驱动

### 完整示例

```python
from maibot.src.platform_io.drivers.base import PlatformIODriver
from maibot.src.platform_io.types import (
    DeliveryReceipt, DeliveryStatus, DriverDescriptor, DriverKind,
    InboundMessageEnvelope, RouteKey, RouteBinding,
)

class MyDriver(PlatformIODriver):
    async def start(self) -> None:
        # 初始化连接
        self._connection = await connect_to_platform()

    async def stop(self) -> None:
        # 清理连接
        await self._connection.close()

    async def send_message(self, message, route_key, metadata=None):
        try:
            platform_msg_id = await self._connection.send(
                target=route_key.account_id,
                content=message.plain_text,
            )
            return DeliveryReceipt(
                internal_message_id=message.message_id,
                route_key=route_key,
                status=DeliveryStatus.SENT,
                driver_id=self.driver_id,
                driver_kind=self.descriptor.kind,
                external_message_id=platform_msg_id,
            )
        except Exception as exc:
            return DeliveryReceipt(
                internal_message_id=message.message_id,
                route_key=route_key,
                status=DeliveryStatus.FAILED,
                driver_id=self.driver_id,
                driver_kind=self.descriptor.kind,
                error=str(exc),
            )
```

### 注册与路由绑定

```python
from maibot.src.platform_io.manager import get_platform_io_manager

manager = get_platform_io_manager()

# 描述符
descriptor = DriverDescriptor(
    driver_id="my_driver.discord",
    kind=DriverKind.PLUGIN,
    platform="discord",
)

# 注册
driver = MyDriver(descriptor)
await manager.add_driver(driver)

# 绑定发送路由
manager.bind_send_route(RouteBinding(
    route_key=descriptor.route_key,
    driver_id=driver.driver_id,
    driver_kind=DriverKind.PLUGIN,
))

# 绑定接收路由
manager.bind_receive_route(RouteBinding(
    route_key=descriptor.route_key,
    driver_id=driver.driver_id,
    driver_kind=DriverKind.PLUGIN,
))
```

Broker 运行中使用 `add_driver` / `remove_driver`，未运行时使用 `register_driver` / `unregister_driver`。路由绑定支持通过 `priority` 字段实现同一路由键下多驱动的优先级排序。

---

---
url: /develop/architecture/prompt-templates.md
---

本文基于 code-map 快照编写。

# Prompt 模板系统

Prompt 模板系统是 MaiBot 赋予 AI 角色灵魂的核心机制。它将 LLM 的指令（System Prompt）、任务逻辑（Task Templates）与运行时数据（Runtime Parameters）解耦，使得开发者可以在不修改代码的情况下，通过编辑 `.prompt` 文件快速调整 AI 的行为模式、回复风格和推理逻辑。

Prompt 模板系统在 MaiBot 整体架构中属于基础服务层，与 Config 配置模块、i18n 国际化模块和 Maisaka 推理引擎深度协作。它向下屏蔽了文件系统和多语言路由的复杂性，向上为 ChatLoopService、学习模块等消费者提供统一的模板获取接口。通过这套系统，MaiBot 能够在多种语言环境下保持一致的回复质量，同时支持运行时的行为热更新。

## 架构概述

Prompt 系统的核心目标是提供一个可国际化、可热重载、且支持复杂变量注入的模板管理机制。它将静态的模板文件转换为可动态渲染的 Prompt 实例，并允许通过上下文构造函数将实时的业务数据注入到模板中。整个系统在 MaiBot 中承担着"AI 行为定义层"的角色——它决定了 LLM 以何种身份、何种风格、何种逻辑框架与用户交互。

系统的整体架构分为四层：

* **存储层**：负责模板文件的物理存储，划分为内置模板目录（`/prompts/`）和自定义模板目录（`/data/custom_prompts/`），按 locale 子目录组织，支持 UTF-8 编码的纯文本 `.prompt` 文件。
* **管理层**：`PromptManager` 作为中央控制器，维护模板的注册、缓存、版本检测和热重载逻辑，通过版本号计数器实现增量更新。
* **渲染引擎层**：接收 `Prompt` 实例和上下文构造函数，执行异步变量替换与递归渲染，输出纯文本 Prompt。渲染管线基于 `asyncio` 实现并发解析。
* **消费者层**：以 Maisaka 的 `ChatLoopService` 为代表的上游模块，通过 `PromptManager.get_prompt()` 获取渲染后的 Prompt 字符串，用于构建 LLM 请求的 System Message 和任务指令。

各层之间通过明确的接口边界解耦：管理层不关心模板文件的存储格式细节，渲染引擎不关心模板的来源与生命周期，消费者不关心渲染引擎的内部实现。这种分层设计确保了每个关注点可以被独立修改和测试。

数据流向为单向管道：模板文件从存储层流向管理层完成注册与缓存，再从管理层流向渲染引擎进行变量注入与渲染，最终渲染结果输出给消费者层。每一层只与相邻层交互，层间不产生循环依赖。

## 架构图

```mermaid
flowchart TD
    subgraph Storage [存储层]
        BuiltIn[内置模板目录 /prompts/locale/*.prompt]
        Custom[自定义模板目录 /data/custom_prompts/locale/*.prompt]
    end

    subgraph Manager [Prompt 管理层]
        PM[PromptManager]
        Cache[模板缓存 & 版本检测]
        Loader[PromptI18n 加载器]
    end

    subgraph Engine [渲染引擎]
        PI[Prompt 实例]
        VarReplacer[变量替换引擎]
        CtxFunc[上下文构造函数]
    end

    subgraph Consumers [消费者]
        ChatLoop[ChatLoopService]
        Maisaka[Maisaka 推理引擎]
        Learn[学习/分析模块]
    end

    BuiltIn --> Loader
    Custom --> Loader
    Loader --> PM
    PM --> Cache
    PM --> PI
    PI --> VarReplacer
    CtxFunc --> VarReplacer
    VarReplacer --> Consumers
```

## 核心概念

**PromptManager** — 模板系统的中央控制台。
负责 Prompt 实例的生命周期管理，包括注册、加载、替换和保存。它维护一个全局的 Prompt 实例字典，并实现了基于文件版本号的自动热重载机制，确保在修改 `.prompt` 文件后无需重启即可生效。

**热重载实现细节**
PromptManager 的热重载基于文件修改时间（mtime）与版本号计数器协同工作。每次 `load_prompts()` 被调用时，系统会遍历模板目录中的所有 `.prompt` 文件，计算文件的 `mtime` 哈希并与缓存中的版本号对比。若检测到变更，则仅重新加载发生变更的模板文件，而非全量刷新。这种增量更新策略在大型多语言部署场景下有效降低了 I/O 开销。版本号计数器是一个单调递增的整数值，每次检测到任何文件变更时自增，消费者可通过对比前后版本号快速判断是否需要重新获取模板。

**缓存失效策略**
模板缓存遵循以下失效规则：

* **Locale 切换**：当 `common.i18n.set_locale()` 被调用时，`PromptManager` 标记所有缓存为 stale，下次 `get_prompt()` 调用触发全量重新加载并重建 locale → 文件路径映射表。
* **文件修改检测**：通过周期性的版本号轮询（非实时文件监听，无 inotify 依赖）检测模板文件变更。检测间隔由 `Config` 模块中的 `prompt_reload_interval` 参数控制，默认值为 60 秒。
* **显式刷新**：开发者可通过 `PromptManager.reload_prompts()` 强制刷新缓存，适用于部署后的模板热修复场景，调用后将清空全部缓存并重新扫描模板目录。
* **模板不存在回退**：当请求的模板名称在当前 locale 下不存在时，系统自动回退至默认 locale（`en-US`）查找，若仍不存在则抛出 `PromptNotFoundError`。

**Prompt 实例** — 模板的包装对象。
每个 `Prompt` 对象持有原始模板字符串。为了保证线程安全和会话隔离，`PromptManager.get_prompt()` 总是返回一个克隆实例。克隆实例允许针对特定会话注入临时的上下文函数，而不会污染全局模板。克隆操作采用浅拷贝策略——原始模板字符串为不可变对象，因此无需深拷贝；但上下文函数字典在每个克隆实例上独立维护，避免并发写入冲突。

**模板文件结构** — 以 `.prompt` 为后缀的纯文本文件。
模板文件采用简单的占位符语法 {{variable}}。在系统内部，这些占位符在渲染前会被转换为 Python 的 `string.Formatter` 语法。模板文件按语言目录（如 `zh-CN`, `en-US`）组织，支持通过自定义目录进行优先级覆盖。模板加载的完整优先级链为：`自定义/目标 locale` → `自定义/回退 locale` → `内置/目标 locale` → `内置/回退 locale`，其中回退 locale 固定为 `en-US`。文件编码要求为 UTF-8（无 BOM），文件名即为模板的逻辑名称（不含 `.prompt` 后缀）。

**变量替换机制** — 递归渲染引擎。
系统支持三种层级的变量解析优先级：

* **内部构造函数**：绑定在特定 Prompt 实例上的函数，优先度最高，仅在当前克隆实例的生命周期内有效。
* **全局构造函数**：通过 `add_context_construct_function` 注册的全局通用函数，对所有 Prompt 实例生效。
* **嵌套 Prompt**：如果变量名指向另一个已注册的 Prompt，引擎将递归渲染该 Prompt 并将其结果注入当前位置。嵌套深度受 `recursive_level > 10` 限制保护。

变量解析失败时（如未注册的变量名且无对应构造函数），渲染引擎抛出 `ContextFunctionNotFoundError`，该异常会被上层 `ChatLoopService` 捕获并记录告警日志，但不会中断整个推理循环。

**多语言支持** — 基于 locale 的动态路由。
系统在加载模板时会调用 `common.i18n` 的 `get_locale()`。加载顺序为：`自定义目录/当前 locale` → `自定义目录/默认 locale` → `内置目录/当前 locale` → `内置目录/默认 locale`。模板加载器 `PromptI18n` 在初始化时会建立 locale → 文件路径的映射表，避免每次加载时重复扫描目录，并将映射关系缓存在内存中以加速后续访问。当某个 locale 的模板目录不存在时，加载器会自动跳过该目录并记录 debug 级别的日志。

## 关键流程

**模板加载流程**

1. `PromptManager` 启动时调用 `load_prompts()`。
2. `PromptI18n` 加载器扫描 `/prompts` 和 `/data/custom_prompts` 目录，收集所有 `.prompt` 文件路径。
3. 根据当前 locale 优先级建立模板映射表，同名的自定义模板覆盖内置模板。
4. 将每个模板文件实例化为 `Prompt` 对象并存入 `PromptManager.prompts` 字典缓存。
5. 记录每个文件的 mtime 哈希作为初始版本号，供后续热重载比对。

重复加载时，`load_prompts()` 仅重新处理版本号发生变化的模板文件，未变动的模板继续使用缓存，避免不必要的 I/O 和解析开销。

加载过程中若遇到文件读取失败、语法解析错误等问题，`PromptI18n` 加载器会跳过该文件并记录错误日志，不会因单个模板文件损坏而导致整个加载流程中断。被跳过的模板将维持上一次成功加载的版本继续服务，直到问题被修复。

**变量注入与渲染流程**

1. 调用方通过 `get_prompt("prompt_name")` 获取克隆实例。
2. (可选) 调用 `add_context("var", func)` 绑定实时数据源，func 是异步可调用对象，返回字符串。
3. 调用 `render_prompt(prompt)` 进入异步渲染管线，该管线基于 `asyncio` 实现并发解析。
4. 渲染引擎解析 {{...}} 块，按优先级顺序调用对应的构造函数或递归渲染子模板。解析过程是异步的：每个 {{variable}} 的解析任务被调度为独立协程，通过 `asyncio.gather()` 并发执行，显著提升含多个变量的模板的渲染速度。
5. 将所有解析结果通过 `.format(**fields)` 注入模板，最终输出纯文本 Prompt。
6. 返回的字符串可供消费者直接用于构建 LLM 的 Message 对象。

渲染引擎在步骤 4 中维护一个已解析变量的集合，防止同一变量在递归渲染中被重复解析，避免同一会话内出现不一致的渲染结果。

## 模块交互

**与 Maisaka 的交互**
Maisaka 的推理引擎（如 `ChatLoopService`）是 Prompt 系统的最大消费者。

* **系统提示词构建**：Maisaka 通过 `PromptManager` 获取 `maisaka_chat` 等核心模板，注入当前用户画像、会话记忆和近期印象，构建最终发送给 LLM 的 System Message。
* **任务分发**：不同的子代理（Planner, Replyer, ExpressionSelector）分别关联不同的 Prompt 模板，从而在同一会话中切换不同的推理模式。

**与 i18n 的交互**
Prompt 系统的国际化与 `common.i18n` 深度集成。

* **Locale 同步**：当用户通过 `set_locale()` 切换语言时，`PromptManager` 在下次获取 Prompt 时会检测到版本变更或 locale 变更，从而触发模板的重新加载。
* **路径解析**：利用 `prompt_i18n.py` 实现的路径路由机制，确保不同语言的 Prompt 能够映射到同一个逻辑名称。

**与 config 的交互**

* **路径配置**：Prompt 系统的根目录由代码中定义的 `PROMPTS_DIR` 和 `CUSTOM_PROMPTS_DIR` 决定，这些路径与项目的根目录相对位置挂钩。
* **自定义覆盖**：用户可以通过在 `data/custom_prompts` 下创建同名 `.prompt` 文件来覆盖内置指令，实现了无需修改源码的"提示词工程"自定义。

## 与其它模块交互

**与 Maisaka 推理引擎的集成**
Maisaka 的 `ChatLoopService` 是 Prompt 模板的核心消费者，其交互深度体现在以下方面：

* **系统提示词装配**：`ChatLoopService` 在每次推理循环开始时调用 `PromptManager.get_prompt("maisaka_chat")` 获取基础系统模板，随后通过 `add_context()` 注入当前会话的用户画像（Persona）、记忆摘要（MemorySummary）、近期印象（RecentImpression）等动态数据。装配完成的 Prompt 作为 System Message 发送给 LLM。
* **子代理模板隔离**：Planner、Replyer、ExpressionSelector 等子代理各自关联独立的 Prompt 模板名称（如 `maisaka_planner`、`maisaka_replyer`）。`ChatLoopService` 根据当前推理阶段选择对应的模板，实现同一会话内的角色切换，确保不同子代理接收差异化的系统指令。
* **上下文生命周期**：每个推理周期（ChatLoop iteration）创建一个新的 Prompt 克隆实例，确保上一次推理的上下文注入不会泄漏到下一次请求中。克隆实例在 `render_prompt()` 完成后即被丢弃，由 Python GC 回收。

**与国际化模块的协作**
`common.i18n` 为 Prompt 系统提供语言环境支持，两者的协作基于事件驱动模型：

* **Locale 变更传播**：当上层调用 `set_locale(locale)` 时，i18n 模块会触发 `LOCALE_CHANGED` 事件。`PromptManager` 通过事件总线监听该事件并自增内部版本号计数器，使所有缓存的模板在下次访问时标记为待刷新。这种松耦合设计避免了 `PromptManager` 对 i18n 模块的直接依赖。
* **模板路径路由**：`PromptI18n` 加载器内部维护一个 `locale → [PromptDir]` 的路由表。加载时优先匹配精确 locale，若无匹配则降级至默认 locale（`en-US`）。例如，若当前 locale 为 `zh-CN` 且 `custom_prompts/zh-CN/` 和 `prompts/zh-CN/` 均存在时，加载顺序为：`custom_prompts/zh-CN/` → `prompts/zh-CN/` → `custom_prompts/en-US/` → `prompts/en-US/`。

**与配置模块的联动**

* **路径配置解析**：模板系统的根目录通过 `Config.prompts_dir` 和 `Config.custom_prompts_dir` 配置项定义。`PromptManager` 在初始化时从 `Config` 读取这些路径，并支持运行时通过配置热更新（Config hot-reload）动态调整模板目录位置。
* **配置驱动的行为控制**：`prompt_reload_interval`（热重载轮询间隔，单位秒）、`prompt_cache_ttl`（缓存 TTL，单位秒）等参数通过 Config 模块管理。当这些配置项变更时，`PromptManager` 通过 Config 模块的事件系统接收 `CONFIG_UPDATED` 通知并即时调整内部参数，无需重启进程。
* **启动依赖顺序**：`PromptManager` 的初始化依赖于 `Config` 模块已完成加载。在 MaiBot 的启动生命周期中，`Config` 模块优先初始化，随后才是 `PromptManager`。若在测试环境中单独使用 Prompt 系统，需要先构造一个最小化的 `Config` 实例。

## 开发注意事项

**避免循环引用**
由于支持嵌套 Prompt 渲染，如果 Prompt A 引用 Prompt B，而 Prompt B 又引用 Prompt A，将导致死循环。`PromptManager` 内部设有 `recursive_level > 10` 的硬限制以防止崩溃。在开发新模板时，应仔细检查模板间的引用关系，避免无意中引入循环依赖。

**不要在原始实例上修改**
`PromptManager.prompts` 中的实例是全局共享的。任何对模板的修改或上下文注入必须在 `get_prompt()` 返回的克隆实例上进行，否则会导致所有会话共享同一套上下文数据。在多会话并发场景下，直接在原始实例上修改将引发数据竞争和不可预期的渲染结果。

**占位符规范**
模板中必须使用 {{variable}} 形式的命名占位符。严禁使用未命名的 `{}` 占位符，因为这会导致 `string.Formatter` 在解析时抛出异常。变量名应遵循蛇形命名法（snake\_case），避免包含空格或特殊字符。

**异步安全**
`render_prompt()` 是异步函数，其中调用的上下文构造函数也必须是异步的。在 `add_context()` 中注册同步函数会导致类型错误。开发者应在上下文构造函数中使用 `async def` 签名，并在函数体内避免阻塞调用。若必须调用同步代码，应使用 `asyncio.to_thread()` 将其委托到线程池执行。

**模板调试技巧**

* 在开发阶段，可以临时调用 `PromptManager.get_prompt("name").raw` 查看原始模板字符串，确认模板文件是否被正确加载。
* 使用 `PromptManager.render_prompt(prompt, debug=True)` 启用调试模式，渲染引擎会输出每个变量的解析过程与耗时，便于定位性能瓶颈或解析失败原因。
* 模板内容的热重载不会触发全量日志，如需验证重载是否生效，可对比 `PromptManager._version` 在修改文件前后的值。

**性能考量**

* 模板文件数量较多时（超过 50 个），首次 `load_prompts()` 的 I/O 压力较大，建议在服务启动预热阶段完成加载。
* 嵌套 Prompt 渲染会引入额外的异步调度开销，嵌套深度建议控制在 3 层以内以保持响应速度。
* 全局构造函数 `add_context_construct_function` 注册的函数会在每次渲染时被调用，应确保其执行效率，避免在其中执行重量级计算或远程调用。

## Hook/扩展点

Prompt 模板系统在设计上不直接暴露 Hook 接口，模板的自定义与扩展通过以下机制实现：

**文件级热重载**
模板更新不依赖代码层面的 Hook 回调。用户在修改 `.prompt` 文件后，`PromptManager` 通过文件版本号检测自动识别变更并在下次模板请求时热加载新内容。整个流程对上层消费者透明，无需重启服务或触发任何手动刷新命令。热重载的触发条件是版本号计数器自增，消费者仅需在调用 `get_prompt()` 时传入 `force_reload=False`（默认值），系统会自动比对缓存版本号决定是否重新加载。

**生命周期事件委托**
模板系统的状态变更事件（如 reload 完成、locale 切换）由 `Config` 模块的事件系统统一管理。其他模块可以通过监听 `Config` 模块的 `PROMPT_RELOADED`、`LOCALE_CHANGED` 等事件来响应模板变化。若需扩展模板加载行为（如加载前预处理、加载后校验），推荐在 `Config` 模块的事件总线上注册自定义监听器，而非直接修改 `PromptManager` 的加载逻辑。这种事件委托模式保持了模板核心链路的简洁性，同时为上层模块提供了足够的扩展点。

**模板自定义机制**
开发者无需侵入代码即可修改 AI 行为模式：

* **自定义模板目录**：在 `data/custom_prompts/{locale}/` 目录下放置同名 `.prompt` 文件，系统将优先加载自定义版本而非内置版本。
* **优先级覆盖**：自定义模板的加载优先级高于内置模板，这意味着只需提供与内置模板同名的 `.prompt` 文件即可覆盖原有行为，无需复制全部内置模板内容。
* **细粒度增量自定义**：支持仅自定义特定 locale 的模板，未覆盖的 locale 自动回退到内置模板，实现渐进式模板定制。例如，用户可以仅提供 `custom_prompts/zh-CN/maisaka_chat.prompt` 来覆盖中文版本的聊天提示词，而英文版本仍使用内置模板。

**最佳实践建议**

* 对于简单的行为调整（修改措辞、调整指令权重），优先使用自定义模板覆盖而非修改源码。
* 对于需要动态注入数据的场景，通过 `add_context()` 绑定上下文构造函数实现，不在模板文件中硬编码业务逻辑。
* 监控模板变更时，监听 `Config` 模块的 `PROMPT_RELOADED` 事件而非自建文件轮询。
* 在团队协作中，建议将自定义模板纳入版本控制（如 Git），并在部署流水线中统一同步 `data/custom_prompts` 目录，避免不同环境间的模板差异导致行为不一致。
* 编写模板时保持每个模板文件聚焦单一职责，避免在一个 `.prompt` 文件中塞入过多逻辑分支，便于后续维护和复用。
* 进行模板 A/B 测试时，利用自定义模板目录的优先级覆盖机制，为不同测试组部署不同版本的模板文件，通过路由分发实现流量划分。
* 模板文件应保持向后兼容，新增占位符时提供默认值或兜底渲染逻辑，避免旧版本消费者因缺失变量而渲染失败。

---

---
url: /manual/adapters/snowluma.md
---

# SnowLuma 适配器

SnowLuma 适配器让 MaiBot 通过 [SnowLuma](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter) 连接到 QQ 平台，收发消息、处理群聊和私聊。

::: warning 可用（测试中）
SnowLuma 适配器目前处于测试阶段，功能基本可用，但可能存在未覆盖的边界情况。如遇问题欢迎在 [GitHub Issues](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter/issues) 反馈。
:::

## 简介

SnowLuma 适配器是一个 MaiBot 插件，通过 WebSocket 与 SnowLuma 进行双向通信。它的工作方式很简单：

* **入站**：SnowLuma 推送 QQ 消息到适配器，适配器转换后注入 MaiBot
* **出站**：MaiBot 生成的回复经适配器转换后，通过 SnowLuma 发送出去

与 NapCat 适配器不同，SnowLuma 适配器只有**插件模式**，不提供独立运行方式。适配器直接在 MaiBot 进程内运行，配置更少，部署更简单。

消息流转：**QQ → SnowLuma → 适配器插件（MaiBot 内部）→ MaiBot**

### 适配器仓库

SnowLuma 适配器的源码：[Mai-with-u/MaiBot-SnowLuma-Adapter](https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter)

## 安装

### 第一步：获取适配器

克隆适配器仓库到 MaiBot 的 `plugins/` 文件夹中：

```bash
# 进入 MaiBot 的 plugins 目录
cd MaiBot/plugins

# 克隆仓库
git clone https://github.com/Mai-with-u/MaiBot-SnowLuma-Adapter.git
```

或者，你也可以通过 MaiBot 的 WebUI 界面安装插件。

### 第二步：配置 SnowLuma 连接

适配器已经在 MaiBot 内部运行了，只需要配置适配器和 SnowLuma 之间的连接信息。编辑适配器的配置文件 `plugins/MaiBot-SnowLuma-Adapter/config.toml`，填写 SnowLuma 的地址和端口。

### 第三步：配置 SnowLuma

确保 SnowLuma 已启用正向 WebSocket 服务器，监听地址和端口需要与适配器配置中的 `luma_client.server` 和 `luma_client.port` 一致。

默认连接地址为 `ws://127.0.0.1:3001`，如果你的 SnowLuma 在同一台机器上运行，保持默认即可。

### 第四步：启动

直接启动 MaiBot 就行，适配器会自动加载并连接。

### 插件默认未启用

SnowLuma 适配器插件安装后**默认是禁用的**，需要手动启用才能连接。

#### 方式一：编辑配置文件（推荐）

编辑 `plugins/MaiBot-SnowLuma-Adapter/config.toml`，将 `enabled` 改为 `true`：

```toml
[plugin]
enabled = true   # 改为 true
config_version = "1.0.0"
```

然后重启 MaiBot 即可。

#### 方式二：通过 WebUI 启用

1. 浏览器访问 `http://127.0.0.1:8001`，输入 Access Token 登录
2. 点击左侧菜单 **"插件管理"**
3. 找到 **"SnowLuma 适配器"**，点击启用开关
4. 保存配置后重启 MaiBot（或等待插件热重载）

> **验证是否启用**：启动 MaiBot 后，查看日志中是否出现适配器加载和连接成功的提示；如果看到 `已在配置中禁用，跳过激活` 则说明未启用。

## 配置参考

适配器的配置文件位于 `plugins/MaiBot-SnowLuma-Adapter/config.toml`，包含以下四个分组。

### 插件设置 (`[plugin]`)

* **`enabled`** — 是否启用 SnowLuma 适配器。关闭时插件只注册消息网关，不会主动连接 SnowLuma。默认关闭
* **`config_version`** — 当前配置结构版本（自动管理，一般不需要手动修改）。默认 "1.0.0"

### SnowLuma 连接 (`[luma_client]`)

* **`server`** — SnowLuma WebSocket 服务地址。默认 "127.0.0.1"
* **`port`** — SnowLuma WebSocket 服务端口。默认 3001
* **`token`** — SnowLuma 访问令牌（可留空）。默认为空
* **`connection_id`** — 可选连接标识，用于区分多条适配器链路。默认为空
* **`reconnect_delay_sec`** — 连接断开后的重连等待时间（秒）。默认 5.0
* **`action_timeout_sec`** — 调用 SnowLuma 动作接口的超时时间（秒）。默认 10.0

### 聊天过滤 (`[chat]`)

* **`enable_chat_list_filter`** — 是否启用群聊与私聊名单过滤。关闭后仅保留 `ban_user_id` 规则。默认开启
* **`show_dropped_chat_list_messages`** — 是否记录未通过聊天名单过滤而被丢弃的消息。默认关闭
* **`group_list_type`** — 群聊名单模式。白名单只接收列表内群聊，黑名单则忽略列表内群聊。默认 "whitelist"
* **`group_list`** — 群聊名单中的群号列表（自动去重）。默认为空
* **`private_list_type`** — 私聊名单模式。白名单只接收列表内私聊，黑名单则忽略列表内私聊。默认 "whitelist"
* **`private_list`** — 私聊名单中的用户 ID 列表（自动去重）。默认为空
* **`ban_user_id`** — 全局屏蔽的用户 ID 列表，这些用户的消息会在进入 MaiBot 之前被直接丢弃。默认为空
* **`ban_qq_bot`** — 是否屏蔽 QQ 官方机器人消息。默认关闭

::: tip 群聊白名单默认开启
适配器默认启用聊天名单过滤，且群聊默认是白名单模式。意味着没有写进 `group_list` 的群消息会被直接丢弃。如果连接成功但群里 @ 机器人没有反应，优先检查这里。
:::

测试阶段可以临时关闭名单过滤：

```toml
[chat]
enable_chat_list_filter = false
```

或者把需要测试的群号加入白名单：

```toml
[chat]
enable_chat_list_filter = true
group_list_type = "whitelist"
group_list = ["你的QQ群号"]
```

### 消息过滤 (`[filters]`)

* **`ignore_self_message`** — 是否忽略机器人自身发送的消息（建议保持开启，避免机器人处理自己刚发出的消息）。默认开启

### 完整配置示例

```toml
[plugin]
enabled = true
config_version = "1.0.0"

[luma_client]
server = "127.0.0.1"
port = 3001
token = ""
connection_id = ""
reconnect_delay_sec = 5.0
action_timeout_sec = 10.0

[chat]
enable_chat_list_filter = true
show_dropped_chat_list_messages = false
group_list_type = "whitelist"
group_list = ["123456789"]
private_list_type = "whitelist"
private_list = []
ban_user_id = []
ban_qq_bot = false

[filters]
ignore_self_message = true
```

## 验证与排查

### 验证连接

怎么知道连上了？看这几个地方：

1. **WebUI 插件列表**：能看到 SnowLuma 适配器插件已加载
2. **MaiBot 日志**：看到 `SnowLuma WebSocket 已连接` 的提示
3. **发消息测试**：在 QQ 群里 @机器人，看有没有回复

### 连不上怎么办？

**检查这几点**：

* SnowLuma 的地址和端口填对了吗？和适配器 `luma_client.server` / `luma_client.port` 一致吗？
* 防火墙拦住了吗？
* SnowLuma 和 MaiBot 在同一台机器吗？
* 访问令牌 `token` 填对了吗？
* 日志里有什么报错信息？

### 收不到消息？

**可能原因**：

* 群聊白名单默认开启，你的群号加入 `group_list` 了吗？
* `enabled` 设为 `true` 了吗？
* SnowLuma 本身收到消息了吗？看 SnowLuma 的日志
* 网络连接正常吗？

### 发不出消息？

**排查方法**：

* 机器人有发言权限吗？（群聊需要权限）
* 看 MaiBot 日志有什么报错
* `action_timeout_sec` 设置是否合理？网络延迟较高时可以适当增大

### 多实例部署

如果需要同一个 MaiBot 对接多个 SnowLuma 实例（比如多个 QQ 号），可以为每个实例配置不同的 `connection_id` 来区分链路：

```toml
[luma_client]
connection_id = "bot-1"
```

---

---
url: /manual/adapters/telegram.md
---

# Telegram 适配器

MaiBot 的 Telegram 平台适配器，通过 Telegram Bot API 长轮询将 Telegram Bot 与 MaiBot 无缝桥接。

## 适配器仓库

Telegram 适配器的源码：[exynos967/MaiBot-Telegram-Adapter](https://github.com/exynos967/MaiBot-Telegram-Adapter)

## 创建 Telegram Bot

在使用适配器之前，你需要先在 Telegram 上创建一个 Bot 并获取 Token。

### 第一步：通过 @BotFather 创建 Bot

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`，按照提示输入 Bot 名称和用户名
3. 创建完成后，BotFather 会返回 Bot Token，格式类似 `123456:ABC-DEF...`
4. 将此 Token 填入适配器配置的 `telegram_bot.token` 字段

### 第二步：关闭 Privacy Mode

默认情况下，Telegram Bot 在群聊中只能接收以 `/` 开头的命令和直接 @Bot 的消息。如果需要 Bot 在群聊中接收所有消息，必须关闭 Privacy Mode：

1. 向 @BotFather 发送 `/setprivacy`
2. 选择你创建的 Bot
3. 选择 **Disable**

关闭 Privacy Mode 后，Bot 将能接收群聊中的所有消息。如果想通过 @Bot 或回复来触发机器人，也建议关闭此项以确保消息能被正常接收。

## 安装

将适配器仓库克隆到 MaiBot 的 `plugins/` 目录下：

```bash
cd /path/to/MaiBot/plugins
git clone https://github.com/exynos967/MaiBot-Telegram-Adapter.git
```

### 依赖

* `maibot_sdk` >= 2.0.0（由 MaiBot 主程序提供）
* `aiohttp` >= 3.9.0（MaiBot 主程序已包含）

如需 SOCKS5 代理支持，额外安装：

```bash
pip install aiohttp-socks
```

## 配置

### 适配器配置

首次加载后，适配器会在插件目录生成 `config.toml`，编辑该文件：

```toml
[plugin]
enabled = true                # 启用插件
config_version = "0.1.0"

[telegram_bot]
token = "你的Bot Token"       # 必填，从 @BotFather 获取
api_base = "https://api.telegram.org"
poll_timeout = 20
proxy_enabled = false
proxy_url = ""                # 例如 socks5://127.0.0.1:1080 或 http://127.0.0.1:7890
proxy_from_env = false

[chat]
group_list_type = "whitelist" # whitelist / blacklist
group_list = []               # chat_id 列表
private_list_type = "whitelist"
private_list = []             # 用户 ID 列表
ban_user_id = []              # 全局屏蔽用户
```

::: tip 提示
配置也可以通过 MaiBot WebUI 的插件配置页面进行热重载修改，无需重启 MaiBot。
:::

### MaiBot 主配置

MaiBot Core 需要通过主配置里的 `platforms` 字段识别"机器人自己"。启用 Telegram 后，请在 MaiBot 主配置的 `[bot]` 中加入 Telegram Bot 的数字 ID：

```toml
[bot]
platforms = ["telegram:123456789"]
```

其中 `123456789` 是你的 Telegram Bot 的数字 ID，也可以使用简写 `tg:123456789`。Bot 数字 ID 会在适配器启动成功后通过日志 `Telegram Bot: id=...` 输出。

::: warning 注意
如果缺少 `platforms` 中的 Telegram 配置，MaiBot 的历史消息和提示词中可能无法将 Bot 自身识别为配置的昵称。
:::

## 配置参考

### `[plugin]` — 插件设置

* **`enabled`** — 是否启用 Telegram 适配器。关闭后插件保持空闲，不会启动轮询。默认关闭
* **`config_version`** — 当前配置结构版本（自动维护，无需手动修改）。默认 "0.1.0"

### `[telegram_bot]` — Telegram Bot 连接配置

* **`token`** — Bot Token，从 @BotFather 获取。启用适配器时必填。默认为空
* **`api_base`** — Telegram Bot API 基础地址。使用自建 API 服务器时可修改此项。默认 "https://api.telegram.org"
* **`poll_timeout`** — 长轮询超时时间（秒）。增大此值可减少请求频率，但会增加消息延迟感知。默认 20
* **`proxy_enabled`** — 是否启用代理。默认关闭
* **`proxy_url`** — 代理地址，支持 `http://`、`https://` 和 `socks5://` 协议。例如 `http://127.0.0.1:7890` 或 `socks5://127.0.0.1:1080`。默认为空
* **`proxy_from_env`** — 是否从环境变量（如 `HTTP_PROXY`、`HTTPS_PROXY`）读取代理设置。默认关闭

### `[chat]` — 聊天过滤

* **`group_list_type`** — 群聊名单模式，可选 `whitelist`（白名单）或 `blacklist`（黑名单）。默认 "whitelist"
* **`group_list`** — 群聊名单中的 chat\_id 列表。默认为空
* **`private_list_type`** — 私聊名单模式，可选 `whitelist`（白名单）或 `blacklist`（黑名单）。默认 "whitelist"
* **`private_list`** — 私聊名单中的用户 ID 列表。默认为空
* **`ban_user_id`** — 全局屏蔽的用户 ID 列表，被屏蔽用户的消息会被直接丢弃。默认为空

::: tip 聊天过滤说明

* **白名单模式**：只处理名单中的群聊/私聊消息，其余丢弃
* **黑名单模式**：处理所有消息，但丢弃名单中的群聊/私聊消息
* 默认群聊为白名单模式，如果发现 Bot 已连接但群里没有反应，优先检查 `group_list` 是否填写了对应的 chat\_id
  :::

## 消息类型支持

* **文本** — 入站：支持 | 出站：支持
* **图片** — 入站：支持（自动下载转 base64） | 出站：支持（base64 / URL）
* **语音** — 入站：支持（自动下载转 base64） | 出站：支持（base64）
* **贴纸** — 入站：支持（转 emoji 类型） | 出站：支持（以动图发送）
* **GIF 动图** — 入站：支持（转 emoji 类型） | 出站：支持（以动图发送）
* **视频** — 入站：不支持 | 出站：支持（URL）
* **文件** — 入站：支持（转文本标记） | 出站：支持（URL）
* **回复消息** — 入站：支持（关联消息 ID） | 出站：支持（reply\_parameters）
* **@Bot** — 入站：支持（多种识别方式）

## 代理配置

如果服务器无法直接访问 Telegram API，可以通过代理连接。适配器支持以下代理方式：

### HTTP/HTTPS 代理

```toml
[telegram_bot]
proxy_enabled = true
proxy_url = "http://127.0.0.1:7890"
```

### SOCKS5 代理

使用 SOCKS5 代理需要额外安装 `aiohttp-socks` 依赖：

```bash
pip install aiohttp-socks
```

然后配置：

```toml
[telegram_bot]
proxy_enabled = true
proxy_url = "socks5://127.0.0.1:1080"
```

### 从环境变量读取代理

如果系统已配置 `HTTP_PROXY` 或 `HTTPS_PROXY` 环境变量，可以启用此选项：

```toml
[telegram_bot]
proxy_enabled = true
proxy_from_env = true
```

### 自定义 API 地址

如果使用自建的 Telegram API 代理服务器（如 Telegram Bot API Server），可以修改 `api_base`：

```toml
[telegram_bot]
api_base = "https://your-api-server.com"
```

## Topic 分流

Telegram 超级群组支持 Topic（话题）功能。适配器会自动将同一群组中不同 Topic 的消息分流为独立的会话，使 MaiBot 在各 Topic 中维护独立的上下文。

具体机制：

* 入站时，适配器将 `chat_id` 和 `message_thread_id` 组合为虚拟的 `group_id`（格式：`chat_id::tg-topic::mt=thread_id`）
* 出站时，适配器解析虚拟 `group_id`，将消息发送到正确的 Topic
* 这样，同一个 Telegram 群组的不同 Topic 在 MaiBot 中被视为不同的群组，各自拥有独立的对话上下文

## @Bot 识别机制

适配器支持多种方式识别用户 @Bot 的行为，确保机器人在群聊中能被正确触发：

1. **mention entity**：Telegram 消息的 `entities` 中包含 `mention` 或 `text_mention` 类型，且指向 Bot
2. **回复 Bot**：用户回复了 Bot 发送的消息（`reply_to_message` 的发送者是 Bot）
3. **文本兜底匹配**：当以上方式均未匹配时，通过正则匹配消息文本中的 `@bot_username`

当识别到 @Bot 时，适配器会：

* 在消息段中插入 `at` 类型的组件，标记 `target_user_id` 为 Bot ID
* 设置 `is_mentioned` 和 `is_at` 为 `true`
* 移除文本开头重复的 `@bot_username` 文本，避免 Prompt 中出现两份 @

## 验证连接

启动 MaiBot 后，检查以下内容确认适配器工作正常：

1. **MaiBot 日志**：看到 `Telegram Bot: id=xxx, username=xxx` 输出，说明 Bot 身份获取成功
2. **MaiBot 日志**：看到 `Telegram 适配器开始轮询...`，说明已开始接收消息
3. **发消息测试**：在 Telegram 中向 Bot 发送私聊消息或在群聊中 @Bot，看是否有回复

### 常见问题

**Bot 启动后没有开始轮询**

* 检查 `plugin.enabled` 是否设为 `true`
* 检查 `telegram_bot.token` 是否填写正确
* 查看日志中是否有 `telegram_bot.token 为空` 的警告

**群聊中收不到消息**

* 确认已关闭 Bot 的 Privacy Mode（参见[关闭 Privacy Mode](#第二步-关闭-privacy-mode)）
* 检查 `chat.group_list` 是否包含目标群聊的 chat\_id
* 检查 `chat.group_list_type` 的模式是否正确

**无法连接 Telegram API**

* 检查网络是否能访问 `api.telegram.org`
* 如果在中国大陆，需要配置代理（参见[代理配置](#代理配置)）
* 检查代理地址格式是否正确

---

---
url: /develop/plugin-dev/tools.md
---

# Tool 组件

`@Tool` 是 MaiBot 插件系统中最核心的组件类型。它允许插件向 LLM 暴露可调用的工具函数，使 LLM 能够在推理过程中主动调用外部能力——例如搜索知识库、查询数据库、调用外部 API 等。

::: tip Tool vs Action
`@Action` 是旧版装饰器，SDK 内部会自动将其转换为 `@Tool` 声明。新插件应直接使用 `@Tool`，不再使用 `@Action`。详见 [Action 组件（Legacy）](./actions.md)。
:::

## 装饰器签名

```python
from maibot_sdk import Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

@Tool(
    name: str,                                              # 工具名称（必填）
    description: str = "",                                  # 工具描述，作为备选描述字段
    brief_description: str = "",                            # 简要描述，优先级高于 description
    detailed_description: str = "",                         # 详细描述，可包含参数说明等
    parameters: list[ToolParameterInfo] | dict | None = None,  # 参数定义
    **metadata,                                             # 额外元数据
)
```

### 参数说明

* **`name`** `str` — 工具名称，需在插件内唯一。LLM 通过此名称调用工具
* **`description`** `str` — 工具备选描述。当 `brief_description` 为空时使用此字段
* **`brief_description`** `str` — 工具主描述（优先使用）。传给 LLM 的工具描述摘要，帮助 LLM 判断是否需要调用
* **`detailed_description`** `str` — 详细描述，可包含参数使用说明、注意事项等。SDK 会自动合并参数 Schema 生成完整描述
* **`parameters`** `list | dict | None` — 工具参数定义，支持两种格式（见下文）

描述字段约定：

* `description`：关于工具的描述，包括使用方法，使用情景，注意事项。当 `brief_description` 为空时，`description` 会作为回退描述。
* `brief_description`：给主程序或小模型快速判断"这个工具是做什么的"的简要描述
* `detailed_description`：描述参数、必填项、可选项和调用约束的详细描述

## 参数定义

### 方式一：结构化参数（推荐）

使用 `ToolParameterInfo` 列表声明参数，SDK 会自动生成 JSON Schema：

```python
from maibot_sdk import Tool, MaiBotPlugin
from maibot_sdk.types import ToolParameterInfo, ToolParamType

class MyPlugin(MaiBotPlugin):
    @Tool(
        "search",
        brief_description="搜索互联网获取信息",
        detailed_description="使用搜索引擎查找相关信息。参数说明：\n- query：string，必填。搜索关键词。\n- limit：integer，可选。返回结果数量上限。",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="搜索关键词",
                required=True,
            ),
            ToolParameterInfo(
                name="limit",
                param_type=ToolParamType.INTEGER,
                description="返回结果数量上限",
                required=False,
                default=5,
            ),
        ],
    )
    async def handle_search(self, query: str, limit: int = 5, **kwargs):
        results = await self._do_search(query, limit)
        return {"results": results}
```

### 方式二：dict 参数（兼容旧式声明）

直接传入 JSON Schema 风格的字典：

```python
class MyPlugin(MaiBotPlugin):
    @Tool(
        "search",
        brief_description="搜索互联网获取信息",
        parameters={
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回结果数量上限", "default": 5},
        },
    )
    async def handle_search(self, query: str, limit: int = 5, **kwargs):
        results = await self._do_search(query, limit)
        return {"results": results}
```

## ToolParameterInfo 字段

* **`name`** `str` — 参数名称
* **`param_type`** `ToolParamType` — 参数类型枚举
* **`description`** `str` — 参数描述
* **`required`** `bool` · 默认 `True` — 是否必填
* **`enum_values`** `list | None` — 可选枚举值列表
* **`default`** `Any` — 默认值
* **`items_schema`** `dict | None` — 数组元素 Schema（当 `param_type=ARRAY` 时使用）
* **`properties`** `dict | None` — 对象属性定义（当 `param_type=OBJECT` 时使用）
* **`required_properties`** `list[str]` — 对象内部必填字段
* **`additional_properties`** `bool | dict | None` — 是否允许额外字段

## ToolParamType 枚举

* **`STRING`** → JSON Schema `string` — 字符串
* **`INTEGER`** → JSON Schema `integer` — 整数
* **`NUMBER`** → JSON Schema `number` — 数字（整数或浮点数）
* **`FLOAT`** → JSON Schema `number` — 浮点数（等价于 NUMBER）
* **`BOOLEAN`** → JSON Schema `boolean` — 布尔值
* **`ARRAY`** → JSON Schema `array` — 数组
* **`OBJECT`** → JSON Schema `object` — 对象

## 处理函数

Tool 处理函数是插件类上的异步方法，接收与参数名对应的具名参数和 `**kwargs`：

```python
@Tool("greet", description="向用户打招呼",
      parameters=[
          ToolParameterInfo(name="stream_id", param_type=ToolParamType.STRING,
                          description="当前聊天流 ID", required=True),
      ])
async def handle_greet(self, stream_id: str, **kwargs):
    await self.ctx.send.text("你好！", stream_id)
    return {"success": True, "message": "已回复"}
```

### 返回值

Tool 处理函数的返回值会作为工具执行结果返回给 LLM。返回值可以是：

* `dict`：推荐，LLM 可以理解结构化数据
* `str`：简单文本结果
* 其他可序列化的值

LLM 会根据返回值决定下一步操作（如向用户回复、调用其他工具等）。

### 返回图片和其他媒体

如果 Tool 需要把图片交给 Maisaka 继续观察或推理，不要把图片 base64 直接塞进 `content`。推荐返回 `dict`，将给 LLM 阅读的文字放在 `content`，将图片本体放在 `content_items`：

```python
from base64 import b64encode


async def handle_draw(self, prompt: str, **kwargs):
    image_bytes = await self._draw_image(prompt)

    return {
        "success": True,
        "content": "图片已生成，请查看索引对应的图片内容。",
        "content_items": [
            {
                "type": "image",
                "data": b64encode(image_bytes).decode("ascii"),
                "mime_type": "image/png",
                "name": "result.png",
                "description": "根据提示词生成的图片",
            }
        ],
    }
```

也可以使用 data URL：

```python
return {
    "success": True,
    "content": "图片已生成。",
    "content_items": [
        {
            "type": "image",
            "uri": f"data:image/png;base64,{b64encode(image_bytes).decode('ascii')}",
            "mime_type": "image/png",
            "name": "result.png",
        }
    ],
}
```

`content_items` 中常用字段如下：

* **`type` / `content_type`** `str` — 内容类型。图片使用 `image`；也支持 `audio`、`resource_link`、`resource`、`binary`
* **`data` / `base64`** `str` — 媒体二进制的 base64 字符串，推荐图片直接使用这个字段
* **`uri`** `str` — 媒体 URI。图片可使用 `data:image/...;base64,...`
* **`mime_type`** `str` — MIME 类型，例如 `image/png`、`image/jpeg`、`image/webp`
* **`name`** `str` — 文件名或展示名称
* **`description`** `str` — 对媒体内容的简短说明
* **`metadata`** `dict` — 额外元数据

Maisaka 会把这类返回拆成两种上下文消息：第一条仍是纯文本 Tool Result，其中包含类似 `tool_result:<tool_call_id>:1` 的媒体索引；随后追加一条普通 user message，里面放入同一索引和真实图片组件。这样可以兼容不支持在 tool result 中直接回传图片的模型 API，同时让支持视觉输入的模型按普通图片消息观察图片。

::: tip 视图逻辑
拆出来的图片在 LLM 输入和 Prompt 预览里会走普通 `ImageComponent` 的展示逻辑，和真实收到的图片消息基本一致。区别是它的来源会标记为 `tool_result_media`，消息 ID 是工具媒体索引，不会被当作真实用户发来的平台消息。
:::

### kwargs 中常见的额外参数

* **`stream_id`** `str` — 当前聊天流 ID，可用于 `ctx.send.text()` 等发送消息
* **`message`** `dict` — 触发此工具调用的原始消息

::: tip stream\_id
`stream_id` 是 Tool 组件中最重要的参数之一，它标识了当前对话流。使用 `ctx.send.text("消息", stream_id)` 可以将消息发送到对应的聊天流中。
:::

## 描述生成规则

SDK 会自动为工具生成完整的描述信息，优先级如下：

1. **`brief_description`**：优先使用（如果提供）
2. **`description`**：降级回退（`brief_description` 为空时使用）
3. **`detailed_description`**：如果提供了，SDK 会将其与参数 Schema 合并生成完整描述
4. **自动生成**：如果上述字段都未提供，SDK 会使用 `"工具 {name}"` 作为描述

自动生成的参数说明格式为：

```
参数说明：
- query：string，必填。搜索关键词
- limit：integer，可选。返回结果数量上限。默认值：5
```

## 完整示例

```python
from typing import Any

from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class SearchPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("搜索插件已加载")

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Tool(
        "search_web",
        description="搜索互联网获取信息",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="搜索关键词",
                required=True,
            ),
            ToolParameterInfo(
                name="limit",
                param_type=ToolParamType.INTEGER,
                description="返回结果数量上限",
                required=False,
                default=5,
            ),
        ],
    )
    async def search(self, query: str, limit: int = 5, **kwargs):
        """搜索互联网"""
        results = await self._do_search(query, limit)
        return {"results": results, "count": len(results)}

    @Tool(
        "get_weather",
        description="获取指定城市的天气信息",
        parameters=[
            ToolParameterInfo(
                name="city",
                param_type=ToolParamType.STRING,
                description="城市名称",
                required=True,
            ),
        ],
    )
    async def get_weather(self, city: str, **kwargs):
        """查询天气"""
        weather = await self._fetch_weather(city)
        return {"city": city, "weather": weather}

    async def _do_search(self, query: str, limit: int) -> list:
        # 实际搜索逻辑
        return []

    async def _fetch_weather(self, city: str) -> dict:
        # 实际天气查询逻辑
        return {}


def create_plugin():
    return SearchPlugin()
```

## 与旧版 Action 的关系

`@Action` 装饰器在 SDK 2.0 中已废弃，内部会自动转换为 `@Tool` 声明：

* `action_parameters` → 转换为 Tool 的 `parameters` Schema（所有参数类型统一为 `string`）
* `activation_type` / `activation_keywords` → 作为 Tool 的 `metadata` 保留
* 使用 `@Action` 时会触发 `DeprecationWarning`

新插件应直接使用 `@Tool`，享受更丰富的参数类型支持和更规范的 Schema 生成。

---

---
url: /AGENTS.md
---
## 根目录文件

| 文件 | 说明 |
|------|------|
| `index.md` | VitePress 首页/Hero page，展示 MaiBot 简介和导航入口 |
| `README.md` | 项目说明，介绍文档仓库用途、本地开发方法和贡献指南 |
| `_redirects` | 单页应用路由重定向配置（所有路径重定向到 /index.html） |
| `.gitignore` | Git 忽略规则（node\_modules, dist, .vitepress/cache 等） |
| `package.json` | Node.js 项目配置（VitePress + Mermaid + Tabs 插件） |
| `pnpm-lock.yaml` | pnpm 依赖锁定文件 |
| `LICENSE` | 开源许可证文件 |

## 文件夹结构详述

### `.vitepress/` — VitePress 站点配置

| 文件/文件夹 | 说明 |
|-------------|------|
| `config.mts` | VitePress 核心配置：导航栏、侧边栏、多语言（中文/English）、搜索、markdown 插件（Mermaid, Tabs）、社交链接 |
| `theme/` | 自定义主题目录 |
| `theme/index.ts` | 主题入口 |
| `theme/style.css` | 自定义样式 |

### `manual/` — 用户手册（简体中文）

| 文件/文件夹 | 说明 |
|-------------|------|
| `index.md` | 用户手册总览 |
| `deployment/` | 部署与安装指南（部署概览、源码安装、Docker、适配器安装） |
| `adapters/` | 平台适配器文档（NapCat QQ连接、GoCQ 适配器） |
| `configuration/` | 配置说明（Bot 配置、模型配置） |
| `features/` | 功能详解（消息管线、Maisaka推理引擎、记忆系统、学习系统、表情包系统、MCP集成） |
| `webui/` | WebUI 管理文档（配置管理、记忆管理、插件管理、聊天统计） |
| `faq/` | 常见问题与故障排除 |
| `getting-started/` | 快速入门指南 |

### `develop/` — 开发文档（简体中文）

| 文件/文件夹 | 说明 |
|-------------|------|
| `index.md` | 开发指南总览（技术栈、项目结构、环境搭建） |
| `architecture.md` | 架构设计总览 |
| `contributing.md` | 贡献指南 |
| `architecture/` | 架构详解（消息管线、Maisaka推理引擎、记忆系统、WebUI内部机制） |
| `plugin-dev/` | 插件开发文档（Manifest、生命周期、Tool、Command、Hook、事件处理、API组件、消息网关、Action、配置、API参考） |
| `adapter-dev/` | 适配器开发文档（PlatformIO 驱动） |

### `features/` — 功能介绍页

| 文件/文件夹 | 说明 |
|-------------|------|
| 各功能页面 | 首页特性卡片展示内容 |

### `changelog/` — 更新日志

| 文件/文件夹 | 说明 |
|-------------|------|
| 各版本日志 | 记录每个版本的更新内容 |

### `community/` — 社区页面

| 文件/文件夹 | 说明 |
|-------------|------|
| 各社区页面 | QQ群、GitHub链接、社交媒体、衍生项目 |

### `en/` — 英文版文档

en/ 目录下的结构与中文版完全镜像，包含 manual/（用户手册）、develop/（开发文档）、features/（功能介绍）、changelog/（更新日志）、community/（社区页面）等子目录。

> ⚠️ **注意**：en/ 英文文档是通过翻译中文内容得来，应最大程度与中文内容保持同步。

### `public/` — 静态资源

| 文件/文件夹 | 说明 |
|-------------|------|
| `images/` | 文档图片（截图、示意图） |
| `title_img/` | 首页标题图片 |
| `avatars/` | 头像/角色图片 |

### `.sisyphus/` — 内部工作流记录

> ⚠️ 注意：此文件夹为内部工作流记录，请勿手动编辑

## 文档写作约定

* **不要在内容页中使用 Markdown 表格**。Markdown 表格在 VitePress 中渲染效果差（移动端不友好、列宽不可控），仅 `index.md` 页面允许使用表格。内容页请用定义列表替代，例如 `**`field`** — 说明。默认 X`

---

---
url: /develop/plugin-dev/vibe-coding.md
---

# Vibe Coding 插件开发指南

本文面向使用 AI 辅助编写 MaiBot 插件的开发者。目标是把插件需求拆成 AI 容易理解、容易验证、不会误改主程序的工作单元。

## AI 任务简报

把下面这段作为给 AI 的首段上下文，再补充你的具体需求：

```text
你正在为 MaiBot 编写第三方插件。插件必须放在 plugins/<plugin-name>/ 下，不要修改 MaiBot 主程序代码，除非我明确许可。请使用 maibot-plugin-sdk，入口文件为 plugin.py，元信息文件为 _manifest.json。必须实现 on_load、on_unload、on_config_update 和 create_plugin。优先使用 @Tool、@Command、@HookHandler、@EventHandler、@API、@MessageGateway；不要给新插件使用 @Action。所有用户可见文本优先使用简体中文。请保持改动边界清晰，并给出测试方式。
```

## 开发边界

* 插件目录固定为 `plugins/<plugin-name>/`；如果插件需要自己的忽略规则，在插件目录内新增 `.gitignore`，不要修改仓库根目录 `.gitignore`。
* 插件入口固定为 `plugin.py`，工厂函数固定为 `create_plugin()`。
* 插件元信息固定为 `_manifest.json`，运行配置放在 `config.toml`。
* 新插件不要修改 `src/`、`dashboard/`、`config/` 等主程序目录；确实需要主程序能力时，先说明原因、影响面和替代方案，再请求许可。
* 不要把本地实验数据、日志、临时脚本、个人密钥、token、cookie、数据库文件提交进插件。
* 依赖以 `_manifest.json` 的 `dependencies` 为准；只有在维护 MaiBot 主程序依赖时才同步 `pyproject.toml` 和 `requirements.txt`。

## 最小目录结构

```text
plugins/my-plugin/
├── _manifest.json
├── plugin.py
├── config.toml
├── README.md
└── .gitignore
```

推荐额外添加：

```text
plugins/my-plugin/
├── tests/
├── docs/
└── assets/
```

## Manifest 要点

`_manifest.json` 用于让 Host 在加载前校验插件。AI 生成时必须注意：

* `manifest_version` 当前固定为 `2`。
* `id` 使用小写反向域名或作者前缀，例如 `com.example.my-plugin`。
* `version` 使用严格三段式语义版本，例如 `1.0.0`。
* `author.url`、`urls.repository` 等 URL 必须以 `http://` 或 `https://` 开头。
* `host_application` 和 `sdk` 都要声明 `min_version` 与 `max_version`。
* Python 包依赖写入 `dependencies`，类型为 `python_package`。
* 插件间依赖写入 `dependencies`，类型为 `plugin`。
* `capabilities` 只声明确实需要的能力。
* `i18n.default_locale` 推荐使用 `zh-CN`。

```json
{
  "manifest_version": 2,
  "id": "com.example.my-plugin",
  "version": "1.0.0",
  "name": "我的插件",
  "description": "一个 MaiBot 插件",
  "author": {
    "name": "开发者",
    "url": "https://github.com/developer"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/developer/my-plugin"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "1.99.99"
  },
  "sdk": {
    "min_version": "2.5.1",
    "max_version": "2.99.99"
  },
  "dependencies": [],
  "capabilities": ["send_message"],
  "i18n": {
    "default_locale": "zh-CN"
  }
}
```

## 代码骨架

```python
from typing import Any

from maibot_sdk import Command, Field, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class PluginSectionConfig(PluginConfigBase):
    """插件基础配置。"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=False, description="是否启用插件")
    config_version: str = Field(default="1.0.0", description="配置版本")


class MyPluginConfig(PluginConfigBase):
    """插件配置。"""

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)


class MyPlugin(MaiBotPlugin):
    """我的插件。"""

    config_model = MyPluginConfig

    async def on_load(self) -> None:
        """插件加载时执行。"""
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        """插件卸载时执行。"""
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        """配置热重载时执行。"""
        del scope
        del config_data
        del version

    @Tool(
        "echo_text",
        description="复述用户提供的文本。适合测试插件是否能被 LLM 调用。",
        parameters=[
            ToolParameterInfo(
                name="text",
                param_type=ToolParamType.STRING,
                description="要复述的文本",
                required=True,
            ),
        ],
    )
    async def echo_text(self, text: str, **kwargs: Any) -> dict[str, str]:
        del kwargs
        return {"content": text}

    @Command("ping", description="测试插件是否在线", pattern=r"^/ping$")
    async def ping(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, int]:
        del kwargs
        await self.ctx.send.text("pong", stream_id)
        return True, "pong", 2


def create_plugin() -> MyPlugin:
    """创建插件实例。"""
    return MyPlugin()
```

## 组件选择

* **让 LLM 主动调用能力** → `@Tool` — 默认工具进入 deferred 池，需要被搜索发现；高频低风险工具才考虑 `core_tool=True`
* **用户输入命令触发** → `@Command` — 使用正则 `pattern` 匹配，例如 `/ping`
* **拦截或观察主流程** → `@HookHandler` — 适合消息改写、发送前审计、流程拦截
* **监听消息或生命周期事件** → `@EventHandler` — 适合统计、记录、异步辅助任务
* **给其他插件调用能力** → `@API` — 只把稳定接口设为公开
* **接入外部聊天平台** → `@MessageGateway` — 适配器类插件使用
* **维护旧插件** → `@Action` — 仅兼容旧代码，新插件不要使用

## Tool 编写要点

* `description` 要写清楚何时使用、参数含义、限制和副作用。
* 参数优先用 `ToolParameterInfo` 声明，类型来自 `ToolParamType`。
* 返回值优先使用 `dict`，把给 LLM 阅读的文字放在 `content`。
* 需要返回图片等媒体时，使用文档约定的 `content_items`，不要把 base64 直接塞进长文本。
* 默认不要设置 `core_tool=True`；过多核心工具会增加模型选择成本。
* 工具内部要处理失败并返回可读错误，不要让异常泄漏成难懂堆栈。

## 发送消息要点

* 已有 `stream_id` 时，使用 `await self.ctx.send.text(content, stream_id)` 发送文本。
* 发送图片、表情、转发、混合消息时，优先使用 `self.ctx.send` 和 `self.ctx.emoji` 提供的能力代理。
* 不要自行计算会话 ID；插件应使用上下文传入的 `stream_id` 或 SDK 提供的消息上下文。
* 用户可见文本默认使用简体中文。

## 配置要点

* 配置模型继承 `PluginConfigBase`，字段使用 `Field(default=..., description="...")`。
* 推荐保留 `[plugin]` 分组，并包含 `enabled` 与 `config_version`。
* WebUI 展示信息可以通过 `__ui_label__`、`__ui_icon__`、`__ui_order__` 补充。
* 配置读取优先使用 `self.config.<section>.<field>`；确实需要原始字典时再用 `self.get_plugin_config_data()`。
* 配置热重载逻辑放入 `on_config_update()`。

## AI 生成代码检查清单

要求 AI 完成后逐项自检：

* `_manifest.json` 字段完整，版本号和 URL 格式合法。
* `plugin.py` 只从标准库、第三方库和 `maibot_sdk` 导入；导入顺序符合项目规范。
* 插件类继承 `MaiBotPlugin`，并声明 `config_model`。
* 已实现 `on_load()`、`on_unload()`、`on_config_update()`。
* 已实现 `create_plugin()` 并返回插件实例。
* 新功能优先使用 `@Tool` 或 `@Command`，没有给新代码使用 `@Action`。
* 没有修改主程序代码和根目录 `.gitignore`。
* 没有硬编码 token、绝对路径、个人 QQ 号、群号或私有 URL。
* 所有网络请求都有超时和异常处理。
* 所有定时任务、后台任务、连接和文件句柄能在卸载时清理。
* 用户可见文本是简体中文。
* README 写明安装、启用、配置、命令和常见问题。

## 推荐提示词

### 生成新插件

```text
请在 plugins/<plugin-name>/ 创建一个 MaiBot 第三方插件，实现 <功能描述>。
要求：
1. 只改插件目录，不改 MaiBot 主程序。
2. 使用 maibot-plugin-sdk 和 plugin.py / _manifest.json 结构。
3. 实现 on_load、on_unload、on_config_update、create_plugin。
4. 配置用 PluginConfigBase + Field，用户可见文本使用简体中文。
5. 给出 README、config.toml、必要的 .gitignore。
6. 完成后说明如何在 MaiBot 中启用和测试。
```

### 修改已有插件

```text
请只修改 plugins/<plugin-name>/ 内的文件，为现有插件增加 <功能描述>。
先阅读 _manifest.json、plugin.py、config.toml 和 README，沿用现有风格。
不要重构无关代码，不要整理全仓库格式。
如果需要主程序改动，先停止并说明原因。
```

### 排查插件问题

```text
请排查 plugins/<plugin-name>/ 的加载或运行问题。
优先检查 _manifest.json 校验、依赖声明、生命周期方法、create_plugin、配置模型、日志中的异常。
请给出最小修复，不要做无关重构。
```

## 测试建议

* 静态检查：确认 `_manifest.json` 是合法 JSON，`plugin.py` 可以被 Python 解释器导入。
* 本地加载：把插件放入 `plugins/`，启动 MaiBot，观察插件加载日志。
* WebUI 检查：在插件管理中确认插件出现、可启用、配置可编辑。
* 命令测试：用 `/ping` 一类命令确认 `@Command` 可触发。
* Tool 测试：通过正常聊天让 LLM 发现并调用工具，观察工具返回是否可读。
* 卸载测试：禁用或卸载插件后，确认后台任务、连接和缓存被清理。

## 发布前检查

* 插件仓库根目录包含 `_manifest.json`、`plugin.py`、`README.md`、`config.toml` 示例。
* README 包含功能说明、安装方式、配置项、命令、权限/能力说明、故障排查。
* 许可证与 `_manifest.json` 中的 `license` 一致。
* 依赖声明完整，避免要求用户手动安装未声明依赖。
* 没有提交 `.venv/`、`__pycache__/`、日志、数据库、密钥或本地配置。
* 如果准备提交到插件仓库，阅读插件仓库贡献指南并按其要求整理元信息。

---

---
url: /develop/architecture/webui-internals.md
---

# WebUI 内部机制

MaiBot WebUI 是基于 FastAPI 的 Web 管理后端，提供插件管理、配置编辑、认证鉴权、WebSocket 通信等功能。本文详述其架构、安全机制和通信协议。

## 整体架构

```mermaid
graph TD
    subgraph "客户端"
        A[React Dashboard]
    end
    subgraph "FastAPI 应用 (app.py)"
        B["AntiCrawlerMiddleware"]
        C["CORSMiddleware"]
        D["API Router /api/webui"]
        E["SPA 静态文件"]
    end
    subgraph "认证层 (core/)"
        F["TokenManager<br/>data/webui.json"]
        G["Cookie 管理<br/>maibot_session"]
        H["RateLimiter<br/>滑动窗口限流"]
    end
    subgraph "路由层 (routers/)"
        I[auth / config / system / model]
        J[plugin / memory / chat / emoji]
        K[person / jargon / expression / statistics]
        L["WebSocket /ws"]
    end
    subgraph "插件运行时 IPC"
        M["PluginRuntimeManager"]
        N["PluginSupervisor × 2"]
        O["Runner 子进程"]
    end
    A -->|HTTPS| B
    B --> C --> D
    D --> I
    D --> J
    D --> K
    D --> L
    I --> F
    F --> G
    A -->|WSS| L
    L -->|临时 Token| G
    D --> M
    M <-->|msgpack IPC| N
    N <-->|msgpack IPC| O
```

## FastAPI 应用工厂

源码位置：`src/webui/app.py`

`create_app()` 创建 FastAPI 实例并配置中间件和路由：

```python
def create_app(host="0.0.0.0", port=8001, enable_static=True) -> FastAPI:
    app = FastAPI(title="MaiBot WebUI")
    _setup_anti_crawler(app)   # 反爬虫中间件
    _setup_cors(app, port)     # CORS 跨域配置
    _register_api_routes(app)  # 注册 API 路由
    _setup_robots_txt(app)     # robots.txt
    if enable_static:
        _setup_static_files(app)  # SPA 静态文件 + 路径穿越防护
    return app
```

### CORS 配置

只允许 localhost 来源（开发端口 + 服务端口）：

```python
allow_origins = [
    "http://localhost:5173",      # Vite 开发服务器
    "http://127.0.0.1:5173",
    f"http://localhost:{port}",   # WebUI 服务端口
    f"http://127.0.0.1:{port}",
]
allow_credentials = True
```

### 静态文件安全

`_resolve_safe_static_file_path()` 通过 `resolve()` + `relative_to()` 双重检查防止路径穿越。

## 认证与安全

### Token 管理器

源码位置：`src/webui/core/security.py`

`TokenManager` 管理 WebUI 的访问令牌：

* `_create_new_token()` — 生成 64 位十六进制 Token（`secrets.token_hex(32)`）
* `get_token()` — 获取当前有效 Token
* `verify_token(token)` — 验证 Token（`secrets.compare_digest` 防时序攻击）
* `update_token(new_token)` — 更新 Token（需 ≥10 位，含大小写和特殊符号）
* `regenerate_token()` — 重新生成随机 Token
* `is_first_setup()` — 检查是否首次配置
* `mark_setup_completed()` — 标记配置完成

Token 存储在 `data/webui.json`（明文 JSON），依赖文件系统权限保护。

### Cookie 认证

源码位置：`src/webui/core/auth.py`

* **Cookie 名称** `maibot_session`
* **有效期** 7 天
* **HttpOnly** ✓（阻止 JS 读取）
* **SameSite** `lax`
* **Secure** 根据环境自动判断

认证流程：

```mermaid
sequenceDiagram
    participant C as 客户端
    participant S as 服务端
    participant T as TokenManager

    C->>S: POST /auth/verify {token}
    S->>T: verify_token(token)
    T-->>S: valid
    S->>C: Set-Cookie: maibot_session=token; HttpOnly; SameSite=lax
    C->>S: GET /api/webui/... (Cookie: maibot_session=token)
    S->>T: verify_token(cookie_value)
    T-->>S: valid
    S-->>C: 200 OK
```

Secure 标志判断逻辑：

1. 读取配置 `webui.secure_cookie`
2. 检查 `webui.mode == "production"`
3. 检查请求头 `X-Forwarded-Proto` 或 `request.url.scheme`
4. HTTP 连接强制禁用 Secure（即使配置要求）

### 限流器

源码位置：`src/webui/core/rate_limiter.py`

内存型滑动窗口限流器：

* **认证接口** — 10 次/分钟/IP，连续失败 5 次 → 封禁 10 分钟
* **普通 API** — 100 次/分钟/IP

::: warning
限流器为内存型，多实例部署时无法共享状态。
:::

### 反爬虫中间件

源码位置：`src/webui/middleware/anti_crawler.py`

`AntiCrawlerMiddleware` 提供四级模式：

* **`false`** — 禁用
* **`basic`** — 仅记录，不阻止（默认）
* **`loose`** — 60 次/分钟限制，阻止检测到的爬虫
* **`strict`** — 15 次/分钟限制，更严格检测

检测维度：

* **User-Agent**：匹配爬虫/扫描工具关键词（googlebot、nmap、shodan 等）
* **HTTP 头**：检测资产测绘工具特征头（x-scan、x-scanner 等）
* **IP 白名单**：支持精确 IP、CIDR、通配符格式
* **频率限制**：滑动窗口请求计数

## WebSocket 通信

### 统一 WebSocket

源码位置：`src/webui/routers/websocket/unified.py`

WebSocket 端点 `/ws` 支持多领域订阅和调用：

```mermaid
sequenceDiagram
    participant C as 客户端
    participant W as WebSocket /ws
    participant M as WebSocketManager

    C->>W: 连接 (token 或 Cookie 认证)
    W->>W: authenticate_websocket_connection()
    C->>W: subscribe {domain: "logs", topic: "main"}
    W->>M: 注册订阅
    M-->>C: logs 数据流
    C->>W: subscribe {domain: "maisaka_monitor", topic: "main"}
    M-->>C: Maisaka 监控事件
    C->>W: subscribe {domain: "plugin_progress", topic: "main"}
    M-->>C: 插件操作进度
```

### WebSocket 认证

源码位置：`src/webui/routers/websocket/auth.py`

双通道认证机制：

1. **临时 Token**（推荐）：先通过 `GET /api/webui/ws-token` 获取 60 秒有效的临时 Token，再在 WebSocket 握手时传入
2. **Cookie**：直接使用 `maibot_session` Cookie 认证

临时 Token 特性：

* 60 秒有效期
* 一次性使用（验证后立即删除）
* 验证原始 session Token 仍然有效

### 订阅域

* `logs` `main` — 日志流
* `maisaka_monitor` `main` — Maisaka 推理监控事件
* `plugin_progress` `main` — 插件操作进度
* `chat` `chat_id` — 聊天消息流

## 插件管理 IPC

### 插件运行时架构

```mermaid
graph TD
    subgraph "Host 主进程"
        A["PluginRuntimeManager<br/>(integration.py)"]
        A --> B["Builtin Supervisor<br/>内置插件"]
        A --> C["Third-party Supervisor<br/>第三方插件"]
        B --> D["ComponentRegistry"]
        C --> E["ComponentRegistry"]
        B --> F["RPCServer"]
        C --> G["RPCServer"]
        A --> H["HookSpecRegistry"]
        A --> I["HookDispatcher"]
    end
    subgraph "Runner 子进程 1 (内置)"
        J["Runner Main"]
        J --> K["Plugin A"]
        J --> L["Plugin B"]
    end
    subgraph "Runner 子进程 2 (第三方)"
        M["Runner Main"]
        M --> N["Plugin C"]
        M --> O["Plugin D"]
    end
    F <-->|msgpack over UDS/TCP/NamedPipe| J
    G <-->|msgpack over UDS/TCP/NamedPipe| M
```

### IPC 协议

源码位置：`src/plugin_runtime/protocol/`

**协议常量**：

* `PROTOCOL_VERSION = "1.0.0"`
* `MIN_SDK_VERSION` / `MAX_SDK_VERSION`：SDK 版本兼容范围

**Envelope 结构**：

* **`protocol_version`** `str` — 协议版本
* **`request_id`** `str` — 请求唯一 ID
* **`message_type`** `MessageType` — REQUEST / RESPONSE / BROADCAST
* **`method`** `str` — RPC 方法名
* **`plugin_id`** `str` — 插件 ID
* **`timestamp_ms`** `int` — 时间戳
* **`timeout_ms`** `int` — 超时
* **`payload`** `dict` — 载荷
* **`error`** `RPCError` — 错误信息

**消息类型**：

* `REQUEST`：Host → Runner 或 Runner → Host 的 RPC 请求
* `RESPONSE`：对 REQUEST 的响应
* `BROADCAST`：一对多通知

### 握手流程

```mermaid
sequenceDiagram
    participant H as Host (RPCServer)
    participant R as Runner

    R->>H: Connect (Transport)
    H->>R: HelloPayload (host_version, capabilities)
    R->>H: HelloResponsePayload (accepted, runner_version)
    H->>R: BootstrapPluginPayload (plugin configs)
    R->>H: RegisterPluginPayload (component declarations)
    H->>R: RunnerReadyPayload
    Note over H,R: 正常 RPC 通信开始
```

### 传输层

源码位置：`src/plugin_runtime/transport/`

帧格式：4 字节大端长度前缀 + msgpack 编码的 Envelope。

* **UDS (Unix Domain Socket)** — Linux / macOS，默认选择
* **Named Pipe** — Windows，Windows 默认
* **TCP** — 全平台，显式配置时使用

传输工厂根据运行平台自动选择最优传输方式。

### 编解码

源码位置：`src/plugin_runtime/protocol/codec.py`

使用 msgpack 进行 Envelope 的序列化和反序列化。

## 配置热重载

### WebUI 热重载

源码位置：`src/webui/webui_server.py`

WebUI 通过 `_maybe_register_reload_callback()` 注册回调，当配置文件变更时：

1. 配置管理器检测到 TOML 文件变化
2. 触发 `_reload_app()` 回调
3. 调用 `create_app()` 重新创建 FastAPI 实例
4. Uvicorn 切换到新应用

### 插件运行时热重载

源码位置：`src/plugin_runtime/integration.py`

`PluginRuntimeManager` 监听配置和插件源码变化：

1. **配置变更**：`_config_reload_callback()` 被触发
2. **依赖分析**：`DependencyPipeline` 计算受影响的插件
3. **重启计划**：根据变更类型决定是否需要重启 Runner
4. **执行重启**：`_handle_main_config_reload()` 协调所有 Supervisor 的重启

## 路由总览

源码位置：`src/webui/routes.py`

所有 API 路由挂载在 `/api/webui` 前缀下：

* `config_router` `/config` — 配置读写（TOML）
* `system_router` `/system` — 系统控制（重启/状态）
* `model_router` `/model` — 模型管理
* `memory_router` `/memory` — 长期记忆管理
* `chat_router` `/chat` — WebUI 聊天 API
* `emoji_router` `/emoji` — Emoji 管理
* `expression_router` `/expression` — 表达方式管理
* `jargon_router` `/jargon` — 黑话/词条管理
* `person_router` `/person` — 人物信息管理
* `plugin_router` `/plugin` — 插件安装/卸载/更新/配置
* `statistics_router` `/statistics` — 统计数据
* `ws_auth_router` `/ws-token` — WebSocket 临时 Token
* `unified_ws_router` `/ws` — 统一 WebSocket

### 认证端点

* **`/health`** `GET` 不需认证 — 健康检查
* **`/auth/verify`** `POST` 不需认证 — 验证 Token 并设置 Cookie
* **`/auth/logout`** `POST` 需认证 — 清除 Cookie
* **`/auth/check`** `GET` 需认证 — 检查认证状态
* **`/auth/update`** `POST` 需认证 — 更新 Token
* **`/auth/regenerate`** `POST` 需认证 — 重新生成 Token
* **`/setup/status`** `GET` 不需认证 — 首次配置状态
* **`/setup/complete`** `POST` 需认证 — 标记配置完成

## 依赖注入

源码位置：`src/webui/dependencies.py`

FastAPI 依赖注入提供认证和限流：

* `require_auth` — 验证 Cookie 中的 Token
* `require_auth_with_rate_limit` — 验证 Token + API 限流
* `verify_token_optional` — 可选验证（不强制）
* `require_plugin_token` — 插件专用认证
* `check_auth_rate_limit` — 认证接口限流
* `check_api_rate_limit` — 普通 API 限流

## SSRF 防护

源码位置：`src/webui/utils/network_security.py`

`validate_public_url()` 禁止访问私有地址：

* 127.0.0.1 / ::1（localhost）
* 10.0.0.0/8、172.16.0.0/12、192.168.0.0/16（私有网络）
* 169.254.0.0/16（链路本地）
* 其他保留地址段

适用于插件安装 URL、图片 URL 等外部请求场景。

## Hook 体系与 WebUI 的交互

WebUI 通过 `PluginRuntimeManager` 与 Hook 体系交互：

```mermaid
flowchart LR
    subgraph "WebUI 路由"
        A["/plugin/install"]
        B["/config/update"]
        C["/system/restart"]
    end
    subgraph "PluginRuntimeManager"
        D["install_plugin()"]
        E["_config_reload_callback()"]
        F["restart()"]
    end
    subgraph "Hook 系统"
        G["HookDispatcher"]
        H["HookSpecRegistry"]
    end
    A --> D
    B --> E
    C --> F
    D --> G
    E --> G
    G --> H
```

## 安全审计要点

* 🔴 高 — 文件上传无类型/大小验证 · `routers/memory.py`
* 🔴 高 — WebSocket 无 Origin 校验 · `routers/websocket/unified.py`
* 🔴 高 — Config API 泄露 API Key · `routers/config.py`
* 🟡 中 — 无 CSRF 保护 · 全局
* 🟡 中 — 无 CSP 头 · 全局
* 🟡 中 — 系统重启无二次确认 · `routers/system.py`
* 🟢 低 — 内存型限流器不共享 · `core/rate_limiter.py`

::: warning
生产环境部署必须使用反向代理（如 Nginx），配置 HTTPS，并设置适当的 CORS 和安全头。
:::

### 缓解建议

针对上述安全审计要点，建议采取以下缓解措施：

**文件上传无验证** ：添加上传文件类型白名单（仅允许图片/文档等必要格式）及大小上限（如 10MB），并使用 `python-magic` 校验真实 MIME 类型

**WebSocket 无 Origin 校验** ：在 `authenticate_websocket_connection()` 中检查 `Origin` 头，仅允许已配置的来源

**Config API 泄露 API Key** ：在配置 Schema 输出时对敏感字段（如 `api_key`、`token`、`secret`）进行脱敏处理，仅在前端呈现掩码值

**无 CSRF 保护** ：建议在表单类请求中添加 CSRF Token 校验，或对写操作检查 `Referer`/`Origin` 头是否为允许的来源

**无 CSP 头** ：在响应中添加 `Content-Security-Policy` 头，限制脚本、样式、字体等资源的加载来源

**系统重启无确认** ：在 `/system/restart` 端点要求用户二次确认（如重新输入 Token 或发送确认参数）

**限流器不共享** ：多实例部署时应改用 Redis 等外部存储实现分布式限流

---

---
url: /manual/deployment/one_key.md
---
# 一键包部署教程

## 免责声明:

* **本教程仅供帮助，如果您的账号因违反平台官方规则被封禁或造成其他损失，本教程不承担任何责任**

### 建议：如果你遇到不懂的问题，善用搜索引擎（比如必应/百度）寻找答案，或者向 [DeepSeek](https://chat.deepseek.com/) 寻求帮助，或进群询问

还可以翻阅:[常见问题](https://www.kdocs.cn/l/ctOGhVv6L8Yq)

![询问 DeepSeek](/images/onekey/onekey_00.png)
（带上本文档的链接，记得开`深度思考`和`联网搜索`，如图,向DeepSeek询问日志问题）

> https://docs.mai-mai.org/manual/deployment/
>
> 参考上面的帮助文档，帮我看看下面的日志

## 准备工作

* 确保你的系统版本至少为 Windows 10 (如果你的系统版本是 Win7 ，甚至更低，那么现在可以放弃了)
* 准备好一份已经下载好的一键（Onekey）包（可以从群文件或 Github 获取，这里我们用 0.3.2 full 版本进行演示（由于版本更新可能导致界面变化，以你看到的界面为准）

> lite 版本不带Python依赖，需要稍后在软件内自行安装，安装位置为 设置-模块更新

* 假设你此时已经成功获取了安装包，如图，右键文件，选择打开所在文件夹
  ![](/images/onekey/onekey_01.webp)
  ![](/images/onekey/onekey_02.webp)
  ![](/images/onekey/onekey_03.webp)
  ![](/images/onekey/onekey_04.webp)

* 双击安装，然后点击下一步下一步下一步……（安装好后，首页大概长这样）
  ![](/images/onekey/onekey_05.webp)

* 接下来，点击 `更新` ，让 MaiBot 更新到最新测试版（1.0.0）
  ![](/images/onekey/onekey_06.webp)
  ![](/images/onekey/onekey_07.webp)

* 点击 `开始更新` ，把本地版本更新到最新版（我这里是已经更新好了）

## 接入QQ

* 接下来让我们连接到QQ，点击 `新增平台`
  ![](/images/onekey/onekey_08.webp)

* 我这里用 NapCat 进行演示，建议为机器人注册一个QQ小号
  ![](/images/onekey/onekey_08.webp)

## （！警告！：搭建机器人可能导致QQ被风控、甚至被封禁的风险！！不要使用大号！！不要使用日常使用的QQ账号！！）

* 填入你准备好的，机器人使用的QQ号，填完后点击配置并启动
  ![](/images/onekey/onekey_09.webp)

* 然后就会弹出这个界面，先不急着配置白名单，待会在 Web UI 中配置，我们先点击右下角的 `保存并关闭`
  ![](/images/onekey/onekey_10.webp)

* 然后我们点击终端
  ![](/images/onekey/onekey_11.webp)

* 再点击 NapCat,打开手机QQ，切换到机器人使用的QQ号，扫码登录

* 切换到 MaiBot 页面，跟随首次配置向导完成配置（也可以点击右侧按钮，在浏览器里打开 Web UI ）

![](/images/onekey/onekey_16.webp)

## 很好！我们已经完成了一键包的配置，接下来是让我们的机器人能够正常接收消息

**（这里假设你已经成功在 模型管理 里配置好模型，关于如何配置模型厂商，请自行上网搜索教程；关于如何配置模型功能，请参考[常见问题](https://www.kdocs.cn/l/ctOGhVv6L8Yq)）**

* 我们需要配置 Napcat 白名单，先点击插件管理
  ![](/images/onekey/onekey_12.webp)

* 点击 Napcat\_Adapter 适配器
  ![](/images/onekey/onekey_13.webp)

* 点添加项目，填入群号或用户QQ号，白名单（whitelist）模式下，机器人只能接收到 列表内 的群聊或私聊，黑名单（blacklist）模式则是屏蔽 列表内 群聊或私聊

* 建议先拿另一个号加机器人的QQ为好友进行测试，功能正常后再添加更多白名单
  ![](/images/onekey/onekey_14.webp)

* 最后不要忘记保存插件设置
  ![](/images/onekey/onekey_15.webp)

* 接下来可以在 WebUI-日志查看器（左边的菜单是可以滚动的，没看到记得往下滑） 或 软件-终端-MaiBot Core 里查看日志，如果日志里显示 `统一 WebSocket 客户端已连接` ,并成功接收到消息，说明 NapCat 连接成功

* ### 最后，欢迎开始你的 MaiBot 之旅！

---

---
url: /develop/plugin-dev/event-handlers.md
---

# 事件处理器

`@EventHandler` 是用于订阅消息和工作流事件的组件装饰器。与 `@HookHandler` 的命名 Hook 点机制不同，`@EventHandler` 基于固定的 `EventType` 枚举值订阅事件，适合在消息处理流程的特定阶段进行拦截或观察。

## 装饰器签名

```python
from maibot_sdk import EventHandler
from maibot_sdk.types import EventType

@EventHandler(
    name: str,                                      # 组件名称（必填）
    description: str = "",                          # 组件描述
    event_type: EventType = EventType.ON_MESSAGE,   # 订阅的事件类型
    intercept_message: bool = False,                # 是否阻塞消息链
    weight: int = 0,                                # 权重，越高越先执行
    **metadata,                                     # 额外元数据
)
```

## EventType 事件类型

* **`UNKNOWN`** — 未知事件
* **`ON_START`** — 插件启动
* **`ON_STOP`** — 插件停止
* **`ON_MESSAGE_PRE_PROCESS`** — 消息预处理阶段（过滤、拦截的最佳时机）
* **`ON_MESSAGE`** — 消息处理阶段
* **`ON_PLAN`** — 规划阶段
* **`POST_LLM`** — LLM 调用后（响应已生成）
* **`AFTER_LLM`** — LLM 调用完成后
* **`POST_SEND_PRE_PROCESS`** — 发送预处理阶段
* **`POST_SEND`** — 消息发送后
* **`AFTER_SEND`** — 消息发送完成后

## intercept\_message 参数

`intercept_message` 控制 EventHandler 是否以阻塞方式参与消息处理链：

* **`False`**（默认） — 异步 fire-and-forget，不影响消息主流程
* **`True`** — 同步阻塞，主程序等待处理器返回后才继续

设为 `True` 时，处理器可以拦截、修改甚至阻止消息的后续处理。

## weight 权重

多个 EventHandler 订阅同一 `EventType` 时，`weight` 决定执行顺序：

* **值越高越先执行**
* 默认值为 `0`
* 与旧系统的 `weight` 语义一致

## 基本用法

### ON\_START：插件初始化

```python
from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class StartupPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "on_startup",
        description="插件启动时初始化资源",
        event_type=EventType.ON_START,
    )
    async def handle_startup(self, **kwargs):
        self.ctx.logger.info("启动事件触发，开始初始化")
        # 在这里执行启动时需要的初始化逻辑
```

### ON\_MESSAGE\_PRE\_PROCESS：消息过滤

```python
from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class MessageFilterPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("消息过滤插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("消息过滤插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "spam_filter",
        description="过滤垃圾消息",
        event_type=EventType.ON_MESSAGE_PRE_PROCESS,
        intercept_message=True,   # 阻塞模式，可以拦截消息
        weight=100,               # 高权重，优先执行
    )
    async def filter_spam(self, message, **kwargs):
        raw_message = message.get("raw_message", "")
        user_id = message.get("user_info", {}).get("user_id", "")

        # 检测垃圾消息
        if self._is_spam(raw_message, user_id):
            self.ctx.logger.info("拦截垃圾消息: user=%s, text=%s", user_id, raw_message)
            return {"intercepted": True, "reason": "spam"}

        # 放行消息
        return {"intercepted": False}

    def _is_spam(self, text: str, user_id: str) -> bool:
        # 简单的垃圾消息检测逻辑
        spam_keywords = ["广告", "加群", "免费"]
        return any(kw in text for kw in spam_keywords)
```

### ON\_MESSAGE：消息观察

```python
from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class MessageObserverPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self._message_count = 0

    async def on_unload(self) -> None:
        self.ctx.logger.info("总消息数: %d", self._message_count)

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "message_counter",
        description="统计消息数量",
        event_type=EventType.ON_MESSAGE,
    )
    async def count_message(self, message, **kwargs):
        self._message_count += 1
        self.ctx.logger.debug("收到第 %d 条消息", self._message_count)
```

### AFTER\_LLM：LLM 响应后处理

```python
from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class LLMPostProcessor(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("LLM 后处理插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("LLM 后处理插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "llm_response_logger",
        description="记录 LLM 响应",
        event_type=EventType.AFTER_LLM,
        weight=50,
    )
    async def log_llm_response(self, **kwargs):
        response = kwargs.get("response", "")
        self.ctx.logger.info("LLM 响应: %s", response[:200])
```

### POST\_SEND：发送后回调

```python
from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class SendAuditPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("发送审计插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("发送审计插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "send_audit",
        description="审计所有发送的消息",
        event_type=EventType.POST_SEND,
    )
    async def audit_send(self, **kwargs):
        message = kwargs.get("message", {})
        self.ctx.logger.info(
            "消息已发送: stream_id=%s",
            message.get("stream_id", "unknown"),
        )
```

## 与 HookHandler 的区别

* **订阅方式**：`@EventHandler` `EventType` 枚举值 → `@HookHandler` 命名 Hook 点字符串
* **粒度**：`@EventHandler` 固定事件类型，数量有限 → `@HookHandler` 自定义 Hook 名称，可无限扩展
* **拦截方式**：`@EventHandler` `intercept_message=True` → `@HookHandler` `mode=HookMode.BLOCKING`
* **优先级**：`@EventHandler` `weight` 数值权重 → `@HookHandler` `order` 三档枚举 + 全局排序
* **异常策略**：`@EventHandler` 无专用参数 → `@HookHandler` `error_policy` 控制
* **适用场景**：`@EventHandler` 消息流程的固定阶段 → `@HookHandler` 主程序定义的任意扩展点

一般原则：

* 如果需要在消息流程的**固定阶段**（如收到消息、LLM 返回后）执行逻辑，使用 `@EventHandler`
* 如果需要订阅主程序定义的**特定命名 Hook 点**（如 `heart_fc.heart_flow_cycle_start`），使用 `@HookHandler`

## 事件处理流程

```mermaid
sequenceDiagram
    participant Host as 主程序
    participant EH1 as EventHandler (weight=100)
    participant EH2 as EventHandler (weight=50)
    participant EH3 as EventHandler (weight=0)

    Host->>Host: 触发事件 EventType
    Host->>Host: 按 weight 降序排列处理器
    Host->>EH1: 执行 (weight=100)
    EH1-->>Host: 返回结果
    Host->>EH2: 执行 (weight=50)
    EH2-->>Host: 返回结果
    Host->>EH3: 执行 (weight=0)
    EH3-->>Host: 返回结果
    Note over Host: 若 intercept_message=True，主流程等待每个处理器返回
```

---

---
url: /develop/architecture/event-bus.md
---

本文基于 code-map 快照编写。

# 事件总线架构

MaiBot 的 EventBus 是进程内通信中枢，负责把分散在启动流程、聊天入口、LLM 管线、发送管线和插件运行时之间的事件，统一收敛到发布/订阅模型中。它不直接定义业务动作，也不负责具体功能执行，而是提供事件注册、事件触发、handler 排序、消息隔离和跨运行时桥接这些基础能力。

## 概述

EventBus 位于 `maibot/src/core/event_bus.py`，属于 `core` 基础设施层。它和 `maibot/src/core/types.py` 中的 `EventType`、`MaiMessages` 共同构成主程序内部事件系统的最小闭环。

**EventBus** ：全局事件总线实例，提供 `subscribe()`、`unsubscribe()`、`emit()` 和任务取消能力。
**EventHandler** ：源码中的 handler 签名，接收 `Optional[MaiMessages]`，返回 `(continue_flag, modified_message)`。
**EventInterceptor** ：文档概念中的拦截型 handler，源码中通过 `intercept=True` 标记，顺序执行，可修改消息并中止链路。
**EventListener** ：文档概念中的非拦截型 handler，源码中通过 `intercept=False` 标记，异步并发执行，不参与主流程控制。
**InterceptResult** ：文档概念中的拦截结果。当前实现没有独立类，实际等价于返回 `(False, message)`，概念上可理解为 `intercept_result.abort()`。
**EventType** ：事件类型枚举，定义系统内可被识别的标准事件名。
**MaiMessages** ：事件消息模型，承载消息段、纯文本、LLM 提示词、LLM 响应、流 ID 和附加数据。

EventBus 的核心职责不是替代 Hook 系统，而是为事件驱动调用提供底层通道。业务模块可以在关键执行点调用 `event_bus.emit()`，插件运行时可以通过 IPC 桥接接收事件，内部 handler 可以通过注册表参与事件处理。

## 架构图

```mermaid
flowchart TD
    subgraph "发布者"
        A["main.py\nON_START"]
        B["chat 消息入口\nSessionMessage / MessageSending"]
        C["LLM 与发送管线\nPOST_LLM / AFTER_LLM / POST_SEND"]
        D["系统停止流程\nON_STOP"]
    end

    subgraph "EventBus"
        E["event_bus.emit(event_type, message)"]
        F["按 event_type 匹配 handler"]
        G["按 weight 降序排序"]
        H["拦截型 handler\nintercept=True"]
        I["非拦截型 handler\nintercept=False"]
        J["消息 deepcopy\n隔离修改副作用"]
        K["bridge_event\nIPC 插件运行时"]
    end

    subgraph "执行结果"
        L["继续执行\ncontinue_flag=True"]
        M["中止链路\ncontinue_flag=False"]
        N["fire-and-forget\n后台任务"]
        O["返回修改后的 MaiMessages"]
    end

    subgraph "插件运行时"
        P["PluginRuntimeManager"]
        Q["Supervisor dispatch_event"]
        R["EventDispatcher"]
        S["EventHandler 组件"]
    end

    A --> E
    B --> E
    C --> E
    D --> E
    E --> J --> F --> G --> H
    G --> I
    H -->|"顺序 await"| L
    H -->|"返回 False"| M
    L --> I
    I --> N
    L --> K
    K --> P --> Q --> R --> S
    K --> O
```

这张图表达的是 EventBus 的一次完整分发：发布者调用 `emit()`，EventBus 根据事件类型取出 handler，按 `weight` 排序，先执行拦截型 handler，再在继续执行的前提下调度非拦截型 handler，最后把事件桥接到插件运行时。

## 核心概念

### 拦截型 handler

拦截型 handler 是主流程的一部分。它在 `subscribe()` 时通过 `intercept=True` 注册，在 `emit()` 中被同步等待。每个 handler 都可以看到当前消息对象，也可以返回新的消息对象。

**执行顺序** ：同一事件类型下的拦截型 handler 按 `weight` 降序执行，权重越大越靠前。
**消息隔离** ：`emit()` 开始时会对传入消息执行 `deepcopy()`，避免外部对象被直接修改。
**可修改消息** ：handler 返回的 `modified_message` 非空时，会替换当前 `current_message`。
**可中止链路** ：handler 返回的 `continue_flag` 为 `False` 时，EventBus 停止后续拦截型 handler，并跳过非拦截型 handler。
**异常处理** ：单个拦截型 handler 异常不会让整个事件总线崩溃，异常会被记录后继续处理下一个 handler。

概念上，拦截型 handler 可以写成下面的形式：

```python
async def security_filter(message: Optional[MaiMessages]):
    if should_block(message):
        return False, message  # 等价于 intercept_result.abort()
    return True, message
```

如果某个 handler 需要返回修改后的消息，可以把新的 `MaiMessages` 作为第二个返回值。调用方收到 `emit()` 的结果后，可以继续把 `modified_message` 写回业务对象。

### 非拦截型 handler

非拦截型 handler 是旁路观察者。它在 `subscribe()` 时通过 `intercept=False` 注册，在 `emit()` 中被放入后台任务执行。

**执行时机** ：只有所有拦截型 handler 都允许继续时，才会调度非拦截型 handler。
**执行方式** ：通过 `asyncio.create_task()` 创建任务，不等待任务完成。
**控制能力** ：非拦截型 handler 不能中止事件链路，也不能改变 `emit()` 的返回值。
**消息快照** ：每个非拦截型 handler 会收到当前消息的 `deepcopy()`，避免并发任务之间互相覆盖。
**任务跟踪** ：运行中的任务会按 handler 名称记录在 `_running_tasks`，支持 `cancel_handler_tasks()` 取消指定 handler 的任务。

概念上，非拦截型 handler 适合做审计、统计、日志、监控和异步副作用：

```python
async def audit_listener(message: Optional[MaiMessages]):
    await write_audit_log(message)
    return True, message
```

即使 `audit_listener()` 抛错，也不会影响主链路。异常会在任务完成回调中被记录。

### EventType 枚举分类

`EventType` 定义在 `maibot/src/core/types.py`。它不是插件声明文件，而是主程序共享的事件类型字典。EventBus 在初始化时会预注册所有内置 `EventType`，因此标准事件在没有任何 handler 时也能被识别。

**生命周期事件** ：`ON_START`、`ON_STOP`，用于启动和停止阶段。
**消息预处理事件** ：`ON_MESSAGE_PRE_PROCESS`，用于消息进入核心处理前的拦截点。
**消息主链事件** ：`ON_MESSAGE`，用于消息处理主链上的事件通知和拦截。
**计划与推理事件** ：`ON_PLAN`、`POST_LLM`、`AFTER_LLM`，用于 LLM 推理前后和计划生成相关节点。
**发送管线事件** ：`POST_SEND_PRE_PROCESS`、`POST_SEND`、`AFTER_SEND`，用于消息发送前后。
**未知事件** ：`UNKNOWN`，用于无法归类的事件或兼容场景。

### handler 注册模型

EventBus 的 handler 是纯 async callable，不需要继承插件基类，也不需要注册为 Hook。注册信息由 `_HandlerEntry` 保存。

**event\_type** ：事件类型，可以是 `EventType` 枚举，也可以是字符串。
**handler** ：异步 callable，签名为 `(Optional[MaiMessages]) -> (bool, Optional[MaiMessages])`。
**name** ：handler 标识名，用于取消注册和任务追踪。
**weight** ：权重，值越大越先执行。
**intercept** ：是否作为拦截型 handler 执行。

注册流程很简单：

```python
event_bus.subscribe(
    event_type=EventType.ON_MESSAGE,
    handler=handler_func,
    name="example.handler",
    weight=10,
    intercept=True,
)
```

取消注册时只需要提供事件类型和 handler 名称：

```python
event_bus.unsubscribe(event_type=EventType.ON_MESSAGE, name="example.handler")
```

## 关键流程

EventBus 的一次 `emit()` 可以拆成四个阶段：事件触发、handler 匹配、拦截型顺序执行、非拦截型并发执行。

```mermaid
sequenceDiagram
    participant Publisher as 发布者
    participant EB as EventBus
    participant Store as _handlers
    participant I as 拦截型 handler
    participant L as 非拦截型 handler
    participant IPC as PluginRuntimeManager

    Publisher->>EB: emit(event_type, message)
    EB->>Store: 按 event_type 查询 handler
    Store-->>EB: handler 列表
    EB->>EB: deepcopy(message)
    EB->>EB: 按 weight 降序排序
    EB->>I: await handler(current_message)
    I-->>EB: (True, modified_message)
    EB->>I: 继续执行下一个拦截型 handler
    I-->>EB: (False, message)
    alt 被中止
        EB-->>Publisher: (False, current_message)
    else 继续执行
        EB->>L: create_task(handler(message_snapshot))
        EB->>IPC: bridge_event(event_type, message_dict)
        IPC-->>EB: (continue_flag, modified_dict)
        EB-->>Publisher: (continue_flag, modified_message)
    end
```

### emit 到 handler 匹配

`emit(event_type, message)` 是唯一的触发入口。它从 `_handlers` 中按 `event_type` 查找 handler 列表。如果事件类型没有 handler，会直接返回 `(True, None)`。

**事件类型查找** ：`handlers = self._handlers.get(event_type, [])`。
**空列表处理** ：没有 handler 时返回继续标志和空消息。
**排序策略** ：注册时已经按 `weight` 降序排序，因此分发时直接使用当前列表。
**字符串事件** ：除了 `EventType` 枚举，也允许字符串事件类型，方便运行时扩展。

### 拦截型顺序执行

拦截型 handler 被单独收集到 `intercept_handlers`。EventBus 会逐个 `await` 它们。

**继续标志** ：初始值为 `True`。
**当前消息** ：使用 `current_message` 保存经过前序 handler 修改后的消息。
**修改消息** ：如果 handler 返回的 `modified` 非空，则替换 `current_message`。
**中止链路** ：如果 handler 返回的 `should_continue` 为 `False`，则 `continue_flag` 变为 `False` 并跳出循环。
**异常隔离** ：异常会被记录，不会中断同一事件的其他 handler。

### 非拦截型并发执行

只有 `continue_flag` 仍为 `True` 时，非拦截型 handler 才会被调度。每个 handler 都拿到一份当前消息快照。

**调度方式** ：`asyncio.create_task(entry.handler(message))`。
**任务命名** ：任务名设置为 handler 名称，便于日志和取消。
**完成回调** ：任务完成后会记录异常，并从 `_running_tasks` 移除。
**不可中止** ：非拦截型 handler 的返回值不会影响 `emit()` 的最终结果。

### IPC 插件运行时桥接

拦截型和非拦截型 handler 执行后，EventBus 会把事件桥接到插件运行时。这个步骤位于 `event_bus.py` 的 `_bridge_to_ipc_runtime()`。

**继续检查** ：如果主链路已经被拦截型 handler 中止，则不再桥接。
**运行时检查** ：如果插件运行时未运行，则直接返回当前结果。
**事件值转换** ：`EventType` 会转换为 `.value`，字符串事件则保持原值。
**消息序列化** ：`MaiMessages` 会通过 `to_transport_dict()` 转为可 IPC 传输的字典。
**回写修改** ：插件运行时返回的修改字典会通过 `apply_transport_update()` 回写到消息对象。

## 模块交互

EventBus 不是一个孤立组件。它通过 `core#类型系统` 获得事件名和消息模型，通过 `plugin_runtime#Hook调度器` 与插件运行时协作，通过 `chat#消息入口调度` 接收消息入口产生的事件。

### 与 core#类型系统协作

`core#类型系统` 主要指 `maibot/src/core/types.py`。它提供 EventBus 需要的两类核心类型。

**EventType** ：定义标准事件名，EventBus 初始化时预注册这些枚举。
**MaiMessages** ：定义统一消息结构，拦截型 handler 可以修改其中的字段。
**ModifyFlag** ：记录 IPC 回写时哪些字段被修改，例如消息段、纯文本、LLM prompt。
**Transport 方法** ：`to_transport_dict()` 和 `apply_transport_update()` 支撑跨 IPC 的消息传递。

`MaiMessages` 的字段覆盖了事件系统常见需求：

**message\_segments** ：消息段列表，来自 `maim_message.Seg`。
**message\_base\_info** ：平台、用户、群聊等基础信息。
**plain\_text** ：处理后的纯文本消息。
**raw\_message** ：原始消息文本。
**stream\_id** ：聊天流 ID，用于定位会话上下文。
**llm\_prompt** ：发送给 LLM 的提示词。
**llm\_response\_content** ：LLM 响应正文。
**llm\_response\_reasoning** ：LLM 推理内容。
**llm\_response\_tool\_call** ：LLM 工具调用信息。
**action\_usage** ：使用的 Action 列表。
**additional\_data** ：附加数据，用于业务模块传递临时上下文。

### 与 plugin\_runtime#Hook调度器协作

EventBus 与 Hook 调度器不是同一个系统，但它们共享相似的发布/订阅思想。EventBus 按事件类型分发，Hook 调度器按命名 Hook 分发。

**EventBus** ：面向 `EventType`，主入口是 `event_bus.emit()`。
**HookDispatcher** ：面向 Hook 名称，主入口是 `PluginRuntimeManager.invoke_hook()`。
**EventHandler** ：插件运行时中的事件处理器组件，由 `EventDispatcher` 调度。
**HookHandler** ：插件运行时中的命名 Hook 处理器，由 `HookDispatcher` 调度。
**阻塞处理器** ：EventBus 中叫拦截型 handler，Hook 中叫 `blocking` handler。
**观察处理器** ：EventBus 中叫非拦截型 handler，Hook 中叫 `observe` handler。

`plugin_runtime#Hook调度器` 的相关源码位置如下：

**PluginRuntimeManager** ：`maibot/src/plugin_runtime/integration.py`，提供 `bridge_event()` 和 `invoke_hook()`。
**EventDispatcher** ：`maibot/src/plugin_runtime/host/event_dispatcher.py`，负责插件事件处理器分发。
**HookDispatcher** ：`maibot/src/plugin_runtime/host/hook_dispatcher.py`，负责命名 Hook 分发。
**Supervisor** ：`maibot/src/plugin_runtime/host/supervisor.py`，在 Supervisor 内暴露 `dispatch_event()` 和 `invoke_hook()`。

EventBus 的桥接流程是先调用 `PluginRuntimeManager.bridge_event()`，再由 `bridge_event()` 遍历 Supervisor，调用 `supervisor.dispatch_event()`。Supervisor 内部再交给 `EventDispatcher` 查询 `EventHandlerEntry` 并执行。

### 与 chat#消息入口调度协作

`chat#消息入口调度` 是 EventBus 最自然的业务入口之一。聊天入口收到外部平台消息后，会形成 `SessionMessage` 或 `MessageSending`，再转换为 `MaiMessages`。

**消息转换工具** ：`maibot/src/chat/event_helpers.py` 提供 `build_event_message()`。
**入站消息** ：`SessionMessage` 可以转换为 `MaiMessages`。
**发送消息** ：`MessageSending` 可以转换为 `MaiMessages`。
**流上下文** ：如果只有 `stream_id`，可以从 `chat_manager` 查找会话并构建最小事件消息。
**生命周期事件** ：`ON_START` 和 `ON_STOP` 没有消息体，`build_event_message()` 对它们返回 `None`。

`maibot/src/chat/message_receive/bot.py` 中保留了事件总线的集成点注释，例如 `ON_MESSAGE_PRE_PROCESS` 和 `ON_MESSAGE` 的调用位置。当前实现也使用插件 Hook 在消息处理前后执行 `chat.receive.before_process` 和 `chat.receive.after_process`。这说明 EventBus 与 chat 入口的关系是明确的，但具体哪些事件点已经启用，应以源码中的实际调用为准。

## 事件类型枚举

本节列出当前 `EventType` 枚举中的关键事件，以及文档中常见的兼容事件名。它们都可以作为 EventBus 的事件类型键使用，其中枚举事件会在初始化时被预注册，字符串事件名则适合插件或外部系统扩展。

**`MESSAGE_RECEIVED`** ：兼容事件名，常用于描述外部平台消息已被接收。当前 `EventType` 枚举未直接定义该名称，可通过字符串事件类型注册或桥接。
**`COMMAND_EXECUTED`** ：兼容事件名，常用于描述命令处理完成后发布通知。当前 `EventType` 枚举未直接定义该名称，可通过字符串事件类型注册或桥接。
**`ON_START`** ：启动事件。`maibot/src/main.py` 在初始化聊天管理器、记忆自动化服务后触发该事件，EventBus 会统一桥接到 IPC 插件运行时。
**`ON_STOP`** ：停止事件。系统重启或停止流程中可以触发该事件，用于通知需要清理资源的组件。
**`ON_MESSAGE_PRE_PROCESS`** ：消息预处理事件。适合在消息进入核心处理前做拦截、改写或过滤。当前 chat 入口中相关调用点是 TODO，说明该事件位已预留。
**`ON_MESSAGE`** ：消息主链事件。适合在消息完成基础处理后、进入推理或命令处理前参与流程控制。
**`ON_PLAN`** ：计划事件。用于计划生成相关节点，可携带 `stream_id` 和 LLM 上下文。
**`POST_LLM`** ：LLM 后事件。LLM 已生成响应后触发，可用于改写响应、审计或触发后续动作。
**`AFTER_LLM`** ：LLM 完成事件。用于 LLM 管线结束后的旁路通知或统计。
**`POST_SEND_PRE_PROCESS`** ：发送前预处理事件。适合在发送前做最终检查或改写。
**`POST_SEND`** ：发送事件。消息即将发送时触发，可用于审计、计数或外部同步。
**`AFTER_SEND`** ：发送后事件。消息发送完成后触发，适合做日志、统计和状态更新。
**`UNKNOWN`** ：未知事件类型。用于兼容未归类事件或运行时动态事件。

### 事件分类说明

**生命周期类** ：`ON_START`、`ON_STOP` 不依赖消息体，通常在应用启动和停止阶段触发。
**入站消息类** ：`MESSAGE_RECEIVED`、`ON_MESSAGE_PRE_PROCESS`、`ON_MESSAGE` 面向外部平台进入系统的消息。
**命令处理类** ：`COMMAND_EXECUTED` 面向命令执行完成后的通知或审计。
**推理计划类** ：`ON_PLAN`、`POST_LLM`、`AFTER_LLM` 面向 LLM 推理和计划生成过程。
**出站发送类** ：`POST_SEND_PRE_PROCESS`、`POST_SEND`、`AFTER_SEND` 面向消息发送过程。
**兼容类** ：`UNKNOWN` 用于兜底，不应作为新业务事件的首选类型。

## 扩展点/Hook

EventBus 自身不提供 Hook 系统。它没有 Hook 规格注册表，没有 `allow_abort`、`allow_observe`、`order` 等 Hook 语义，也不直接管理插件组件声明。它提供的是更底层的事件发布/订阅能力。

**EventBus 负责** ：事件类型匹配、handler 注册、顺序拦截、异步旁路、消息快照、IPC 桥接。
**Hook 系统负责** ：命名 Hook 规格、插件组件声明、blocking/observe 模式、early/normal/late 顺序、abort 策略。
**EventHandler 负责** ：插件侧按事件类型注册的处理器组件。
**HookHandler 负责** ：插件侧按 Hook 名称注册的处理器组件。

EventBus 是 Hook 系统的底层实现基础，原因在于它验证并沉淀了几个关键模式。

**发布/订阅** ：调用方只关心事件类型，不直接知道谁会处理事件。
**权重排序** ：handler 可以按优先级排列，避免硬编码调用顺序。
**拦截与旁路分离** ：主流程控制权和观察型副作用被区分开。
**消息不可变性保护** ：通过 `deepcopy()` 降低 handler 之间的副作用耦合。
**跨运行时扩展** ：通过 IPC 桥接把事件传播到插件 Supervisor。

如果未来需要新增 Hook，不应把 Hook 规格塞进 EventBus。更合理的方向是让 Hook 系统复用 EventBus 的排序、拦截、旁路和桥接思想，但保留自己的命名、规格、插件声明和错误策略。

## 设计边界

EventBus 适合处理进程内事件和插件运行时桥接，不适合承载所有业务控制逻辑。

**适合使用 EventBus** ：启动停止通知、消息入口拦截、发送前后通知、LLM 管线旁路事件、跨模块状态同步。
**不适合使用 EventBus** ：高频细粒度状态更新、需要强事务保证的操作、需要复杂权限模型的业务流程、需要长期持久化的事件日志。
**适合拦截型 handler** ：安全过滤、敏感词处理、消息改写、流程中止。
**适合非拦截型 handler** ：统计、审计、监控、异步通知、缓存刷新。
**适合 Hook 系统** ：插件显式声明的扩展点、需要参数 Schema 的扩展点、需要 blocking/observe 策略的扩展点。

## 实现细节

### handler 存储结构

EventBus 使用 `_handlers` 保存事件类型到 handler 条目的映射。

**键** ：`EventType` 枚举或字符串事件类型。
**值** ：`_HandlerEntry` 列表。
**排序** ：每次 `subscribe()` 后都会按 `weight` 降序重排。
**预注册** ：构造函数中遍历所有 `EventType`，为内置事件创建空列表。

### 消息隔离策略

`emit()` 会对传入消息执行 `deepcopy()`。这个设计让 handler 可以安全修改消息对象，而不会污染调用方原始对象。

**输入消息** ：调用方传入的 `message`。
**当前消息** ：`current_message`，拦截型 handler 之间传递的可变副本。
**异步快照** ：非拦截型 handler 收到的是 `current_message.deepcopy()`。
**IPC 消息** ：桥接时转换为传输字典，插件侧修改后再回写。

### 异常策略

EventBus 对 handler 异常采用隔离策略。

**拦截型异常** ：记录错误，继续执行后续 handler。
**非拦截型异常** ：在任务完成回调中记录错误。
**IPC 桥接异常** ：记录 warning，不影响主链路返回值。
**任务创建失败** ：记录错误，不阻塞其他 handler。

这种策略让事件总线保持稳定，但也意味着调用方不能依赖某个 handler 一定执行成功。需要强一致性的逻辑应放在业务主流程或 Hook 的 blocking 策略中。

### 任务取消

`cancel_handler_tasks(handler_name)` 用于取消指定 handler 的运行中任务。

**查找任务** ：从 `_running_tasks` 中取出 handler 名称对应的任务列表。
**取消任务** ：对未完成的任务调用 `cancel()`。
**等待回收** ：通过 `asyncio.gather(..., return_exceptions=True)` 等待取消完成。
**清理记录** ：任务完成回调会从 `_running_tasks` 中移除已完成任务。

## 典型调用示例

### 注册拦截型 handler

```python
async def before_message(message: Optional[MaiMessages]):
    if not message:
        return True, None
    if message.plain_text.startswith("!ignore"):
        return False, message
    return True, message

event_bus.subscribe(
    event_type=EventType.ON_MESSAGE,
    handler=before_message,
    name="core.before_message_filter",
    weight=100,
    intercept=True,
)
```

### 注册非拦截型 handler

```python
async def message_audit(message: Optional[MaiMessages]):
    if not message:
        return True, None
    await audit_service.record(message)
    return True, message

event_bus.subscribe(
    event_type=EventType.ON_MESSAGE,
    handler=message_audit,
    name="core.message_audit",
    weight=0,
    intercept=False,
)
```

### 触发事件并处理结果

```python
continue_flag, modified_message = await event_bus.emit(
    event_type=EventType.ON_MESSAGE,
    message=event_message,
)

if not continue_flag:
    return

if modified_message and modified_message.plain_text:
    message.processed_plain_text = modified_message.plain_text
```

## 与旧 events\_manager 的关系

当前 EventBus 是面向最终架构的事件系统。它不依赖插件基类，内部 handler 直接注册 async callable，IPC 插件通过 `plugin_runtime` 桥接。

**不再要求继承插件基类** ：内部 handler 只需符合签名。
**不再把事件逻辑绑定到单一管理器** ：EventBus 是全局单例，模块可以按需注入或导入。
**保留事件类型兼容** ：标准 `EventType` 来自 `core/types.py`。
**保留消息模型兼容** ：事件消息统一使用 `MaiMessages`。
**保留插件扩展能力** ：通过 `bridge_event()` 进入插件运行时。

## 审计要点

**权重冲突** ：多个 handler 使用相同 `weight` 时，执行顺序取决于注册顺序和列表排序稳定性。
**异步副作用不可见** ：非拦截型 handler 不会阻塞 `emit()`，调用方不能假设它已完成。
**消息字段一致性** ：修改 `message_segments` 后，应同步维护 `plain_text`，否则可能产生不一致。
**IPC 回写限制** ：只有 `MaiMessages` 中可序列化的字段能安全跨 IPC 回写。
**生命周期事件无消息体** ：`ON_START` 和 `ON_STOP` 不携带 `MaiMessages`，handler 需要处理 `None`。
**TODO 事件点** ：`ON_MESSAGE_PRE_PROCESS` 和 `ON_MESSAGE` 在 chat 入口中存在集成点注释，启用前需要确认业务主链已经迁移完成。

## 结论

EventBus 是 MaiBot 内部事件通信的基础设施。它用发布/订阅模型连接核心类型系统、聊天入口和插件运行时，用拦截型 handler 支持主流程控制，用非拦截型 handler 支持异步旁路，用 IPC 桥接把事件扩展到插件 Supervisor。

它的边界也很清楚：EventBus 提供底层事件分发，不提供完整 Hook 规格系统。需要插件显式声明、参数校验、blocking/observe 策略和复杂错误策略时，应继续使用 `plugin_runtime` 中的 Hook 调度器。需要统一事件名、消息快照、顺序拦截和异步通知时，EventBus 是更合适的入口。

---

---
url: /manual/adapters/napcat.md
---

# 使用NapCat和适配器连接麦麦

你可以通过 **NapCat** 来获取QQ的消息和信息

然后通过 **适配器**将这些消息翻译并发送给MaiBot

## 适配器仓库

NapCat 适配器的源码：[Mai-with-u/MaiBot-Napcat-Adapter](https://github.com/Mai-with-u/MaiBot-Napcat-Adapter)

## 安装适配器

你可以在WebUI的插件商店直接找到NapCat Adapter适配器，直接安装即可

⚠️安装后需要手动进行**启用**，你可以在webui的插件管理看到哪些插件被启用了

```bash
# 克隆插件
git clone -b main https://github.com/Mai-with-u/MaiBot-Napcat-Adapter.git

```

**将适配器目录放入 MaiBot 的 `plugins/` 文件夹中**

## 配置 NapCat

1. 打开 NapCat 的网页界面
2. 找到 "正向 WebSocket" 或 "WebSocket 服务器" 设置
3. 启用正向 WebSocket 服务器，监听端口需要和 NapCat Adapter插件中的 `端口` 一致 （`plugins/MaiBot-Napcat-Adapter/config.toml` 中 `napcat_server.port` ）
4. 如果你设置的WebSocket连接有访问Token，将这个Token复制并填写到**Adapter插件配置**的**访问令牌**配置项中。（注意不是napcat webui的token也不是maibot webui的token！！！）

具体配置方法请参考 [NapCat 官方文档](https://napneko.github.io/guide/boot/Shell)。

正向 WebSocket 服务器默认端口通常为 `3001`。适配器会作为客户端连接到 NapCat，例如 `ws://127.0.0.1:3001`，具体地址和端口以适配器配置为准。

## 启动

直接启动 MaiBot 就行，适配器会自动加载并连接。

#### 群聊白名单

NapCat 适配器默认启用聊天名单过滤，群聊默认是白名单模式。没有写进 `群聊名单` 的群消息会被直接丢弃；如果你发现 NapCat 已经连接成功，但群里 @ 机器人没有反应，优先插件的 `聊天过滤` 配置。

`plugins/MaiBot-Napcat-Adapter/config.toml`

```toml
[chat]
enable_chat_list_filter = true
show_dropped_chat_list_messages = true
group_list_type = "whitelist"
group_list = ["你的QQ群号"]
```

测试阶段也可以临时关闭名单过滤：

```toml
[chat]
enable_chat_list_filter = false
```

## 独立模式使用指南 🔧

::: warning 旧版方法
独立版适配器是早期的接入方式，通常只建议在已有独立部署、兼容旧环境或有特殊网络需求时继续使用。新部署建议优先使用上方的插件版适配器，配置更少，也更便于维护。
:::

如果你需要独立运行适配器，按以下步骤操作。

使用 `main` 分支：

```bash
# 克隆 main 分支（默认）
git clone https://github.com/Mai-with-u/MaiBot-Napcat-Adapter.git

# 或者如果已克隆，确保在 main 分支
cd MaiBot-Napcat-Adapter
git checkout main
```

### 配置 MaiBot

在 `config/bot_config.toml` 里添加：

```toml
[bot]
platform = "qq"           # 用 QQ 平台
qq_account = 123456789    # 你的机器人 QQ 号
nickname = "麦麦"          # 机器人昵称
```

还是在 `config/bot_config.toml` 里，设置连接参数：

```toml
[maim_message]
ws_server_host = "127.0.0.1"   # 服务器地址（本地就用这个）
ws_server_port = 8000           # 端口号（默认 8000）
auth_token = []                 # 认证令牌，空着就行
```

* **`ws_server_host`** — 服务器地址，本地用 `127.0.0.1`，服务器用实际 IP
* **`ws_server_port`** — 端口号，默认 `8000`，改了就记住这个数字
* **`auth_token`** — 密码验证，空着就行，不用管

> 💡 **注意**：`maim_message` 配置的是 legacy WebSocket 服务（端口 8000）。适配器通过 MMC 协议连接 MaiBot，默认连接 MaiBot 的 `config/bot_config.toml` 中 `[maim_message]` 设置的 `ws_server_port`（默认 8000）。确保适配器的 `config.toml` 中 `maibot_server.port` 与 MaiBot 的 `ws_server_port` 设置一致。

### 安装 NapCat

请参考 [NapCat 官方文档](https://napneko.github.io/guide/boot/Shell) 安装 NapCat。

**Docker 用户**：如果你使用项目自带的 `docker-compose.yml`，NapCat 已经作为 `napcat` 服务包含在内，直接和 MaiBot 一起启动即可：

```bash
docker compose up -d
```

### 设置 NapCat 连接

1. 打开 NapCat 的网页界面
2. 找到 "反向 WebSocket" 设置
3. 填上 MaiBot 地址：`ws://127.0.0.1:8000/ws`

具体配置方法请参考 [NapCat 官方文档](https://napneko.github.io/guide/boot/Shell)。

💡 **提示**：如果 NapCat 和 MaiBot 都在 Docker Compose 里运行，请确认 MaiBot 的 `maim_message.ws_server_host` 监听地址允许容器网络访问。

### 登录 QQ

启动 NapCat 后需要登录 QQ。具体登录方法请参考 [NapCat 官方文档](https://napneko.github.io/guide/boot/Shell)。

### 连接步骤

推荐启动顺序：

1. **启动 NapCat** → 等 QQ 登录成功
2. **启动 MaiBot** → 等 WebSocket 服务启动
3. **启动适配器** → 适配器连接到 NapCat 和 MaiBot
4. **自动连接** → NapCat 会自动连上适配器

```bash
# Docker 一键启动（推荐）
docker compose up -d

# 手动启动
# 终端 1：启动 NapCat
# 终端 2：启动适配器 (进入适配器目录运行)
# 终端 3：uv run python bot.py
```

## 一些问题 ✅

怎么知道连上了？看这几个地方：

**插件模式**：

1. **WebUI 插件列表**：能看到 NapCat 适配器插件已加载
2. **MaiBot 日志**：看到适配器插件已加载的提示
3. **发消息测试**：在 QQ 群里 @机器人，看有没有回复

**独立模式**：

1. **MaiBot 日志**：看到 "WebSocket 服务启动成功"
2. **NapCat 日志**：看到 "反向 WebSocket 连接成功"
3. **适配器日志**：看到连接成功
4. **发消息测试**：在 QQ 群里 @机器人，看有没有回复

### 连不上怎么办？

**检查这几点**：

* 是否启用了插件，插件是默认关闭的哦
* 地址和端口填对了吗？是否正确填写WS连接的token
* NapCat 和 MaiBot 在同一台机器吗？
* 日志里有什么报错信息？

### 收不到消息？

**可能原因**：

* 适配器是否正确设置了群聊白名单？哪些群聊允许聊天？
* QQ 号填错了？要和 NapCat 登录的一致
* NapCat 本身收到消息了吗？看 NapCat 日志
* 网络连接正常吗？

---

---
url: /develop/architecture/global-managers.md
---

# 全局管理器

本文基于 code-map 快照编写

## 概述

全局管理器模块（`src.manager`）负责提供应用级的单例服务，用于协调系统底层的通用基础能力。该模块设计轻量，不包含业务逻辑，仅作为纯粹的工具型服务，确保在整个应用生命周期内，基础任务调度和持久化存储拥有统一的入口和状态管理。

该模块不依赖其他 MaiBot 内部模块，仅使用 Python 标准库中的 `asyncio`、`json`、`os` 等基础包。两个核心管理器（AsyncTaskManager 和 LocalStorageManager）互不依赖，各自独立运行。这种设计确保了管理器模块可以作为系统的基础设施层，被 MainSystem、各适配器以及插件按需引用，而不会引入循环依赖。

## 架构图

```mermaid
graph TD
    subgraph "Manager Module"
        ATM[AsyncTaskManager]
        LSM[LocalStorageManager]
    end

    subgraph "MainSystem Initialization"
        MS[MainSystem]
    end

    subgraph "Registered Tasks"
        OTR[OnlineTimeRecordTask]
        SOT[StatisticOutputTask]
        THB[TelemetryHeartBeatTask]
        TSU[TelemetryStatsUploadTask]
    end

    subgraph "Storage Layer"
        JSON[(local_store.json)]
    end

    MS -->|register/start| ATM
    ATM -->|schedule| OTR
    ATM -->|schedule| SOT
    ATM -->|schedule| THB
    ATM -->|schedule| TSU
    
    LSM -->|atomic write/read| JSON
    MS -.->|use| LSM
```

## 核心概念

### AsyncTaskManager

异步任务管理器负责管理后台异步任务的生命周期。它允许系统在不阻塞主逻辑的前提下，运行定时心跳、数据统计等循环任务。

AsyncTaskManager
职责：管理任务的注册、启动、取消和优雅停止。
关键组件：
AsyncTask：任务基类。定义了 `wait_before_start`（启动延迟）和 `run_interval`（运行间隔），支持一次性任务或循环任务。
abort\_flag：全局中止标志。当系统关闭时，通过设置该标志通知所有循环任务停止运行。
\_lock：异步锁。确保在添加或停止任务时的线程安全，防止并发修改任务列表。
单例实例：`async_task_manager`

任务调度机制
AsyncTaskManager 的核心是一个基于 `asyncio` 的任务调度引擎，其工作流程分为四个阶段：

```
注册阶段
    调用 `add_task()` 将 AsyncTask 实例加入内部任务列表。该方法持有 `_lock` 异步锁，防止并发场景下的竞态条件。注册时任务处于"已注册"状态，尚未创建 `asyncio.Task`，不会占用事件循环资源。

调度阶段
    调用 `start_task()` 为注册的任务创建 `asyncio.Task`。该方法内部通过 `asyncio.create_task()` 将 `AsyncTask.run()` 包装为协程任务。每个 AsyncTask 实例对应一个 `asyncio.Task` 对象，引用保存在 `_task` 属性中，用于后续的取消与等待操作。调度后的任务进入"运行中"状态。

执行循环
    调度启动后，任务进入事件循环驱动的执行循环：
    - 若 `wait_before_start > 0`，先执行 `asyncio.sleep(wait_before_start)` 实现延迟启动。
    - 主循环条件为 `while not self.abort_flag`，持续检测全局中止标志。
    - 每轮循环中调用 `run()` 执行业务逻辑，`run()` 内的异常会被 `try/except` 捕获并记录，防止单个任务崩溃影响整个管理器。
    - `run()` 返回后，若 `run_interval > 0`，通过 `asyncio.sleep(run_interval)` 休眠指定间隔，实现周期执行；否则任务仅执行一次后退出。

停止与清理阶段
    调用 `stop_and_wait_all_tasks()` 时，管理器设置 `abort_flag = True`。所有运行中的任务在下一次循环条件检查时感知到该标志并主动退出。管理器通过 `asyncio.wait_for()` 等待每个任务退出，超时时间为 10 秒。超时未退出的任务会被强制取消。每个 `asyncio.Task` 注册了 `add_done_callback`，任务结束后自动从内部列表中移除已终止的引用，防止内存泄漏。
```

### LocalStorageManager

本地存储管理器提供一个简单的键值对接口，用于将轻量级配置或状态持久化到本地 JSON 文件中。

LocalStorageManager
职责：实现本地数据的原子化读写与损坏自动恢复。
实现机制：
字典接口：通过实现 `__getitem__`、`__setitem__` 等魔术方法，使其像 Python 字典一样操作。
原子写入：写入时先创建临时文件（`.tmp`），写入完成后使用 `os.replace` 原子替换目标文件，防止写入崩溃导致数据丢失。
损坏恢复：在加载文件时，若检测到 JSON 损坏，会自动将原文件备份为 `.corrupt` 后缀，并重建一个空的存储文件，确保系统能正常启动。
单例实例：`local_storage`

初始化流程
LocalStorageManager 在 `MainSystem.initialize()` 阶段被初始化。初始化时首先确定存储文件路径（默认与主配置文件同目录下的 `local_store.json`）。随后尝试加载已存在的文件内容至内存字典，若文件不存在则以空字典启动。加载过程中若发现 JSON 解析错误，自动执行损坏恢复流程。

使用场景
该管理器适合存储以下类型的数据：
\- 用户配置偏好（如语言设置、主题选择）。
\- 运行时状态标记（如首次运行标记、功能开关）。
\- 轻量计数器与缓存值。
对于需要复杂查询或事务支持的数据，应直接使用数据库代替。

## 关键流程

### 定时任务执行流程

AsyncTaskManager 对定时任务的管理遵循从注册到清理的完整生命周期：

1. 任务定义
   开发者继承 `AsyncTask` 基类并实现 `run()` 方法。`run()` 是任务的核心逻辑，应设计为可重入的幂等操作，因为同一任务可能在多次调度中重复执行。基类构造函数接收 `wait_before_start` 和 `run_interval` 两个参数，分别控制首次执行延迟和执行间隔。

2. 任务注册
   调用 `async_task_manager.add_task(task)` 将任务实例加入内部列表。注册时持有 `_lock` 异步锁，确保在并发场景下不会出现竞态条件。注册完成后任务处于"已注册"状态，尚未创建对应的 `asyncio.Task`，不占用事件循环资源。

3. 调度启动
   管理器遍历已注册任务列表，对每个任务调用 `start_task()`，内部通过 `asyncio.create_task()` 创建协程任务。每个 AsyncTask 实例对应一个 `asyncio.Task`，其引用保存在 `_task` 属性中，用于后续的取消与等待操作。调度成功后任务进入"运行中"状态。

4. 执行循环
   * 若 `wait_before_start > 0`，先执行 `asyncio.sleep(wait_before_start)`，实现延迟启动，避免系统启动阶段的任务竞争。
   * 进入 `while not self.abort_flag` 循环，只要 `abort_flag` 未被设置，就持续执行 `run()`。
   * 每次 `run()` 返回后，若 `run_interval > 0`，通过 `asyncio.sleep(run_interval)` 休眠指定间隔，实现固定周期的循环执行。
   * 若 `run_interval <= 0`，任务在完成一次 `run()` 后自动退出，适用于一次性任务。
   * `run()` 内部的异常会被 `try/except` 捕获并记录日志，防止单个异常导致任务永久终止。

5. 任务清理
   通过 `add_done_callback` 注册完成回调。当 `asyncio.Task` 完成时（无论是正常结束、异常退出还是被取消），回调函数自动将该任务从内部列表中移除。这确保了管理器不会持有已终止任务的引用，避免内存泄漏。

批量停止机制
`stop_and_wait_all_tasks()` 提供了统一的批量停止能力：
\- 设置 `abort_flag = True`，通知所有运行中的任务主动退出。
\- 并发等待所有任务完成，超时上限为 10 秒。
\- 超时未退出的任务通过 `task.cancel()` 强制取消。
\- 所有任务停止后清空内部任务列表，释放引用。

### 本地存储读写流程

写入数据：
\- 用户调用 `local_storage[key] = value`。
\- 更新内存中的 `store` 字典。
\- 调用 `save_local_store()` 触发原子写入。
\- 创建临时文件 $\rightarrow$ JSON 序列化 $\rightarrow$ 原子替换 $\rightarrow$ 删除临时文件。
\- 若写入过程发生异常（如磁盘空间不足、权限错误），临时文件会自动清理，原始文件不受影响。

```
原子写入的优势在于：即使写入过程中进程崩溃，也不会破坏原有数据文件。临时文件写完后通过 `os.replace` 进行文件系统级别的重命名操作，确保目标文件的更新是瞬时的。
```

读取数据：
\- 用户调用 `local_storage[key]`。
\- 直接从内存字典 `store` 中获取值（启动时已一次性加载至内存）。

```
读取操作仅涉及内存访问，不会触发文件 I/O，因此具有极高的性能。所有文件读取仅在初始化时执行一次，后续所有读操作都在内存中进行。
```

持久化触发策略
`save_local_store()` 在每次写操作后立即调用，实现同步持久化。这种设计在每次赋值时都涉及磁盘 I/O，但换取了数据安全性，确保任何写操作的结果都能被即时持久化，避免系统崩溃导致的内存数据丢失。

## 与 MainSystem 的交互

全局管理器在 `MainSystem` 的生命周期中扮演关键的支撑角色，两者通过直接方法调用进行协作，遵循注册 → 调度 → 执行 → 清理的完整任务生命周期。

初始化阶段
在 `MainSystem.initialize()` 执行过程中，系统通过 `AsyncTaskManager.add_task()` 注册一系列核心后台任务。注册完成后，管理器依次调用 `start_task()` 为每个任务创建 `asyncio.Task` 并启动执行循环。注册的核心任务包括：
\- OnlineTimeRecordTask：记录机器人在线时长，周期性更新启动时间戳。
\- StatisticOutputTask：定期输出运行统计数据，包括消息吞吐量、活跃会话数等。
\- TelemetryHeartBeatTask：发送遥测心跳包，用于监控系统健康状态。
\- TelemetryStatsUploadTask：上传统计指标至遥测服务，用于数据分析与性能监控。

```
这些任务的 `wait_before_start` 和 `run_interval` 参数在实例化时指定，确保了系统完全启动后再开始执行各定时任务，避免启动阶段的任务竞争。
```

运行阶段
任务启动后各自独立运行，通过 `abort_flag` 机制感知系统状态。各任务之间互不干扰，单个任务的异常不会影响管理器或其他任务的正常运行。AsyncTaskManager 在此阶段仅作为任务列表的维护者，不介入具体业务逻辑的执行。

关闭阶段
在 `main()` 函数的 `finally` 块中，系统调用 `async_task_manager.stop_and_wait_all_tasks()`。该方法的执行流程如下：
1\. 设置 `abort_flag = True`：通知所有运行中的任务在下一次循环条件检查时退出。
2\. 广播取消信号：遍历所有活跃的 `asyncio.Task`，依次调用 `cancel()`。
3\. 等待优雅退出：通过 `asyncio.wait_for()` 等待每个任务退出，超时时间为 10 秒。
4\. 强制终止：对于超时未退出的任务，由 `asyncio` 事件循环强制取消。
5\. 资源清理：清空内部任务列表，确保所有 async\_task\_manager 占用的引用被释放。

```
整个关闭过程确保没有任何挂起的异步操作导致进程僵死，实现可预期的干净退出。
```

## Hook/扩展点

全局管理器模块作为基础设施层，在设计哲学上遵循最小化和非侵入原则，因此**不对外暴露 Hook 接口**。MainSystem 与 Manager 之间的交互全部通过直接方法调用完成，没有经过事件总线或 Hook 机制。

与其他模块的协作方式如下：

插件自定义定时任务
在 `MainSystem` 启动流程中，`event_bus.emit(EventType.ON_START)` 发出后，插件可以在其 `on_start` 回调中获取 `async_task_manager` 的单例实例，并通过 `add_task()` 注册自定义定时任务。这为插件提供了定时执行自身逻辑的能力，例如定期清理缓存、定时发送消息等。

本地存储的使用
插件或系统模块可以通过 `local_storage` 单例直接读写持久化数据。`LocalStorageManager` 提供的是同步文件 I/O 接口，适合存储配置项、状态标记等轻量级数据。对于需要结构化查询的场景，应直接使用数据库而非本地存储。

设计考量
管理器模块刻意保持最小化接口的原因是：
\- 避免在基础设施层引入复杂度，保持职责边界清晰。
\- 定时任务的管理已由 AsyncTaskManager 完整覆盖，无需额外的 Hook 抽象。
\- 本地存储仅提供最基础的键值对操作，不承担数据模型的职责。

```
这种设计使得管理器模块可以独立于业务逻辑变化而稳定存在，同时为上层模块提供了足够的扩展能力。
```

---

---
url: /features.md
---

# 功能介绍

MaiBot（麦麦）不仅仅是一个聊天机器人——她是一个致力于以真实人类风格进行交互的数字生命。以下是她拥有的核心能力。

### 💬 智能对话管线

从消息接收到最终回复的完整处理管线，支持 Hook 拦截、命令分发、过滤检查和灵活路由。

[了解消息管线 →](../manual/features/message-pipeline.md)

### 🧠 Maisaka 推理引擎

基于工具调用的多轮内部推理系统。Planner 决策、Timing Gate 节奏控制、自动打断与重试，让对话节奏自然流畅。

[了解 Maisaka →](../manual/features/maisaka-reasoning.md)

### ❤️ 长期记忆系统

A-Memorix 记忆引擎提供知识图谱、对话摘要和人物画像，自动写回机制让麦麦持续积累对你的了解。

[了解记忆系统 →](../manual/features/memory-system.md)

### 📖 表达与黑话学习

自动从对话中提取表达风格和群体黑话，通过 LLM 推断含义并逐步完善，让麦麦越来越像你身边的人。

[了解学习系统 →](../manual/features/learning.md)

### 😊 表情包系统

基于 VLM 的表情包自动识别、情绪标签生成和智能选择，让对话更生动。

[了解表情系统 →](../manual/features/emoji-system.md)

### 🔌 MCP 集成

支持 Model Context Protocol，连接外部工具服务器，无限扩展麦麦的能力边界。

[了解 MCP →](../manual/features/mcp.md)

---

---
url: /manual/webui/config-management.md
---

# 在浏览器里改配置

不用编辑文件，点点鼠标就能改 MaiBot 的设置！

## 两种修改方式

### 1. 表单模式（推荐）

像填问卷一样改配置，简单直观：

* 每个设置都有说明文字
* 下拉菜单、开关、输入框，操作方便
* 自动检查格式对不对

### 2. 高级模式

直接编辑配置文件，适合懂技术的用户：

* 可以看到完整的配置文件
* 自由修改任何内容
* 需要懂 TOML 格式

## 能改哪些设置？

### 🤖 机器人设置

* **基本资料** - 名字、头像、签名
* **聊天行为** - 回复速度、消息长度
* **人格特征** - 性格、说话风格

### 💬 消息设置

* **回复规则** - 什么时候回复、回复谁
* **表情使用** - 爱不爱用表情包
* **错别字** - 要不要故意打错字

### 🧠 智能设置

* **记忆系统** - 记多少、记多久
* **模型选择** - 用哪个 AI 模型
* **API 配置** - 模型服务商设置

## 修改步骤

### 表单模式

1. 打开 WebUI，点击左侧"配置管理"
2. 选择要修改的分类（如"机器人设置"）
3. 找到要改的项目，输入新值
4. 点击"保存"，配置会保存到文件（配置重载功能待实现，重启后生效）

### 高级模式

1. 点击"原始配置"标签
2. 直接编辑文本内容
3. 点击"保存"，系统会检查格式
4. 有错会提示，没错就生效

## 修改建议

### 新手推荐

* 先改**机器人名字**和**签名**，让机器人有个性
* 调**回复速度**，太快太慢都不好
* 试试**人格设置**，让机器人更有趣

### 进阶玩法

* 配置**多个 AI 模型**，不同任务用不同模型
* 设置**关键词回复**，让机器人更智能
* 调整**记忆参数**，记住更多聊天内容

## 注意事项

⚠️ **重要提醒**：

* 改错设置可能导致机器人异常
* 不确定的选项先查文档
* 建议先备份重要配置

📝 **小技巧**：

* 鼠标悬停在设置项上会有说明
* 改完记得点保存
* 有问题可以重置默认设置

## 常见问题

**Q: 改坏了怎么办？**
A: 可以重置默认设置，或者手动改回原来的值

**Q: 为什么保存失败？**
A: 可能是格式不对，看看错误提示

**Q: 修改后多久生效？**
A: 当前配置保存后需要重启机器人才能生效（配置热重载功能待实现）

---

---
url: /manual/webui/plugin-management.md
---

# 安装和管理插件

插件就像给 MaiBot 安装"App"，让它拥有更多功能！

## 什么是插件？

插件是 MaiBot 的扩展功能，比如：

* 🎮 **游戏插件** - 能陪用户玩游戏
* 🎨 **画图插件** - 能生成图片
* 🎵 **音乐插件** - 能播放音乐
* 🌤️ **天气插件** - 能查天气预报
* 📚 **学习插件** - 能教知识

## 安装插件

### 方法一：在线安装（推荐）

1. 打开 WebUI，点击"插件管理"
2. 点击"安装插件"按钮
3. 输入插件地址（GitHub 链接）
4. 点击"安装"，等待完成

**示例地址**：

```
https://github.com/作者/插件名
```

### 方法二：Git URL 安装

1. 获取插件的 Git 仓库地址（GitHub 等）
2. 在插件管理页面点击"安装插件"
3. 输入 Git 仓库 URL
4. 点击"安装"，等待完成

> 注：当前仅支持通过 Git 仓库 URL 安装插件，不支持本地文件上传

## 管理已安装插件

### 查看插件

插件页面会显示：

* 📋 **插件名称** 和简介
* 🔧 **版本号** 和作者
* ✅ **启用状态**（绿色=启用，灰色=禁用）
* 📖 **使用说明**（点击可看）

### 启用/禁用插件

* 开关打开 → 插件生效
* 开关关闭 → 插件停用
* 改完立即生效，不用重启

### 配置插件

有些插件可以自定义设置：

1. 点击插件的"设置"按钮
2. 修改配置选项
3. 保存后立即生效

**常见配置**：

* API 密钥（需要外部服务的插件）
* 触发关键词
* 功能开关

### 更新插件

插件有新版本时会显示更新提示：

1. 点击"更新"按钮
2. 等待下载和安装
3. 自动完成，数据不会丢失

### 卸载插件

不需要的插件可以卸载：

1. 点击"卸载"按钮
2. 确认卸载
3. 插件文件会被删除

⚠️ **注意**：卸载后插件的数据可能会丢失

## 插件推荐

### 新手必备

* **欢迎插件** - 新用户入群自动欢迎
* **帮助插件** - 提供命令帮助
* **签到插件** - 每日签到功能

### 娱乐向

* **抽卡插件** - 模拟各种抽卡
* **骰子插件** - 掷骰子游戏
* **猜谜插件** - 猜谜语、脑筋急转弯

### 实用向

* **翻译插件** - 多语言翻译
* **计算插件** - 数学计算
* **时间插件** - 时间日期查询

## 使用技巧

### 插件冲突

如果插件功能重复或冲突：

* 只启用需要的插件
* 联系插件作者更新

### 性能优化

插件太多可能影响性能：

* 不用的插件及时卸载
* 定期清理无用插件
* 关注插件资源占用

### 安全提醒

* 只安装可信来源的插件
* 查看插件权限要求
* 定期更新插件版本

## 常见问题

**Q: 插件安装失败怎么办？**
A: 检查网络连接，确认插件地址正确，查看错误提示

**Q: 插件不起作用？**
A: 确认插件已启用，检查配置是否正确，查看 MaiBot 日志

**Q: 哪里找插件？**
A: GitHub 上搜索"MaiBot 插件"，或者加入社区获取推荐

**Q: 能自己开发插件吗？**
A: 当然可以！有开发文档和示例代码，零基础也能学

## 获取帮助

* 插件页面有使用说明
* 查看插件的 README 文档
* 加入 MaiBot 交流群询问
* 在 GitHub 提交问题

---

---
url: /manual/deployment/installation.md
---

# 📦 MaiBot 安装指南

## 环境要求

* **Python 3.12 及以上版本**（推荐 3.12 / 3.13）
* **Git**

## 下载 MaiBot

从 [GitHub Release](https://github.com/Mai-with-u/MaiBot/releases/) 下载最新版本，或者直接克隆仓库：

::: code-group

```bash [稳定版（包含预发布版） (推荐)]
git clone https://github.com/Mai-with-u/MaiBot.git
cd MaiBot
```

```bash [开发版 (尝鲜)]
git clone -b dev https://github.com/Mai-with-u/MaiBot.git
cd MaiBot
```

:::

::: warning ⚠️ 注意
`dev` 分支有新功能但可能不稳定。第一次用建议选 `main` 分支。
:::

## 安装依赖

我们推荐你用 [uv](https://github.com/astral-sh/uv) 管理依赖。

### 安装 uv

::: code-group

```bash [Windows]
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash [macOS / Linux]
curl -LsSf https://astral.sh/uv/install.sh | sh
```

:::

### 安装项目依赖

::: code-group

```bash [推荐：uv]
uv sync
```

```bash [备用：pip（不推荐，可能缺少部分依赖）]
pip install -r requirements.txt
```

:::

## 启动

```bash
uv run python bot.py
```

## 用户协议确认

第一次启动会要求你同意用户协议，很简单：

**在终端输入"同意"就行！**

## 常见问题

### 启动后提示"模型列表不能为空"？

`model_config.toml` 中必须至少包含一个模型配置。如果自动升级失败，需要手动创建模型配置文件，包括：

* 至少一个 API 提供商（`[[api_providers]]`）
* 至少一个文本模型（`[[models]]`）
* 对应的任务分配（`[model_task_config.xxx]`）

视觉模型和嵌入模型是可选的——视觉模型仅在需要看图时配置，嵌入模型仅在启用记忆功能时配置。

参考 [模型配置文档](../configuration/model-config.md) 进行配置。

### uv 命令找不到？

安装 uv 后需要将其加入 PATH 环境变量：

```bash
# Linux/macOS
source $HOME/.local/bin/env

# 或者重新打开终端

# 验证安装
uv --version
```

### 非交互环境下如何同意用户协议？

在服务器或无头环境下，无法在终端中输入"同意"，可以使用环境变量跳过：

```bash
# 方法一：使用程序提示的 hash 值（每次可能不同，以实际提示为准）
export EULA_AGREE=<终端显示的hash值>
export PRIVACY_AGREE=<终端显示的hash值>

# 方法二：先运行一次看提示的 hash 值，记录后用环境变量启动
uv run python bot.py  # 会显示需要的环境变量
```

---

---
url: /develop/architecture/tool-system.md
---

# 工具系统架构

本文基于 code-map 快照编写。

MaiBot 的工具系统把插件工具、旧版 Action、MaiSaka 内置能力和外部 MCP 工具收敛到同一套抽象层。它不负责教插件作者如何写一个 `@Tool`，也不替代 [插件 Tool 用法](../plugin-dev/tools.md) 中的开发教程。本文聚焦内部实现，说明工具声明、工具调用、Provider 适配和 ToolRegistry 路由如何协同工作。

## 1. 概述

MaiBot 当前统一四类工具来源：

**插件 `@Tool`** ：插件运行时中的 Tool 组件。插件 SDK 使用 `@Tool` 声明工具，运行时把声明写入组件注册表，`PluginToolProvider` 再把这些工具暴露给统一工具层。

**旧 `@Action`** ：旧版插件中的 Action 组件。SDK 2.0 会把 `@Action` 自动转换为 Tool 声明，MaiBot 运行时仍保留兼容路径，使旧插件可以继续被 LLM 调用。

**MaiSaka 内置 Tool** ：推理引擎自带的系统级能力，例如 `send_emoji`、记忆查询、回复、等待、结束本轮等。这些工具由 `MaisakaBuiltinToolProvider` 提供。

**MCP Tool** ：通过 `MCPToolProvider` 桥接外部 MCP 服务器的远程工具。MCP 管理器负责连接、发现和调用，MaiBot 工具层只消费统一后的 `ToolSpec` 和 `ToolExecutionResult`。

统一后的目标是让推理引擎只面对一种工具模型：

**工具声明** ：告诉 LLM 有哪些工具、工具做什么、参数是什么。

**工具调用** ：把 LLM 的选择转成可执行请求，包含工具名、参数、会话和流信息。

**工具执行** ：由对应 Provider 执行，返回统一结果，再写回对话历史或触发后续动作。

## 2. 架构图

```mermaid
flowchart TD
    A[插件 @Tool] -->|组件注册表| P1[PluginToolProvider]
    B[旧 @Action] -->|SDK 自动转换| P1
    C[MaiSaka 内置 Tool<br/>send_emoji, manage_memory 等] --> P2[MaisakaBuiltinToolProvider]
    D[外部 MCP Server] -->|MCPManager| P3[MCPToolProvider]

    subgraph ToolProvider 接口
        P1
        P2
        P3
    end

    P1 --> R[ToolRegistry]
    P2 --> R
    P3 --> R
    R -->|list_tools / get_llm_definitions| E[MaiSaka 推理引擎]
    E -->|ToolInvocation| R
    R -->|选择 Provider| P1
    R -->|选择 Provider| P2
    R -->|选择 Provider| P3
    P1 -->|ToolExecutionResult| E
    P2 -->|ToolExecutionResult| E
    P3 -->|ToolExecutionResult| E
```

这张图说明了两层边界。上层是工具来源，来源可以来自插件、旧 Action、内置模块或 MCP 服务器。下层是统一协议，所有来源都要变成 `ToolProvider`，再由 `ToolRegistry` 统一暴露给 MaiSaka 推理引擎。

概念层可以把 Provider 接口理解为 `get_tools()` 和 `execute_tool()`。源码中的实际方法名是 `list_tools()` 和 `invoke()`，二者职责一致：前者返回工具声明，后者执行工具调用。

## 3. 核心概念

### 3.1 ToolCall

**定义** ：LLM 在推理过程中产生的工具调用意图。

**内部模型** ：MaiBot 内部执行时使用 `ToolInvocation`，而不是直接复用模型 API 的原始 `ToolCall`。

**关键字段** ：

**`tool_name`** ：要执行的工具名。

**`arguments`** ：LLM 生成的参数对象。

**`call_id`** ：模型工具调用 ID，用于把结果放回正确位置。

**`session_id`** ：会话 ID。

**`stream_id`** ：聊天流 ID。

**`reasoning`** ：模型选择该工具时的推理文本。

**`metadata`** ：扩展信息，例如 anchor message、来源标记或调试字段。

`ToolCall` 是推理结果，`ToolInvocation` 是执行请求。MaiBot 在二者之间做标准化，避免每个 Provider 都理解不同模型的原始格式。

### 3.2 ToolIcon

**定义** ：统一工具图标定义。

**源码模型** ：`ToolIcon`。

**关键字段** ：

**`src`** ：图标资源地址。

**`mime_type`** ：资源 MIME 类型。

**`sizes`** ：图标尺寸列表。

图标不是 LLM 选择工具的必要信息。它主要服务于需要展示工具列表的 UI、监控面板或调试界面。工具声明中 `icons` 可以为空，不影响推理和调用。

### 3.3 ToolAnnotation

**定义** ：统一工具注解信息。

**源码模型** ：`ToolAnnotation`。

**关键字段** ：

**`audience`** ：工具面向的使用者或模型集合。

**`priority`** ：工具优先级。

**`metadata`** ：注解扩展字段。

注解用于表达工具的非功能信息。它不直接决定工具是否可调用，但可以为未来的调度、过滤、展示或权限判断提供结构化元数据。

### 3.4 ToolSpec

**定义** ：统一工具声明。

**源码模型** ：`ToolSpec`。

**关键字段** ：

**`name`** ：工具名，必须在统一工具视图中唯一。

**`description`** ：给 LLM 使用的工具描述。

**`title`** ：可选展示标题。

**`parameters_schema`** ：参数 JSON Schema。

**`output_schema`** ：输出 Schema，供支持结构化输出的模型使用。

**`provider_name`** ：声明来自哪个 Provider。

**`provider_type`** ：Provider 类型，例如 `plugin`、`builtin`、`mcp`。

**`enabled`** ：是否启用。

**`icons`** ：图标列表。

**`annotation`** ：工具注解。

**`metadata`** ：扩展元数据。

`ToolSpec` 是工具系统的核心数据对象。所有来源都必须先变成 `ToolSpec`，才能进入 LLM 工具定义列表和调用路由。

### 3.5 ToolProvider

**定义** ：统一工具提供者接口。

**源码模型** ：`ToolProvider` Protocol。

**概念方法** ：

**`get_tools()`** ：列出当前 Provider 可暴露的工具声明。源码对应 `list_tools(context)`。

**`execute_tool()`** ：执行指定工具调用。源码对应 `invoke(invocation, context)`。

**资源释放** ：源码还要求 `close()`，用于释放 Provider 持有的外部连接或异步资源。

Provider 不关心其他来源如何注册，也不直接参与 LLM 选择。它只负责把自己的工具翻译成统一声明，并在被注册表选中时执行请求。

### 3.6 ToolRegistry

**定义** ：统一工具注册表。

**源码模型** ：`ToolRegistry`。

**职责** ：

**注册 Provider** ：`register_provider()` 保存 Provider。同名 Provider 后注册会替换先注册者。

**注销 Provider** ：`unregister_provider()` 按 Provider 名称移除。

**列出工具** ：`list_tools()` 按 Provider 顺序收集工具，并跳过重复名称。

**查询工具** ：`get_tool_spec()` 和 `has_tool()` 用于判断某个工具是否存在。

**生成 LLM 定义** ：`get_llm_definitions()` 把 `ToolSpec` 转为模型层可消费的 `ToolDefinitionInput`。

**执行调用** ：`invoke()` 根据工具名找到负责 Provider，并返回统一结果。

**关闭资源** ：`close()` 关闭所有 Provider。

`ToolRegistry` 是工具系统的调度中心。它让 MaiSaka 推理引擎不需要知道工具来自插件、内置模块还是 MCP。

### 3.7 ToolExecutionContext

**定义** ：工具执行上下文。

**关键字段** ：

**`session_id`** ：会话 ID。

**`stream_id`** ：聊天流 ID。

**`reasoning`** ：模型选择工具的推理文本。

**`is_group_chat`** ：是否为群聊。

**`group_id`** ：群 ID。

**`user_id`** ：用户 ID。

**`platform`** ：平台名称。

**`metadata`** ：扩展上下文。

执行上下文把模型调用时的会话状态传给 Provider。插件工具尤其依赖这些字段，例如通过 `stream_id` 找到可发送消息的聊天流。

### 3.8 ToolAvailabilityContext

**定义** ：工具暴露可用性判断上下文。

**关键字段** ：

**`session_id`** ：会话 ID。

**`stream_id`** ：聊天流 ID。

**`is_group_chat`** ：是否为群聊。

**`group_id`** ：群 ID。

**`user_id`** ：用户 ID。

**`platform`** ：平台名称。

可用性上下文用于决定某个工具在当前聊天中是否应该暴露给 LLM。内置工具会根据群聊、私聊和配置过滤；插件工具也可以基于运行时状态做可见性判断。

### 3.9 ToolExecutionResult

**定义** ：统一工具执行结果。

**关键字段** ：

**`tool_name`** ：被执行的工具名。

**`success`** ：是否成功。

**`content`** ：文本结果。

**`error_message`** ：错误信息。

**`structured_content`** ：结构化结果，通常是 dict 或 list。

**`content_items`** ：可包含图片、音频、资源链接等多媒体结果项。

**`post_history_messages`** ：执行后需要追加到历史的消息。

**`metadata`** ：扩展元数据。

`ToolExecutionResult.get_history_content()` 会把结果转成适合写入历史消息的文本。若存在 `content_items`，会优先拼合可读摘要，避免直接把媒体二进制塞进 LLM 上下文。

## 4. 四类工具来源详解

### 4.1 插件 `@Tool`

**源码入口** ：`maibot/src/plugin_runtime/tool_provider.py`。

**Provider** ：`PluginToolProvider`。

**provider\_name** ：`plugin_runtime`。

**provider\_type** ：`plugin`。

插件 `@Tool` 由 SDK 注册为插件组件。插件运行时启动后，Host 侧 `ComponentRegistry` 保存 Tool 条目，`ComponentQueryService` 提供只读查询视图。`PluginToolProvider` 不直接持有插件对象，而是通过 `component_query_service` 读取当前可用的工具声明。

声明阶段：

**插件加载** ：Runner 子进程加载插件，并注册 Tool 组件。

**组件注册表** ：Host 侧 `ComponentRegistry` 记录工具名、插件 ID、调用方法、参数 Schema、可见性和启用状态。

**查询视图** ：`ComponentQueryService` 把注册表条目转换为 `ToolSpec`。

**Provider 暴露** ：`PluginToolProvider.list_tools()` 返回统一工具列表。

执行阶段：

**工具名匹配** ：`PluginToolProvider.invoke()` 根据 `ToolInvocation.tool_name` 找到 Tool 条目。

**IPC 调用** ：Host 通过插件运行时 RPC 调用 Runner 子进程中的插件方法。

**结果归一化** ：插件返回值被转换为 `ToolExecutionResult`。

**历史兼容** ：旧 `@Action` 转换后的工具也走同一执行路径。

### 4.2 旧 `@Action`

**源码入口** ：插件 SDK 转换层和 `plugin_runtime/tool_provider.py`。

**Provider** ：仍由 `PluginToolProvider` 暴露。

**兼容方式** ：SDK 内部把 `@Action` 转换为 `@Tool` 声明。

旧 Action 的兼容重点不是让 LLM 知道它曾经是 Action，而是让它以 Tool 语义进入统一系统。转换后，旧 Action 会获得工具名、描述、参数 Schema 和调用入口。运行时保留必要的元数据，用于区分它来自 legacy component。

兼容边界：

**不鼓励新插件使用** ：新插件应直接使用 `@Tool`。

**保留执行路径** ：MaiBot 运行时仍能调用由旧 Action 转换来的工具。

**不重复 API 教程** ：Action 到 Tool 的转换细节属于插件开发文档边界，本文只说明架构位置。

**统一结果模型** ：执行完成后仍返回 `ToolExecutionResult`，MaiSaka 不关心它来自旧 Action 还是新 Tool。

### 4.3 MaiSaka 内置 Tool

**源码入口** ：`maibot/src/maisaka/builtin_tool/`。

**Provider** ：`MaisakaBuiltinToolProvider`。

**provider\_name** ：`maisaka_builtin`。

**provider\_type** ：`builtin`。

内置工具是 MaiSaka 推理引擎的一部分，用于完成模型自身不能直接完成的核心动作。例如 `send_emoji` 发送表情包，记忆查询类工具读取长期记忆或人物画像，`reply` 发送回复，`finish` 结束本轮思考。

内置工具特点：

**强绑定推理流程** ：内置工具服务于 Planner、Timing Gate 和 Action Loop。

**声明集中管理** ：`BUILTIN_TOOL_ENTRIES` 集中声明工具名、spec 构造器和 handler。

**阶段控制** ：工具可标记为 `timing`、`action` 或 `both`。

**可见性控制** ：工具可标记为 `visible`、`deferred` 或 `hidden`。

**配置过滤** ：部分工具根据全局配置启用或禁用。

**聊天范围过滤** ：部分工具只在群聊或私聊中暴露。

`MaisakaBuiltinToolProvider` 的 `list_tools()` 会调用内置工具聚合函数，按当前可用性上下文过滤工具。`invoke()` 则通过工具名找到对应 handler 并执行。

### 4.4 MCP Tool

**源码入口** ：`maibot/src/mcp_module/provider.py`。

**Provider** ：`MCPToolProvider`。

**provider\_name** ：`mcp`。

**provider\_type** ：`mcp`。

MCP 工具来自外部 MCP 服务器。MaiBot 通过 `MCPManager` 连接服务器、发现工具、调用工具并关闭连接。`MCPToolProvider` 是这个能力的适配器。

MCP 工具特点：

**外部能力** ：工具实现位于 MaiBot 进程外。

**运行时连接** ：MaiBot 启动时根据 MCP 配置初始化管理器。

**工具发现** ：`MCPManager.get_tool_specs()` 返回统一 `ToolSpec` 列表。

**工具调用** ：`MCPManager.call_tool_invocation()` 执行远程调用。

**资源释放** ：`MCPToolProvider.close()` 会关闭 MCP 连接。

MCP 工具扩展了 MaiBot 的能力边界，但调用链仍保持统一。MaiSaka 只看到 `ToolSpec`，执行时只提交 `ToolInvocation`，最后只接收 `ToolExecutionResult`。

## 5. 关键流程

### 5.1 工具注册

```mermaid
sequenceDiagram
    participant B as 内置工具目录
    participant P as PluginRuntime
    participant M as MCPManager
    participant R as ToolRegistry

    B->>R: register_provider(MaisakaBuiltinToolProvider)
    P->>R: register_provider(PluginToolProvider)
    M->>R: register_provider(MCPToolProvider)
```

注册发生在 MaiSaka 运行时初始化阶段。内置 Provider 和插件 Provider 是默认注册的。MCP Provider 只有在 MCP 启用且成功发现工具时才会注册。

注册规则：

**同名替换** ：`ToolRegistry.register_provider()` 会先移除同名 Provider，再加入新 Provider。

**顺序保留** ：列出工具时按注册顺序遍历 Provider。

**去重保护** ：如果多个 Provider 暴露同名工具，先注册的保留，后出现的跳过并记录警告。

**启用过滤** ：`ToolSpec.enabled` 为 false 的工具不会进入统一列表。

### 5.2 工具发现

```mermaid
flowchart LR
    A[ToolRegistry.list_tools] --> B[遍历 Provider]
    B --> C[Provider.list_tools]
    C --> D[ToolSpec 列表]
    D --> E{enabled?}
    E -->|否| F[跳过]
    E -->|是| G{工具名已存在?}
    G -->|是| H[保留先注册者]
    G -->|否| I[加入统一工具列表]
```

工具发现不是一次性静态快照。每次 MaiSaka 需要给模型准备工具定义时，都会通过 `ToolRegistry.list_tools()` 收集当前可用工具。

发现阶段会处理三类差异：

**来源差异** ：插件、内置、MCP 的声明来源不同，但最终都是 `ToolSpec`。

**上下文差异** ：不同聊天流、群聊或私聊可能暴露不同工具。

**可见性差异** ：隐藏工具不会进入 LLM 工具列表，延迟发现工具也可能暂时不暴露。

### 5.3 推理引擎选择

MaiSaka 通过 `ChatLoopService` 设置统一 `ToolRegistry`。当 Planner 需要工具定义时，`ToolRegistry.get_llm_definitions()` 会把 `ToolSpec` 转为模型层工具定义。

选择过程：

**模型看到工具列表** ：LLM 根据 prompt、上下文和工具描述决定是否调用工具。

**模型返回 ToolCall** ：模型返回工具名和参数。

**MaiBot 构建 ToolInvocation** ：把模型调用标准化为内部请求。

**Registry 查找 Provider** ：按工具名遍历 Provider，找到声明包含该工具且启用的 Provider。

**执行对应 Provider** ：调用 `provider.invoke()`。

### 5.4 工具调用

```mermaid
sequenceDiagram
    participant E as MaiSaka 推理引擎
    participant R as ToolRegistry
    participant P as ToolProvider
    participant H as 工具处理器

    E->>R: invoke(ToolInvocation, ToolExecutionContext)
    R->>P: list_tools(ToolAvailabilityContext)
    P-->>R: ToolSpec 列表
    R->>P: invoke(ToolInvocation, ToolExecutionContext)
    P->>H: 执行工具
    H-->>P: 原始结果
    P-->>R: ToolExecutionResult
    R-->>E: ToolExecutionResult
```

调用阶段的关键是定位 Provider。`ToolRegistry.invoke()` 会把 `ToolExecutionContext` 转成 `ToolAvailabilityContext`，用于匹配当前聊天环境中的工具声明。找到 Provider 后，它会执行工具并返回统一结果。

异常处理：

**Provider 抛出异常** ：Registry 捕获异常，返回失败的 `ToolExecutionResult`。

**Provider 未找到工具** ：返回 `未找到工具：{tool_name}`。

**工具自身失败** ：Provider 应返回 `success=False`，并填写 `error_message`。

**资源清理** ：运行时关闭时调用 `ToolRegistry.close()`，由每个 Provider 自行释放资源。

### 5.5 结果返回

工具结果进入 MaiSaka 后，会被写入对话历史或触发后续动作。结果可能包含：

**纯文本结果** ：写入 `content`，适合简单查询类工具。

**结构化结果** ：写入 `structured_content`，适合模型继续分析的数据。

**媒体内容项** ：写入 `content_items`，例如图片、音频或资源链接。

**后续消息** ：写入 `post_history_messages`，用于补充工具执行后的上下文。

`ToolExecutionResult.get_history_content()` 负责生成历史摘要。它优先使用文本内容，其次使用内容项摘要，再其次使用结构化内容 JSON，最后才使用错误信息。

## 6. 与插件开发的关系

插件开发文档 [Tool 组件](../plugin-dev/tools.md) 关注的是插件作者如何使用 `@Tool`、如何声明参数、如何返回值、如何处理图片和媒体。本文不重复这些 API 用法，只说明它们在内部架构中的位置。

对插件作者而言，需要理解三条边界：

**声明边界** ：插件使用 `@Tool` 声明能力，运行时把它变成 Tool 组件。

**发现边界** ：MaiSaka 通过 `PluginToolProvider` 和 `ToolRegistry` 发现插件工具。

**执行边界** ：插件方法在 Runner 子进程中执行，Host 通过统一工具协议接收结果。

对 MaiBot 内部实现而言，插件工具只是 `ToolProvider` 的一个来源。无论工具来自插件、旧 Action、内置模块还是 MCP，MaiSaka 最终只面对同一套 `ToolSpec`、`ToolInvocation` 和 `ToolExecutionResult`。

---

---
url: /develop.md
---

# 开发指南

MaiBot（麦麦 / MaiSaka）是基于大语言模型的可交互智能体。本节面向希望参与开发或编写插件的开发者，介绍项目的技术栈、目录结构与开发环境搭建。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | FastAPI |
| ORM | SQLModel |
| ASGI 服务器 | Uvicorn |
| 配置管理 | Pydantic + TOML + 热重载 |
| 插件 IPC | msgpack over UDS / TCP / Named Pipe |
| 包管理 | uv |
| 代码检查 | Ruff |
| 许可证 | GPL-3.0 |

## 项目结构

```
MaiBot/
├── src/                    # 核心源码
│   ├── config/             # 配置管理（TOML + Pydantic + 热重载）
│   ├── chat/               # 聊天处理、心流引擎、回复生成
│   ├── maisaka/             # 核心 AI 运行时（规划器、推理引擎、工具调用）
│   ├── A_memorix/           # 长期记忆引擎
│   ├── plugin_runtime/      # 插件运行时（Host/Runner IPC 架构）
│   ├── platform_io/         # 平台抽象层（路由、驱动、去重）
│   ├── llm_models/          # LLM 客户端实现
│   ├── services/            # 业务服务层（发送服务、记忆流等）
│   ├── webui/               # FastAPI Web 管理后端
│   ├── learners/            # 表达方式学习与黑话挖掘
│   ├── emoji_system/        # Emoji 管理
│   ├── mcp_module/          # Model Context Protocol 集成
│   ├── manager/              # 全局管理器（表情管理等）
│   ├── person_info/          # 人物画像信息模块
│   ├── common/              # 共享工具（数据库、日志、i18n、消息模型）
│   ├── prompt/              # Prompt 模板管理
│   └── core/                # 核心类型定义、事件总线、工具注册
├── dashboard/               # 前端（独立仓库构建，禁止修改）
├── plugins/                 # 第三方插件目录
├── src/plugins/built_in/    # 内置插件目录
├── pytests/                 # 测试
└── data/                    # 运行时数据（gitignore）
```

### 核心模块说明

* **config/**：使用 Pydantic 模型管理配置，支持 TOML 文件热重载，配置修改通过模版+版本号方式发布，不直接编辑运行时配置。
* **chat/**：聊天消息入口与主链路调度。包含 `ChatBot`（消息处理入口）、`ChatManager`（会话管理）、`HeartFlow`（心流消息处理器）等。
* **maisaka/**：核心 AI 运行时。以 `ChatLoopService` 为中心，负责 LLM 对话循环、工具调用规划、上下文消息管理等。
* **A\_memorix/**：长期记忆引擎，负责持久化用户偏好、对话记忆等心理学维度数据。
* **plugin\_runtime/**：插件运行时系统。采用 Host（主进程）/ Runner（子进程）IPC 架构，使用 msgpack 编解码，支持 Hook 机制、组件注册与热重载。
* **platform\_io/**：平台抽象层。通过 `RouteKey` 路由机制实现多平台消息收发的统一管理，支持驱动的注册、路由绑定、入站去重与出站跟踪。
* **llm\_models/**：LLM 客户端实现，封装各模型 API 的调用逻辑。
* **services/**：业务服务层，包含 `SendService`（出站消息发送）等核心服务。
* **webui/**：FastAPI 驱动的 Web 管理后端，提供插件管理、配置编辑、认证鉴权等功能，默认绑定 `127.0.0.1:8001`。
* **core/**：核心类型定义，包括 `ComponentType`、`ActionInfo`、`CommandInfo`、`ToolInfo`、`MaiMessages` 等，以及事件总线 (`EventBus`) 和工具注册中心 (`ToolRegistry`)。
* **learners/**：表达方式学习与黑话挖掘，通过分析聊天内容自动学习新词和表达习惯。
* **emoji\_system/**：表情包管理与分发系统，支持表情包的加载、匹配、拼图筛选和发送。
* **mcp\_module/**：Model Context Protocol 集成，支持 MCP Server/Client 协议的外部工具调用。
* **common/**：共享工具模块，包括数据库模型 (`SQLModel`)、日志系统、国际化 (`i18n`)、消息数据模型 (`MaimMessage`) 等公共基础设施。
* **prompt/**：Prompt 模板管理系统，支持多语言 Prompt 的加载、变量替换和模板热重载。
* **manager/**：全局管理器模块，管理应用级别的单例服务（如表情管理器等）。
* **person\_info/**：人物画像信息模块，负责用户画像数据的查询与展示。

## 开发环境搭建

### 前置条件

* Python 3.10 或更高版本
* [uv](https://github.com/astral-sh/uv) 包管理工具

### 安装依赖

```bash
uv sync
```

### 启动项目

```bash
uv run python bot.py
```

`bot.py` 采用 Runner/Worker 双进程模型：Runner 进程负责守护与重启（退出码 42 触发重启），Worker 进程执行实际的 `MainSystem` 初始化与任务调度。

### 运行测试

```bash
uv run pytest
```

### 代码检查与格式化

```bash
# Lint 检查
uv run ruff check .

# 自动格式化
uv run ruff format .
```

## 架构详解

深入了解各子系统的内部架构和实现原理：

### 基础域（Wave 1）—— 底层基础设施

底层基础设施，提供通信、工具抽象和系统运行底座。

* [事件总线架构](./architecture/event-bus.md)：MaiBot 全系统事件通信中枢，提供发布/订阅模型和拦截型、非拦截型两类事件处理器
* [工具系统架构](./architecture/tool-system.md)：四类工具来源的统一抽象层，通过 ToolProvider 接入插件、旧 Action、MaiSaka 内置工具和 MCP 工具

### 核心功能域（Wave 2）—— 主要业务链路

消息处理、推理、记忆、WebUI 和服务封装构成 MaiBot 的主要业务链路。

* [消息管线](./architecture/message-pipeline.md)：入站消息的完整处理流程——从平台适配器到 Hook 拦截、过滤、命令分发、HeartFlow 和出站发送
* [Maisaka 推理引擎](./architecture/maisaka-reasoning.md)：对话推理的核心——Timing Gate 节奏控制、Planner 规划循环、工具调用和打断机制
* [记忆系统](./architecture/memory-system.md)：A-Memorix 长期记忆引擎——双路检索、存储层、记忆策略和人物画像
* [WebUI 内部机制](./architecture/webui-internals.md)：FastAPI 后端架构——认证安全、WebSocket 通信、插件管理和配置热重载
* [服务层架构](./architecture/service-layer.md)：封装 LLM 调用、记忆操作、发送消息、数据库访问和统计聚合等业务服务，供上层模块复用

### 辅助功能域（Wave 3）—— 增强能力模块

增强能力模块，可按部署需求启用、替换或扩展。

* [表达学习架构](./architecture/expression-learning.md)：从对话中学习行为模式、俚语和表达偏好，为个性化回复提供持续更新的风格素材
* [表情系统内部架构](./architecture/emoji-internals.md)：管理表情包加载、匹配和生成，为消息理解与回复生成提供视觉表达素材
* [MCP 集成架构](./architecture/mcp-integration.md)：连接外部 MCP Server，将远程工具能力接入统一 Tool System
* [Prompt 模板系统](./architecture/prompt-templates.md)：管理 Prompt 模板加载、参数化和运行时更新，支撑推理引擎的上下文组织
* [全局管理器架构](./architecture/global-managers.md)：集中管理跨模块异步任务、配置状态和运行时服务，减少入口编排复杂度

## 下一步

* [架构设计](./architecture.md)：了解 Runner/Worker 进程模型与消息处理管线
* [贡献指南](./contributing.md)：了解代码规范与贡献流程
* [插件开发](./plugin-dev/)：学习如何开发 MaiBot 插件
* [适配器开发](./adapter-dev/)：学习如何开发平台适配器

---

---
url: /manual/getting-started.md
---

# 🚀 MaiBot 快速上手

**欢迎使用 MaiBot！** 本文档会带你从零开始，让麦麦成功跑起来。

## 📋 准备工作

你需要准备以下 3 样东西：

### 1️⃣ 一个 QQ 小号 🆔

* **必须是 QQ 小号**（机器人账号有被限制登录的风险，不要用主号）
* **能正常登录**（建议先在手机上确认账号正常）

### 2️⃣ 一个 AI 模型的 API 密钥 🔑

MaiBot 需要调用大语言模型来思考和回复。**首次启动时会自动生成默认配置，默认使用阿里云百炼（通义千问）**，你只需要获取百炼的 API 密钥即可。

| 服务商 | 价格 | 特点 | 获取方式 |
|--------|------|------|----------|
| **阿里云百炼 (Qwen)** 🏆 默认 | 便宜 | 默认集成，国内直连稳定；通义千问全系列 + 第三方模型，**文本/视觉/向量**全能力覆盖 | [百炼控制台](https://bailian.console.aliyun.com/) → API-KEY |
| **硅基流动** | 便宜 | 聚合 200+ 模型（DeepSeek、Qwen、GLM 等），**一个 API Key 覆盖文本/视觉/向量**，支持支付宝/微信支付 | [官网注册](https://cloud.siliconflow.cn/) |
| **DeepSeek** | 极低 | 极致性价比，推理能力顶尖（V4 支持 1M 超长上下文），MIT 开源可自托管 | [官网注册](https://platform.deepseek.com/) |
| **智谱 GLM** | 免费起 | 清华大学团队出品，**文本/视觉/向量全支持**；Flash 系列**永久免费**，新用户送 2000 万 tokens | [智谱开放平台](https://open.bigmodel.cn/) |
| **Kimi (Moonshot)** | 中等 | **超长上下文（262K）**，原生多模态（文本+图片+视频理解），中英双语能力出色 | [官网注册](https://platform.moonshot.cn/) |

::: tip 💡 新手推荐

* **不想折腾？用阿里云百炼** — 默认配置直接可用，只需填 API Key
* **追求极致性价比？用 DeepSeek** — 极低价格获得顶级推理能力
* **想要免费？用智谱 GLM** — Flash 模型永久免费，注册即送 2000 万 tokens
* 大部分服务商提供**免费试用额度**，可以先体验再决定
  :::

MaiBot 通过 Git 下载和管理代码。从 [git-scm.com](https://git-scm.com/) 下载安装。

## 🏃‍♂️ 安装步骤

### 第 1 步：下载 MaiBot 📥

**方法一：下载压缩包（Windows 新手推荐）**

1. 访问 [MaiBot Releases 页面](https://github.com/Mai-with-u/MaiBot/releases)
2. 找到最新版本，展开 **Assets**，下载 **Source code (zip)**
3. 解压到你想要的位置（比如桌面）

**方法二：Git 克隆**（如果你装了 Git）

```bash
git clone https://github.com/Mai-with-u/MaiBot.git
```

如需使用开发分支：

```bash
git checkout dev
```

### 第 2 步：安装 Python 🐍

> MaiBot 需要 **Python 3.12 及以上版本**（推荐 3.12 / 3.13）。

1. 访问 [python.org](https://www.python.org/downloads/) 下载 Windows 安装包
2. **安装时务必勾选 "Add Python to PATH"**
3. 打开命令提示符（`Win + R` → 输入 `cmd` → 回车），验证安装：

```bash
python --version
```

### 第 3 步：安装 uv（包管理器）📦

MaiBot 使用 [uv](https://docs.astral.sh/uv/) 管理依赖，速度比 pip 快很多。

在命令提示符中运行：

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后**关闭并重新打开**命令提示符。

### 第 4 步：安装项目依赖

进入你解压好的 MaiBot 文件夹，在地址栏输入 `cmd` 回车打开命令提示符，运行：

```bash
uv sync
```

这会创建虚拟环境（`.venv`）并安装所有依赖，大概需要几分钟。

::: tip 💡 国内用户
MaiBot 已配置清华镜像源，`uv sync` 会自动使用，无需手动设置。
:::

### 第 5 步：首次启动（生成配置 + 同意协议）

```bash
uv run python bot.py
```

**首次启动时，终端会显示用户协议（EULA）和隐私协议，输入 `同意` 并回车以继续。** 之后系统会自动生成默认配置到 `config/` 目录，然后退出——**这是正常行为**。

::: tip 💡 服务器/无头环境
如果在没有交互终端的服务器上部署，无法输入"同意"，可以使用环境变量跳过协议确认：

```bash
# 先运行一次，终端会显示需要的 hash 值
uv run python bot.py
# 复制终端显示的 EULA_AGREE=xxx 和 PRIVACY_AGREE=xxx
# 然后设置环境变量重新启动
export EULA_AGREE=<显示的hash>
export PRIVACY_AGREE=<显示的hash>
uv run python bot.py
```

:::

### 第 6 步：再次启动，进入 WebUI

```bash
uv run python bot.py
```

这次启动后，你会看到类似这样的日志：

```
🌐 WebUI 服务器启动中...
🌐 访问地址: http://127.0.0.1:8001
🔑 WebUI 访问令牌: e7b2a4f1...（一长串字符）
💡 请在浏览器中打开访问地址，输入上面的访问令牌进行登录
```

### 第 7 步：浏览器打开 WebUI，完成设置 🌐

1. 打开浏览器，访问 **http://127.0.0.1:8001**
2. 你会看到一个登录页面，**输入终端里那串访问令牌（Access Token）**
3. 登录成功后，如果是首次使用，会自动进入**配置向导**
4. 在向导中填写 **API 密钥**（只需要填这个，其他都有默认值）
5. 完成后系统标记初始化完成，进入正常管理界面

::: tip 💡 所有配置都在 WebUI 上操作
修改昵称、人格、聊天频率、模型等，都可以在 WebUI 的"配置管理"中在线修改，**无需手动编辑文件**，保存即生效。
:::

## 📱 连接 QQ

MaiBot 核心启动后，还需要连接 QQ 才能收发消息。MaiBot 通过 **NapCat** 实现 QQ 接入。

### 安装 NapCat

参照 [NapCat 官方安装指南](https://napneko.github.io/guide/install) 安装并登录你的 QQ 小号。

### 安装 NapCat 适配器

在 MaiBot WebUI 中（浏览器访问 `http://127.0.0.1:8001`）：

1. 点击左侧菜单 **"插件管理"**
2. 搜索 **"NapCat 适配器"**
3. 点击安装

安装完成后，根据适配器的配置说明填写 NapCat 的连接地址即可。

::: warning ⚠️ 重要：插件默认不启用
**无论是通过 WebUI 安装还是手动克隆到 `plugins/` 目录，插件安装后默认都是禁用状态。** 安装完成不等于就能用了！

需要在 WebUI 的 **"插件管理"** 页面中，找到 NapCat 适配器，**手动点击启用开关**。

或者直接编辑 `plugins/MaiBot-Napcat-Adapter/config.toml`，将 `[plugin] enabled` 改为 `true`，然后重启 MaiBot。

> 如何确认是否启用？启动后看日志：出现「激活」说明已启用，出现「跳过激活」说明还是禁用状态。
> :::

::: tip 💡 更多适配器信息
详细的 NapCat 适配器安装和配置请参考 [NapCat 适配器文档](../adapters/napcat.md)。
:::

## 🎉 开始聊天

### 测试机器人

在 QQ 群里 @机器人，或者在私聊中发送消息：

```
@麦麦 你好！
```

如果机器人回复你了，恭喜，部署成功！🎉

## 🆘 常见问题

### 启动后自动退出？

查看日志确认原因，在命令提示符中运行：

```bash
uv run python bot.py
```

常见原因：

* **API 密钥未填写** — `model_config.toml` 中的 `api_key` 还是 `your-api-key`
* **配置格式错误** — TOML 文件语法不正确

### 端口被占用？

启动时如果报错类似以下内容：

```
WebUI 服务器 启动失败: 端口 8001 已被占用 (host=127.0.0.1)
```

说明默认端口被其他程序占用了。

**解决方法一：改端口**

编辑 `config/bot_config.toml`，在 `[webui]` 段落中修改端口：

```toml
[webui]
port = 8002   # 改成其他未被占用的端口，如 8002、8003
```

保存后重新启动，WebUI 访问地址也会变成 `http://127.0.0.1:8002`。

> 💡 如果 `maim_message` 的 WebSocket 端口（默认 8000）也被占用，同样在 `[maim_message]` 段落中修改 `ws_server_port`。

**解决方法二：关闭占用端口的进程**

```bash
# Windows（CMD）
netstat -ano | findstr :8001
# 记下最后一列的 PID，然后用任务管理器或命令关闭
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8001
# 记下 PID，然后
kill -9 <PID>
```

关闭后重启 MaiBot 即可使用原来的端口。

### 机器人不回复？

按顺序排查：

1. ✅ NapCat 是否在线？（NapCat 界面显示已登录）
2. ✅ API 密钥是否正确？（WebUI 配置中检查）
3. ✅ 插件是否已安装？（WebUI 插件管理中确认）
4. ✅ 日志是否有报错？（WebUI 日志页面查看）

### API Key 无效？

* 确认没有多余的空格
* 检查 API 服务商选择是否正确
* 确认账户是否有余额或免费额度

### 浏览器打不开？

* 确认 MaiBot 正在运行（终端窗口是打开的）
* 检查地址是否正确：`http://127.0.0.1:8001`
* 防火墙是否允许

### 如何修改配置？

* **通过 WebUI**：浏览器访问 `http://127.0.0.1:8001`，在配置管理页面修改
* **直接编辑文件**：修改 `config/bot_config.toml` 或 `config/model_config.toml`
* 修改后大部分配置无需重启，MaiBot 支持**配置热重载**（部分配置仍需重启生效）

## 🎯 下一步

恭喜你成功部署了 MaiBot！接下来可以：

* 📚 **[配置详解](../configuration/)** — 调整人格、聊天频率、记忆等参数
* 🔌 **[插件开发](../../develop/plugin-dev/)** — 为麦麦开发新功能
* 🧠 **[了解麦麦的大脑](../../manual/features/maisaka-reasoning.md)** — 深入理解 MaiBot 的推理机制
* 💬 **邀请麦麦进群** — 和朋友们一起玩

**遇到问题？** 加入技术交流群提问：[麦麦脑电图](https://qm.qq.com/q/RzmCiRtHEW)

**祝你玩得开心！**

---

---
url: /develop/plugin-dev.md
---

# 插件开发指南

MaiBot 的插件系统采用 Host/Runner IPC 架构，插件代码运行在独立的子进程中，通过 msgpack 编码的 RPC 协议与主进程通信。本节介绍插件系统的架构原理、开发流程和核心概念。

## 架构概览

```mermaid
graph TD
    subgraph Host 主进程
        A[PluginRuntimeManager] --> B[Builtin Supervisor]
        A --> C[Third-party Supervisor]
        B --> D[RPC Server]
        C --> E[RPC Server]
    end
    subgraph Runner 子进程
        F[Builtin Runner] --> G[内置插件]
        H[Third-party Runner] --> I[第三方插件]
    end
    D <-->|msgpack over UDS/TCP/NamedPipe| F
    E <-->|msgpack over UDS/TCP/NamedPipe| H
```

### Host（主进程侧）

* **PluginRuntimeManager**：单例管理器，管理 Builtin 和 Third-party 两个 Supervisor
* **PluginSupervisor**：负责 Runner 子进程的启动、停止、健康检查和插件热重载
* **ComponentRegistry**：组件注册表，管理所有插件声明的 Tool、Command 等组件
* **HookDispatcher**：Hook 分发器，将命名 Hook 调用分发到对应 Supervisor

### Runner（子进程侧）

* 每种 Supervisor 各自管理一个独立的 Runner 子进程
* 通过 `PluginLoader` 发现和加载插件
* 通过 `RPCClient` 与 Host 通信
* 在插件加载后注入 `PluginContext`，再调用 `on_load()` 生命周期方法

### 通信协议

* **编解码**：使用 msgpack 格式进行二进制序列化（`MsgPackCodec`）
* **传输层**：支持 Unix Domain Socket、TCP、Named Pipe 三种传输方式
* **RPC 模型**：
  * Host → Runner：通过 `invoke_plugin()` 调用插件组件（Tool、Command 等）
  * Runner → Host：插件通过 `self.ctx` 的能力代理发起 RPC 回调（如 `ctx.send.text()`、`ctx.db.query()`）

## 快速开始

### 1. 安装 SDK

```bash
pip install maibot-plugin-sdk
```

::: tip 注意
安装包名为 `maibot-plugin-sdk`，但代码中导入时使用 `maibot_sdk`：

```python
from maibot_sdk import MaiBotPlugin, Command, Tool
```

:::

### 2. 创建插件目录

```
plugins/
└── my-plugin/
    ├── _manifest.json
    ├── plugin.py
    └── config.toml          # 可选
```

### 3. 编写 Manifest

在 `_manifest.json` 中声明插件元信息（完整字段说明见 [Manifest 系统](./manifest.md)）：

```json
{
  "manifest_version": 2,
  "id": "com.example.my-plugin",
  "version": "1.0.0",
  "name": "我的插件",
  "description": "一个示例插件",
  "author": {
    "name": "开发者",
    "url": "https://github.com/developer"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/developer/my-plugin"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "1.99.99"
  },
  "sdk": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "capabilities": ["send_message"],
  "i18n": {
    "default_locale": "zh-CN"
  }
}
```

### 4. 编写插件代码

在 `plugin.py` 中继承 `MaiBotPlugin`，用装饰器声明组件，并实现三个生命周期方法：

```python
from maibot_sdk import MaiBotPlugin, Command, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("插件配置已更新: version=%s", version)

    @Tool(
        "greet",
        brief_description="向用户打招呼",
        detailed_description="参数说明：\n- stream_id：string，必填。当前聊天流 ID。",
        parameters=[
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="当前聊天流 ID",
                required=True,
            ),
        ],
    )
    async def handle_greet(self, stream_id: str, **kwargs):
        await self.ctx.send.text("你好！", stream_id)
        return {"success": True, "message": "已回复"}

    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2


def create_plugin():
    return MyPlugin()
```

::: warning 必须实现三个生命周期方法
SDK 要求所有插件实现 `on_load()`、`on_unload()` 和 `on_config_update()` 三个方法，否则 Runner 会拒绝加载。详见 [生命周期](./lifecycle.md)。
:::

### 5. 安装与运行

将插件目录放入 `plugins/` 文件夹，启动 MaiBot 后插件会自动被发现和加载。也可以通过 WebUI 进行插件管理。

## 核心概念

### 插件基类

所有插件必须继承 `MaiBotPlugin`，通过类属性和装饰器声明插件能力：

```python
from maibot_sdk import MaiBotPlugin, Tool, Command, CONFIG_RELOAD_SCOPE_SELF
from typing import ClassVar, Iterable


class MyPlugin(MaiBotPlugin):
    # 订阅全局配置热重载（仅 "bot" 和 "model" 两个值有效）
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    @Tool("my_tool", brief_description="示例工具")
    async def handle_tool(self, **kwargs):
        ...

    @Command("my_cmd", pattern=r"^/my_cmd")
    async def handle_cmd(self, **kwargs):
        ...


def create_plugin():
    return MyPlugin()
```

### 组件装饰器

SDK 提供 8 种组件装饰器，全部从 `maibot_sdk` 顶层导入：

| 装饰器 | 用途 | 说明 |
|--------|------|------|
| `@Tool` | LLM 工具/函数调用 | LLM 可调用的工具，最常用的组件类型 |
| `@Command` | 斜杠命令 | 用户通过正则匹配触发的命令 |
| `@HookHandler` | 命名 Hook 处理器 | 订阅特定 Hook 点，支持 blocking/observe 模式 |
| `@EventHandler` | 消息/工作流事件 | 监听消息、LLM 生成等生命周期事件 |
| `@API` | 插件间 API | 暴露可被其他插件调用的 API |
| `@MessageGateway` | 平台适配器 | 将外部平台（QQ、Discord 等）接入 MaiBot |
| `@LLMProvider` | LLM Provider | 声明新LLM模型接入点（client\_type），扩展模型服务 |
| `@Action` | 兼容旧插件 | 内部自动转换为 `@Tool`，新插件应直接使用 `@Tool` |

### 能力代理

通过 `self.ctx` 访问 16 种能力代理，所有调用自动通过 RPC 转发到 Host：

```python
# 上下文访问
self.ctx              # PluginContext 实例
self.ctx.logger       # logging.Logger，名称为 "plugin.<plugin_id>"

# 能力代理
self.ctx.api          # 插件 API 查询、调用与动态同步
self.ctx.gateway      # 消息网关路由与运行时状态上报
self.ctx.send         # 发送文本、图片、表情、转发、混合消息
self.ctx.db           # 数据库增删改查计数
self.ctx.llm          # LLM 文本生成、工具调用、嵌入向量与 ASR 语音识别
self.ctx.config       # 插件配置读取
self.ctx.emoji        # 表情包管理
self.ctx.message      # 历史消息查询
self.ctx.frequency    # 发言频率控制
self.ctx.component    # 插件与组件管理
self.ctx.chat         # 聊天流查询、打开或创建聊天流
self.ctx.person       # 用户信息查询
self.ctx.render       # 将 HTML 渲染为 PNG 图片
self.ctx.knowledge    # LPMM 知识库搜索
self.ctx.tool         # LLM 工具定义查询
self.ctx.maisaka      # Maisaka 上下文追加与主动任务
```

### 配置模型

插件可通过 `PluginConfigBase` 声明强类型配置，Runner 会自动生成默认配置和 WebUI Schema：

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyPluginConfig(PluginConfigBase):
    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 通过 self.config 访问强类型配置
        self.ctx.logger.info("当前问候语: %s", self.config.greeting)
        # 通过 self.get_plugin_config_data() 访问原始 dict
        raw = self.get_plugin_config_data()
```

* 声明 `config_model` 后，`self.config` 返回强类型配置实例
* 未声明时调用 `self.config` 会抛出 `RuntimeError`
* `self.get_plugin_config_data()` 始终可用，返回原始配置字典
* 配置来源为插件目录下的 `config.toml`

## 目录结构约定

```
my-plugin/
├── _manifest.json       # 必需：插件清单
├── plugin.py            # 必需：插件入口，包含 create_plugin()
├── config.toml          # 可选：插件配置
├── i18n/                # 可选：国际化资源
│   ├── zh-CN.json
│   └── en-US.json
└── assets/              # 可选：静态资源
```

## 内置插件与第三方插件

MaiBot 维护两个独立的 Runner 子进程：

* **内置插件**：位于 `src/plugins/built_in/`，运行在 Builtin Supervisor 下
* **第三方插件**：位于 `plugins/`，运行在 Third-party Supervisor 下

两者使用相同的通信协议和组件注册机制。Supervisor 之间的启动顺序由跨 Supervisor 依赖关系决定，如果检测到循环依赖则拒绝启动。

## 下一步

* [Manifest 系统](./manifest.md)：了解 `_manifest.json` 的完整字段定义与校验规则
* [生命周期](./lifecycle.md)：学习插件加载、卸载与配置热重载的生命周期方法
* [Hook 系统](./hooks.md)：学习如何使用 @HookHandler 拦截和改写消息
* [Tool 组件](./tools.md)：学习如何开发 LLM 可调用的工具组件
* [Command 组件](./commands.md)：学习如何开发斜杠命令组件
* [LLMProvider 组件](./llmprovider.md)：学习如何开发自定义LLM Provider接入新模型
* [Action 组件](./actions.md)：了解兼容旧系统的 @Action 装饰器
* [配置管理](./config.md)：学习如何声明和使用插件配置
* [API 参考](./api-reference.md)：查阅完整的插件 SDK API

---

---
url: /changelog.md
---

# 更新日志

本页记录 MaiBot 的主要版本更新内容。完整更新日志请参阅 [GitHub Releases](https://github.com/Mai-with-u/MaiBot/releases)。

## v1.0.0

1.0.0 是一次系统性升级。如果想看更完整的图文说明，可以阅读 [MaiBot 1.0.0 更新专题](./v1-0-0.md)。

### 重大更新

* **Maisaka 推理引擎重构**：全面升级规划建设与回复生成的协作机制，Planner 与 Replyer 现已实现深度联动
* **思考力度机制**：动态控制回复时间和长度，让回复节奏更自然
* **A-Memorix 记忆引擎 v1.0**：全新长期记忆系统，支持知识图谱、人物画像、聊天摘要
* **反馈纠错系统**：根据用户反馈自动修正过时记忆，保持记忆时效性
* **MCP 内置插件**：Model Context Protocol 作为内置插件加入，默认不启用
* **全局记忆**：新增全局记忆配置，可选择让记忆跨会话检索

### WebUI 重大更新

* **模型预设市场**：可以将模型配置完整分享，分享按钮位于模型配置界面右上角
* **全面安全加固**：所有 WebUI API 和 WebSocket 端点添加身份认证保护，Cookie 添加 Secure 和 SameSite 属性
* **前端认证重构**：从 localStorage 迁移到 HttpOnly Cookie，新增 WebSocket 临时 token 认证机制
* **增强插件配置管理**：支持原始 TOML 配置的加载和保存，前端支持查看和编辑插件配置文件源文件

### 细节功能更新

* 移除频率自动调整
* 移除情绪功能
* 优化记忆检索超时设置
* 插件安装时可主动选择克隆的分支
* 首页反馈问卷功能，可以提交反馈信息和建议
* 黑话和表达不再提取包含名称的内容
* 模型界面支持编辑 extra params 额外字段
* 模型任务分配支持编辑慢请求检测阈值
* 模型界面支持对单个模型单独指定温度和 max\_tokens 参数

## v0.12.2

* 优化私聊 wait 逻辑
* 超时时强制引用回复
* 修复部分适配器断联问题
* 修复表达反思配置未生效
* 优化记忆检索逻辑

## v0.12.1

### 🌟 主要更新

* 添加年度总结功能，可在 WebUI 查看
* 可选让 LLM 判定引用回复
* 表达方式优化：支持自动和手动评估，使其更精准
* 回复和规划记录：WebUI 可以查看每一条回复和 plan 的详情

### 细节功能更改

* 优化间隔过长消息的显示
* 启用黑话检测（enable\_jargon\_detection）
* 全局记忆黑名单（global\_memory\_blacklist），指定部分群聊不参与全局记忆
* 移除 utils\_small 模型，移除弃用的 LPMM 模型

## v0.12.0

### 🌟 重大更新

* 添加思考力度机制，动态控制回复时间和长度
* Planner 和 Replyer 联动，更好的回复逻辑
* 新的私聊系统
* 增加麦麦做梦功能
* MCP 插件作为内置插件加入
* 添加全局记忆配置

## 更早版本

更早版本的更新日志请参阅 [GitHub Releases](https://github.com/Mai-with-u/MaiBot/releases) 或项目仓库中的 `changelogs/` 目录。

---

---
url: /develop/architecture/service-layer.md
description: MaiBot services 服务层架构说明
---

本文基于 code-map 快照编写。

# 服务层架构

MaiBot 的 `services/` 服务层是宿主进程内部的业务逻辑封装层。它把 LLM 调用、长期记忆、出站消息、数据库访问、统计聚合和记忆自动化等能力收口成稳定的 Python 接口，供 `chat`、`maisaka`、`webui` 以及插件运行时包装层调用。

服务层不直接承担平台协议细节，也不替代 A\_memorix 内核或 Platform IO 驱动。它的职责是把上层意图翻译成底层模块能执行的请求，再把底层返回的结果整理成上层更容易消费的对象。

## 服务层在架构中的位置

**业务边界**：服务层位于宿主业务模块和底层基础设施之间。`chat` 负责消息入口、会话状态和管线调度，`maisaka` 负责推理、规划和工具执行，`webui` 负责管理接口和可视化，底层模块负责协议、数据库、模型客户端和记忆内核。

**调用方边界**：内部模块可以直接导入 `src.services` 下的服务模块。插件系统不应绕过服务层直接访问底层模块，而应通过 `plugin_system.apis` 的薄包装间接调用，这样插件升级时不会把底层实现细节暴露给插件生态。

**职责边界**：服务层允许封装请求构造、参数规范化、错误收敛、统计记录和统一日志，但不应该把不同平台的私有协议写进服务层。平台差异应继续留在 `platform_io` 和适配器驱动中。

**数据边界**：服务层返回的对象优先面向业务语义，例如 `MemorySearchResult`、`LLMResponseResult`、`DashboardData`。底层模型、数据库行和平台回执可以在服务层内转换，避免上层到处处理实现细节。

## 架构图

```mermaid
flowchart TD
    subgraph 上层模块
        Chat[chat 消息管线]
        Maisaka[Maisaka 推理引擎]
        WebUI[WebUI FastAPI]
        Plugin[plugin_system.apis 薄包装]
    end

    subgraph services 服务层
        Send[SendService]
        LLM[LLMService]
        Memory[MemoryService]
        DB[DatabaseService]
        Stats[StatisticsService]
        Automation[MemoryAutomationService]
        Embedding[EmbeddingService]
        Generator[GeneratorService]
    end

    subgraph 底层基础设施
        PlatformIO[Platform IO]
        LLMModels[llm_models 编排调度器]
        AMemorix[A_memorix 长期记忆内核]
        SQL[SQLModel 数据库]
        LocalStore[local_storage 缓存]
    end

    Chat --> Send
    Chat --> LLM
    Chat --> Memory
    Chat --> DB
    Chat --> Generator
    Maisaka --> LLM
    Maisaka --> Memory
    Maisaka --> Send
    WebUI --> Memory
    WebUI --> Stats
    WebUI --> DB
    Plugin --> Send
    Plugin --> LLM
    Plugin --> Memory

    Send --> PlatformIO
    LLM --> LLMModels
    Memory --> AMemorix
    DB --> SQL
    Stats --> SQL
    Stats --> LocalStore
    Automation --> Memory
    Automation --> LLM
    Automation --> DB
    Generator --> LLM
```

## 服务目录总览

**`__init__.py`**：声明 `services` 是核心服务层。模块注释明确说明内部模块应直接使用此层，插件系统通过薄包装间接调用。

**`send_service.py`**：统一出站消息发送。它构造 `SessionMessage`，执行发送前 Hook，委托 `PlatformIOManager.send_message()`，再处理成功回执、落库、表情包使用统计和 Maisaka 历史同步。

**`llm_service.py`**：统一 LLM 调用门面。它解析模型任务名，构造 `LLMServiceClient`，封装文本生成、多图消息生成、图片理解、语音转写和兼容嵌入入口，并把实际执行交给 `LLMOrchestrator`。

**`memory_service.py`**：统一长期记忆操作。它通过 `a_memorix_host_service.invoke()` 路由到 A\_memorix，提供搜索、文本摄入、摘要摄入、人物画像查询、维护和管理类接口。

**`memory_flow_service.py`**：记忆自动化服务。它包含人物事实写回队列、聊天摘要写回队列和 `MemoryAutomationService`，在消息发送后触发自动提取和摘要写回。

**`database_service.py`**：数据库通用 CRUD 门面。它封装 SQLModel 查询、过滤、排序、分页、日期和枚举序列化，并提供工具记录保存接口。

**`statistics_service.py`**：WebUI 仪表盘统计门面。它聚合消息量、模型请求、在线时间、Token 用量、费用和最近活动，并提供 24h、168h、720h 缓存。

**`statistics_aggregation_service.py`**：统计汇总表刷新服务。它用原生 SQL 增量刷新消息、工具调用和模型用量的小时汇总表。

**`embedding_service.py`**：文本嵌入服务。它把嵌入请求转发给 `llm_models`，推荐替代 `LLMServiceClient.embed_text()` 的兼容入口。

**`generator_service.py`**：回复器调用入口。它从 `replyer_manager` 获取会话级 `MaisakaReplyGenerator`，生成回复文本并做分词、纠错等后处理。

**`message_service.py`**：消息查询和格式化服务。它按时间范围、会话、分页检索 `SessionMessage`，支持工具记录查询和历史消息量统计。

**`message_word_frequency_service.py`**：词频服务。它使用 jieba 和正则规则分析群聊消息，维护 `HighFrequencyTerm` 表，并提供缓存和过期清理。

**`html_render_service.py`**：HTML 渲染服务。它管理 Playwright 浏览器实例生命周期，把 HTML 内容渲染为 PNG 图片。

**`telemetry_stats_service.py`**：遥测统计服务。它构建匿名运行载荷，聚合模型任务分配、LLM 用量、在线时段和消息量。

**`service_task_resolver.py`**：模型任务解析工具。它从 `model_task_config` 中解析可用任务名，支持旧版 `TaskConfig` 对象映射。

**`llm_cache_stats.py`**：LLM prompt cache 统计服务。它按任务、请求类型和模型聚合缓存命中指标，并生成 HTML 或 JSON 诊断报告。

## 核心服务详解

### SendService

**定位**：`SendService` 是内部模块的统一出站消息发送入口。它对应文档中的 `send_text`、`send_image`、`send_emoji` 三类发送意图，代码入口分别是 `text_to_stream()`、`image_to_stream()`、`emoji_to_stream()`，以及面向消息组件序列的 `custom_reply_set_to_stream()`。

**职责**：服务层负责把文本、Base64 图片或 Base64 表情包转换成内部 `MessageSequence`，再构造出站 `SessionMessage`。它会补齐机器人账号、平台、群信息、路由元数据、引用回复组件和轻量纯文本摘要，但不会决定底层走插件链还是 legacy 旧链。

**Platform IO 协作**：真正的路由和发送由 `PlatformIOManager` 完成。`SendService` 会先调用 `ensure_send_pipeline_ready()`，再用 `build_route_key_from_message()` 构造路由键，最后调用 `send_message()`。发送成功后，服务层回填外部平台消息 ID，分发适配器回调，并在需要时写入数据库。

**状态副作用**：成功发送后，`SendService` 会记录表情包使用次数，通知 `memory_automation_service.on_message_sent()`，并可选择同步到当前会话的 Maisaka 历史。这个同步动作让后续推理能看到自己刚刚发出的消息，避免历史链断裂。

**失败语义**：如果目标聊天流不存在、平台未配置机器人账号、Platform IO 发送失败或发送前 Hook 中止，服务层返回 `None` 或 `False`。调用方不应假设消息一定送达，需要按返回值处理失败分支。

### LLMService

**定位**：`LLMService` 是宿主侧的 LLM 调用门面。它把文本生成、消息列表生成、图片理解、语音转写和兼容嵌入请求统一成服务层入口，再把请求交给 `src.llm_models` 的 `LLMOrchestrator` 执行。

**请求构造**：`LLMServiceClient` 初始化时会解析 `task_name`，绑定 `request_type` 和 `session_id`，并创建 `LLMOrchestrator`。`generate_response()` 负责单轮文本请求，`generate_response_with_messages()` 接收消息工厂，`generate_response_for_image()` 会规范化图片 Base64 和格式，`transcribe_audio()` 负责语音转写。

**重试和模型选择**：服务层不直接实现重试循环，而是通过 `LLMOrchestrator` 统一处理。底层会根据任务配置选择模型，支持随机、顺序和负载均衡策略。网络错误、空回复、429、5xx、响应解析失败等可重试问题会在底层按 provider 配置重试。

**流式响应**：底层请求对象支持 `stream_response_handler`，用于承载流式响应能力。服务层保留这个扩展点，让上层可以在不改变服务边界的情况下接入流式消费逻辑，同时继续由底层负责协议客户端和请求生命周期。

**统计记录**：`LLMServiceClient` 会记录 prompt cache 命中和未命中 token，底层 `llm_usage_recorder` 会把模型调用写入 `ModelUsage`。这些记录再被 `StatisticsService` 汇总成 WebUI 仪表盘数据。

**兼容入口**：`embed_text()` 保留在 `LLMServiceClient` 中，但代码注释推荐新调用方改用 `EmbeddingServiceClient`。这样可以把文本生成和向量生成拆成更清晰的职责。

### MemoryService

**定位**：`MemoryService` 是 A\_memorix 的宿主侧门面。它把长期记忆的搜索、写入、维护和管理操作封装成稳定接口，避免业务模块直接理解 A\_memorix 的组件名和返回结构。

**add 写入**：代码中的写入入口主要是 `ingest_text()` 和 `ingest_summary()`。`ingest_text()` 用于摄入文本、实体、关系、标签和来源元数据，`ingest_summary()` 用于写入聊天摘要或外部整理后的文本。两者都会带上 `chat_id`、`user_id`、`group_id`、时间范围和过滤策略。

**recall 检索**：`search()` 对应记忆召回。调用方传入查询文本、limit、mode、人物 ID、会话 ID、时间范围和过滤参数，服务层调用 A\_memorix 的 `search_memory`，再把结果整理成 `MemorySearchResult` 和 `MemoryHit`。

**forget 与删除**：`forget` 语义在代码中分散在维护和管理接口里。`maintain_memory()` 支持 restore、reinforce、freeze、protect 等维护动作，`delete_admin()` 支持预览和执行删除操作，WebUI 和内置工具可通过 `action` 参数表达更细的删除意图。

**graph\_query 图谱查询**：`graph_admin()` 是图谱相关查询和管理的入口。WebUI 中 `action="get_graph"` 和 `action="search"` 就是通过该服务查询记忆图谱。人物画像查询则使用 `get_person_profile()`。

**错误收敛**：服务层会把 A\_memorix 的复杂返回统一成布尔值、错误字符串和结构化对象。调用方可以优先判断 `success`，再读取 `detail`、`error` 或结构化命中列表。

### DatabaseService

**定位**：`DatabaseService` 是 SQLModel 访问的通用封装。它不表达业务规则，而是把数据库会话、查询语句、过滤条件、排序字段、分页限制和返回值序列化统一起来。

**CRUD 操作**：`db_save()` 支持按主键或指定字段更新或插入记录，`db_get()` 支持过滤、排序、limit 和单条结果，`db_update()` 和 `db_delete()` 按过滤条件批量操作，`db_count()` 返回匹配记录数量。

**类型处理**：服务层会把 `datetime`、`date`、`Enum`、字典、列表和集合转换成适合 msgpack 或 JSON 的值。返回记录时会优先使用 Pydantic 的 `model_dump()`，没有该能力时再回退到 `__dict__`。

**工具记录**：`store_tool_info()` 和兼容入口 `store_action_info()` 用于保存 Maisaka 工具调用记录。它们会写入工具 ID、时间戳、会话 ID、工具名称、工具数据、推理文本和展示提示。

**调用边界**：业务服务可以在服务层内部调用 `DatabaseService`，例如 `StatisticsService` 读取 `ModelUsage`、`OnlineTime`、`Messages` 和 `ToolRecord`。普通业务模块不应到处手写 SQLModel 查询，除非它本身就是数据访问层的一部分。

### StatisticsService

**定位**：`StatisticsService` 是 WebUI 仪表盘统计的服务层入口。它面向前端展示聚合数据，而不是直接暴露数据库表。

**在线时间**：服务层读取 `OnlineTime` 记录，并按查询窗口裁剪起止时间。它计算窗口内的有效在线秒数，再用于计算每小时费用和每小时 token 用量。

**消息计数**：服务层通过 `count_messages()` 统计时间窗口内的总消息数和带引用回复的消息数。这些指标进入 `StatisticsSummary`，供仪表盘展示聊天活跃度。

**Token 用量**：服务层读取 `ModelUsage`，聚合请求数、总费用、总 token、平均响应耗时，并按模型名称排序返回 Top 模型统计。小时和日级时间序列会补齐空桶，便于前端绘制连续图表。

**缓存策略**：`get_dashboard_statistics()` 会优先读取 `local_storage` 中的仪表盘缓存，默认缓存 600 秒，支持 24h、168h、720h 三个窗口。`refresh_dashboard_statistics_cache()` 可以重新计算并保存稀疏时间序列。

**汇总表协作**：`statistics_aggregation_service` 负责把消息、工具记录和模型用量写入小时汇总表。`StatisticsService` 面向仪表盘，汇总表服务面向查询性能，两者不应混成一个职责。

### MemoryAutomationService

**定位**：`MemoryAutomationService` 是记忆自动化的协调器。它包含 `PersonFactWritebackService` 和 `ChatSummaryWritebackService`，在消息发送后把合适的内容送入异步队列。

**触发方式**：当前实现不是简单全局定时任务，而是由 `send_service` 在发送成功后调用 `on_message_sent()`。这样自动化服务只处理已经确认发送的消息，避免把失败消息写入长期记忆。

**人物事实写回**：`PersonFactWritebackService` 会识别目标人物，收集用户原始发言和邻近上下文，再使用 `LLMServiceClient(task_name="utils")` 提取稳定事实。提取结果会通过 `store_person_memory_from_answer()` 写入 A\_memorix。

**聊天摘要写回**：`ChatSummaryWritebackService` 会按会话维护触发游标。当新增消息数达到配置阈值时，它读取最近上下文，调用 `memory_service.ingest_summary()` 写入聊天摘要，并更新触发计数避免重启后重复写入。

**队列边界**：两个写回服务都使用 `asyncio.Queue`，默认队列大小为 256。队列满时服务层只记录警告并跳过本次触发，不阻塞主消息发送流程。

**配置依赖**：人物事实写回和聊天摘要写回都受 A\_memorix 集成配置控制。服务层在入队前检查配置，避免用户关闭功能后仍消耗模型调用和写入资源。

## 服务间依赖关系

**LLMService 与 MemoryService**：LLMService 依赖 MemoryService 注入记忆上下文。这里不是全局单例强依赖，而是调用方先从 `MemoryService.search()` 或启发式记忆模块得到 `MemorySearchResult`，再把它格式化为 prompt 或 `message_factory` 中的上下文消息，交给 `LLMServiceClient.generate_response_with_messages()` 使用。

**MemoryService 与 A\_memorix**：MemoryService 的所有核心记忆操作都通过 `a_memorix_host_service.invoke()` 路由。服务层负责参数整理、超时、异常收敛和返回对象转换，A\_memorix 负责索引、检索、摘要、图谱和写入内核。

**SendService 与 Platform IO**：SendService 负责构造消息和执行 Hook，Platform IO 负责平台路由和驱动发送。服务层不直接调用适配器驱动，这样新增平台时不需要改业务发送逻辑。

**StatisticsService 与 DatabaseService**：StatisticsService 当前直接读取 SQLModel 模型和统计汇总表，但它依赖数据库服务所维护的数据契约。消息、工具记录、模型用量和在线时间都需要由其他服务或管线先写入数据库。

**MemoryAutomationService 与 LLMService**：人物事实写回会把用户发言、上下文和机器人回复交给 `LLMServiceClient` 做事实提取。这个调用使用 `utils` 任务，并带有明确的提示约束，要求只提取用户原始发言可支持的稳定事实。

**MemoryAutomationService 与 MemoryService**：聊天摘要写回最终调用 `memory_service.ingest_summary()`。摘要服务只负责判断触发条件、收集上下文和更新游标，真正写入长期记忆仍由 MemoryService 完成。

**GeneratorService 与 LLMService**：GeneratorService 通过 `replyer_manager` 获取 Maisaka 回复器，回复器内部再按请求类型获取 `LLMServiceClient`。这样回复生成、表达方式和模型调用被分层管理。

## Hook 扩展点

**`send_service.after_build_message`**：出站 `SessionMessage` 构建完成后触发。此时消息已经包含目标会话、机器人账号、消息组件和轻量纯文本摘要，但尚未进入 Platform IO。Hook 可以改写消息体，也可以中止发送。

**`send_service.before_send`**：真正调用 Platform IO 前触发。它是最接近真实发送的拦截点，适合做敏感词二次检查、平台策略判断、引用回复修正或发送参数改写。

**`send_service.after_send`**：发送流程结束后触发。它只用于观察最终结果，不允许中止或改写。参数中包含 `sent`、`typing`、`set_reply`、`reply_message_id`、`storage_message` 和 `show_log`。

**send\_before 语义**：文档中说的 `send_before` 对应代码里的 `send_service.before_send`。它接收的是发送前的最终消息和发送参数，允许 Hook 通过返回 kwargs 修改这些参数。

**send\_after 语义**：文档中说的 `send_after` 对应代码里的 `send_service.after_send`。它用于日志、埋点、审计和后续观察，不应在这里重新发起发送或修改消息体。

**Hook 超时**：发送服务 Hook 的默认超时为 5000ms。`after_build_message` 和 `before_send` 允许中止，`after_send` 不允许中止。

**Hook 消息格式**：Hook 收到的是序列化后的 `SessionMessage`，返回时也可以返回序列化消息。服务层会尝试反序列化返回消息，失败时记录警告并继续使用原消息。

**Hook 与 Platform IO 的边界**：Hook 可以改变发送参数和消息内容，但不应直接调用平台驱动。真正的发送仍然由 Platform IO 完成，这样插件链、legacy 旧链和适配器路由选择保持一致。

## 与 Maisaka 的交互

**推理引擎获取 LLM 客户端**：`MaisakaChatLoopService` 会按 `request_kind` 解析模型任务名和统计 request\_type，然后缓存 `LLMServiceClient`。不同子代理可以使用不同模型任务，例如 planner、replyer、expression\_selector 或 mid\_memory。

**启发式记忆注入**：`HeuristicMemoryInjector` 先用 `LLMServiceClient(task_name="utils")` 根据近期消息生成聊天印象，再调用 `memory_service.search()` 召回相关长期记忆。召回结果会格式化为一次性参考文本，合并给 Planner 或 Replyer。

**中期记忆摘要**：`mid_term.py` 使用 `LLMServiceClient(task_name="mid_memory", request_type="maisaka.mid_term_memory")` 生成中期聊天记录摘要。摘要结果会被转换成复杂消息，再插入 Maisaka 历史，供后续上下文使用。

**记忆查询工具**：`query_memory` 内置工具直接调用 `memory_service.search()`。当人物定向检索未命中且查询文本存在时，它会降级为普通关键词检索，并把结果包装成工具响应和 Replyer 记忆参考。

**回复发送工具**：`reply` 内置工具生成可见回复后，通过 `send_service._send_to_target_with_message()` 发送。调用时会传入 `sync_to_maisaka_history=True` 和 `maisaka_source_kind="guided_reply"`，确保发送结果同步回 Maisaka 历史。

**反馈纠错任务**：推理引擎在生成响应后，会调用 `memory_service.enqueue_feedback_task()` 把查询工具 ID、会话 ID 和时间戳交给 A\_memorix 反馈系统。这让长期记忆可以根据工具查询结果进行后续纠错。

**服务层隔离价值**：Maisaka 不需要理解 Platform IO 路由、A\_memorix 组件名、SQLModel 模型或统计缓存结构。它只通过服务层表达“要生成内容”、“要检索记忆”、“要发送回复”和“要记录统计”的意图。

## 典型调用链

**Chat 到 SendService**：Chat 管线完成推理或命令处理后，把回复文本或消息组件交给 SendService。SendService 构建出站消息，执行 `after_build_message` 和 `before_send`，通过 Platform IO 发送，再执行 `after_send`。

**Maisaka 到 LLMService**：Maisaka 的子代理按请求类型获取 `LLMServiceClient`，构造 prompt 或消息工厂，调用 `generate_response_with_messages()`。底层 Orchestrator 选择模型、构造请求、执行重试、记录 token，并返回统一结果。

**Maisaka 到 MemoryService**：启发式记忆、人物画像和内置查询工具都会调用 MemoryService。服务层把查询条件传给 A\_memorix，再把命中结果整理成业务对象，供推理引擎决定是否注入上下文。

**WebUI 到 StatisticsService**：WebUI 的 `/statistics/dashboard`、`/statistics/summary` 和 `/statistics/models` 路由调用 StatisticsService。服务层负责读取缓存、实时计算、补齐时间序列和返回前端 schema。

**MemoryAutomationService 到 MemoryService**：发送成功后，SendService 通知 MemoryAutomationService。自动化服务先入队，再在后台判断是否触发人物事实写回或聊天摘要写回，最终通过 MemoryService 写入长期记忆。

## 开发注意事项

**不要绕过服务层写业务逻辑**：如果 chat、maisaka 或 webui 需要新的业务动作，应优先新增或扩展服务层接口，而不是让上层直接调用底层客户端。

**不要把平台协议写进服务层**：SendService 可以继承 Platform IO 路由元数据，但不能知道具体平台如何发送消息。平台差异应留在 `platform_io` 和适配器。

**不要把 A\_memorix 细节暴露给推理层**：MemoryService 应继续屏蔽 A\_memorix 组件名、payload 结构和错误格式。Maisaka 只需要关心记忆是否可用，以及召回内容如何进入上下文。

**不要让 Hook 承担核心发送职责**：Hook 可以拦截和改写发送，但不应替代 SendService。发送成功后的落库、回执回填、记忆自动化通知和 Maisaka 历史同步仍由服务层统一管理。

**不要让统计服务变成数据库服务**：StatisticsService 可以读取数据库和汇总表，但通用 CRUD 仍属于 DatabaseService。统计服务应关注聚合口径、缓存和前端 schema。

**不要阻塞主消息管线**：MemoryAutomationService 使用异步队列处理写回。即使队列满或模型提取失败，也不应阻塞用户消息发送。

## 小结

服务层是 MaiBot 宿主进程中的业务协调层。它让 `chat`、`maisaka` 和 `webui` 用一致的方式完成消息发送、模型调用、记忆检索、数据访问和统计展示，同时把平台协议、模型客户端、数据库细节和 A\_memorix 内核隔离在底层。

当服务层保持清晰边界时，上层可以专注业务流程，底层可以独立演进，插件生态也能通过稳定包装获得能力，而不会直接依赖容易变化的内部实现。

---

---
url: /develop/architecture.md
---

# 架构设计

本文基于 code-map 快照编写，作为架构文档的导航中心。它把 MaiBot 的架构拆成 12 篇专题文档，并用 Runner/Worker 进程模型与 MainSystem 初始化流程串起主入口。

## 快速入口

**消息处理管线** ：从平台消息入站到出站发送的完整链路，详见 [消息管线](architecture/message-pipeline.md)。

**插件运行时架构** ：插件生命周期、Host/Runner 双进程通信、组件注册和 Hook 分发，详见 [插件开发文档](./plugin-dev/)、[生命周期](./plugin-dev/lifecycle.md)、[工具](./plugin-dev/tools.md)、[Hook](./plugin-dev/hooks.md)。

**Platform IO 架构** ：MaiBot 与适配器之间的发送、接收、路由、去重和出站跟踪，详见 [PlatformIO 驱动开发](./adapter-dev/platform-io.md)。

**事件总线（EventBus）** ：事件总线（EventBus）是 MaiBot 全系统通信中枢，提供发布/订阅模型，支持拦截型（同步顺序）和非拦截型（异步并发）两种事件处理器。详见 [事件总线架构](architecture/event-bus.md)。

**工具抽象层（Tool System）** ：工具抽象层（Tool System）统一管理四类工具来源：插件 @Tool、旧 @Action（自动转换）、MaiSaka 内置 Tool、MCP Tool，提供统一的 ToolProvider 接口。详见 [工具系统架构](architecture/tool-system.md)。

## Runner/Worker 进程模型

MaiBot 通过 `bot.py` 实现 Runner/Worker 双进程模型：

```mermaid
graph TD
    A[用户运行 bot.py] --> B{环境变量检查}
    B -->|MAIBOT_WORKER_PROCESS != 1| C[Runner 进程]
    B -->|MAIBOT_WORKER_PROCESS == 1| D[Worker 进程]
    C -->|subprocess.Popen| E[启动 Worker 子进程]
    E -->|返回码 42| C
    E -->|其他返回码| F[退出]
    D --> G[MainSystem 初始化]
    G --> H[调度异步任务]
```

* **Runner 进程**：守护进程，负责启动、监控 Worker 子进程。当 Worker 以退出码 42 退出时，Runner 会自动重新启动 Worker（热重启机制）。当 Runner 收到 Ctrl+C 信号时，会优雅终止 Worker。
* **Worker 进程**：实际执行业务逻辑的进程。设置环境变量 `MAIBOT_WORKER_PROCESS=1` 后进入 Worker 模式，执行 `MainSystem` 的初始化和任务调度。

## MainSystem 初始化流程

`MainSystem.initialize()` 通过 `await` 串行初始化各组件：

```mermaid
graph LR
    A[MainSystem.initialize] --> B[_init_components]
    B --> C[配置文件热重载启动]
    B --> D[注册记忆配置重载回调]
    B --> E[Prompt 模板加载]
    B --> F[异步任务管理器注册定时任务]
    B --> G[插件运行时启动]
    B --> H[A_memorix 长期记忆启动]
    B --> I[表情管理器加载]
    B --> J[聊天管理器初始化]
    B --> K[记忆自动化服务启动]
    B --> L[消息处理器注册]
    B --> M[ON_START 事件分发]
```

核心初始化顺序：

1. 启动配置文件热重载监视器
2. 注册 A\_memorix 配置重载回调（`register_config_reload_callback()`）
3. 加载 Prompt 模板
4. 注册定时任务（在线时间统计、统计输出、遥测心跳）
5. 启动插件运行时（`PluginRuntimeManager.start()`），建立双子进程（内置插件 + 第三方插件）
6. 启动 A\_memorix 长期记忆服务
7. 加载表情管理器
8. 初始化聊天管理器
9. 启动记忆自动化服务（`memory_automation_service.start()`）
10. 将 `ChatBot.message_process` 注册到消息 API 服务器
11. 触发 `ON_START` 事件（`event_bus.emit`）并分发到插件运行时（`bridge_event`）

`schedule_tasks()` 随后启动持续运行的服务：表情定期维护、消息 API 服务器、消息服务器。

## 新增架构入口

**[事件总线架构](architecture/event-bus.md)** ：事件总线（EventBus）是 MaiBot 全系统通信中枢，提供发布/订阅模型，支持拦截型（同步顺序）和非拦截型（异步并发）两种事件处理器。详见 [事件总线架构](architecture/event-bus.md)。

**[工具系统架构](architecture/tool-system.md)** ：工具抽象层统一管理插件 @Tool、旧 @Action（自动转换）、MaiSaka 内置 Tool、MCP Tool 四类工具来源，并通过 ToolProvider 接口接入推理与执行链路。详见 [工具系统架构](architecture/tool-system.md)。

**[服务层架构](architecture/service-layer.md)** ：服务层把 LLM 调用、记忆操作、发送消息、数据库访问和统计聚合等业务能力封装成可复用服务，避免上层模块直接耦合底层实现。详见 [服务层架构](architecture/service-layer.md)。

**[表达学习架构](architecture/expression-learning.md)** ：表达学习从对话中沉淀行为模式、俚语和表达偏好，让 MaiBot 的回复风格随时间适配用户语境。详见 [表达学习架构](architecture/expression-learning.md)。

**[表情系统内部架构](architecture/emoji-internals.md)** ：表情系统管理表情包的加载、匹配和生成，是消息语义理解与个性化回复的重要素材来源。详见 [表情系统内部架构](architecture/emoji-internals.md)。

**[MCP 集成架构](architecture/mcp-integration.md)** ：MCP 集成连接外部 MCP Server，把远程工具能力纳入统一 Tool System，扩展模型可调用的工具边界。详见 [MCP 集成架构](architecture/mcp-integration.md)。

**[Prompt 模板系统](architecture/prompt-templates.md)** ：Prompt 模板系统负责系统提示词、任务模板和运行参数的加载管理，影响推理引擎的上下文组织方式。详见 [Prompt 模板系统](architecture/prompt-templates.md)。

**[全局管理器架构](architecture/global-managers.md)** ：全局管理器集中维护跨模块共享的异步任务、配置状态和运行时服务，降低入口编排复杂度。详见 [全局管理器架构](architecture/global-managers.md)。

## 消息处理管线

消息处理管线是 MaiBot 从平台入站到最终发送的主链路，覆盖消息预处理、会话管理、命令执行、心流调度、Maisaka 推理、回复生成和 Platform IO 发送。详细阶段、数据结构、Hook 拦截点和出站流程请阅读 [消息管线](architecture/message-pipeline.md)。

## 插件运行时架构

插件运行时采用 Host 主进程加两个 Runner 子进程的双子进程隔离模型，通过 msgpack IPC 和 RPC 管理内置插件、第三方插件、组件注册和 Hook 分发。完整设计、开发约束和组件 API 请转至 [插件开发文档](./plugin-dev/)，重点阅读 [生命周期](./plugin-dev/lifecycle.md)、[工具](./plugin-dev/tools.md)、[命令](./plugin-dev/commands.md)、[Hook](./plugin-dev/hooks.md)、[事件处理器](./plugin-dev/event-handlers.md) 和 [消息网关](./plugin-dev/message-gateway.md)。

## Platform IO 架构

Platform IO 是 MaiBot 与平台适配器之间的中间层，负责 RouteKey 解析、发送和接收路由、驱动注册、入站去重和出站追踪。适配器实现与驱动接口请阅读 [PlatformIO 驱动开发](./adapter-dev/platform-io.md)。

## 本节文档索引

**基础域（Wave 1）** ：底层基础设施，提供通信、工具抽象和系统运行底座。
: [事件总线架构](architecture/event-bus.md) ：MaiBot 全系统事件通信中枢，提供发布/订阅模型和拦截型、非拦截型两类处理器。
: [工具系统架构](architecture/tool-system.md) ：四类工具来源的统一抽象层，通过 ToolProvider 接入插件、旧 Action、MaiSaka 内置工具和 MCP 工具。

**核心功能域（Wave 2）** ：消息处理、推理、记忆、WebUI 和服务封装构成 MaiBot 的主要业务链路。
: [消息管线](architecture/message-pipeline.md) ：从平台消息入站到出站发送的完整链路，包含预处理、会话、命令、心流、推理和发送 Hook。
: [Maisaka 推理引擎](architecture/maisaka-reasoning.md) ：MaiBot 的核心 AI 运行时，负责对话推理、节奏控制、LLM 请求和工具调用循环。
: [记忆系统（A-Memorix）](architecture/memory-system.md) ：MaiBot 的长期记忆子系统，负责持久化、嵌入、图谱检索、人物画像和记忆策略。
: [WebUI 内部机制](architecture/webui-internals.md) ：基于 FastAPI 的 Web 管理后端，覆盖认证、路由、WebSocket、插件运行时 IPC 和安全机制。
: [服务层架构](architecture/service-layer.md) ：封装 LLM 调用、记忆操作、发送消息、数据库访问和统计聚合等业务服务，供上层模块复用。

**辅助功能域（Wave 3）** ：增强能力模块，可按部署需求启用、替换或扩展。
: [表达学习架构](architecture/expression-learning.md) ：从对话中学习行为模式、俚语和表达偏好，为个性化回复提供持续更新的风格素材。
: [表情系统内部架构](architecture/emoji-internals.md) ：管理表情包加载、匹配和生成，为消息理解与回复生成提供视觉表达素材。
: [MCP 集成架构](architecture/mcp-integration.md) ：连接外部 MCP Server，将远程工具能力接入统一 Tool System。
: [Prompt 模板系统](architecture/prompt-templates.md) ：管理 Prompt 模板加载、参数化和运行时更新，支撑推理引擎的上下文组织。
: [全局管理器架构](architecture/global-managers.md) ：集中管理跨模块异步任务、配置状态和运行时服务，减少入口编排复杂度。

---

---
url: /manual/webui/memory-management.md
---

# 查看和管理记忆

MaiBot 会记住聊天内容，就像人的记忆一样。你可以在 WebUI 里查看和管理这些记忆。

## 什么是记忆？

想象 MaiBot 有一个"大脑"，会记录：

* 💬 **聊过什么** - 对话内容、重要信息
* 👥 **认识谁** - 用户的性格、喜好
* 🔗 **知识图谱** - 事物之间的关系
* 📚 **学习资料** - 你教它的知识

## 查看记忆

### 记忆总览

打开"记忆管理"页面，能看到：

* 总共记住多少东西
* 最近记住了什么
* 记忆分类统计

### 搜索记忆

想找特定内容？用搜索功能：

* 输入关键词，比如"游戏"、"美食"
* 按时间筛选，看某段时间的记忆
* 按用户筛选，看和谁的聊天记忆

### 知识图谱

像思维导图一样，显示概念之间的关系：

* 每个圆圈是一个概念（比如"原神"）
* 连线表示关系（比如"原神-游戏"）
* 点击圆圈看详细信息

## 管理记忆

### 添加记忆

可以手动教 MaiBot 新知识：

1. 点击"导入记忆"
2. 粘贴文本或上传文件
3. 选择处理方式
4. 开始导入

### 纠正记忆

发现画像或关系不准确时，可以通过对应管理入口修正：

1. 在人物画像中设置或删除手动 override
2. 在知识图谱中调整节点、关系或权重
3. 使用反馈纠错、删除恢复或重新导入来处理过时内容

普通段落正文目前不提供任意文本编辑入口；需要修正时，建议删除错误来源后重新导入，或通过反馈纠错机制处理。

### 删除记忆

不想记住某些内容？

* 单条删除：找到记忆，点击"删除"
* 批量删除：选择多条，一起删除
* 按来源删除：删除某个群聊的所有记忆

⚠️ **注意**：删除后进入回收站，还可以恢复

## 人物画像

MaiBot 会给每个用户建立"画像"：

* 性格特点（开朗、内向等）
* 兴趣爱好（游戏、动漫等）
* 聊天习惯（爱用表情包、说话方式等）

你可以：

* 查看自己的画像
* 修改不准确的描述
* 给好友添加备注

## 高级功能

### 记忆强化

让某些记忆更重要：

* 选中重要记忆
* 点击"强化记忆"
* 这些记忆就不容易被遗忘

### 永久记忆

特别重要的内容可以设为永久：

* 选择"永久记忆"
* 这些内容永远不会被自动清理

### 记忆调优

如果 MaiBot 记性不好，可以：

* 调整记忆参数
* 重新处理记忆
* 优化检索效果

### 运行时维护

WebUI 还提供运行时自检、自动保存开关、向量重建、段落向量回填、导入任务和删除操作记录等运维入口。

## 使用建议

### 日常维护

* 定期查看记忆，删除无用内容
* 发现错误及时纠正
* 重要信息可以手动强化

### 提升效果

* 教机器人专业知识，让它更聪明
* 完善人物画像，让对话更贴心
* 合理设置记忆容量，平衡性能和效果

## 常见问题

**Q: 记忆会保存多久？**
A: 默认长期保存。记忆演化会让旧关系权重逐渐衰减，低权重内容可能被标记为待裁剪；具体行为由 A\_Memorix 的记忆演化配置控制。

**Q: 记忆占空间吗？**
A: 文本记忆占用很小，放心使用

**Q: 可以导出记忆吗？**
A: 当前仅支持导出记忆调优配置，暂不支持完整记忆导出

**Q: 记忆会泄露隐私吗？**
A: 记忆数据默认存储在本地目录中。生成摘要、画像、纠错或向量时可能会调用你配置的模型服务，请根据自己的部署方式和模型提供商确认数据边界。

---

---
url: /manual/configuration/model-config.md
---

# 模型配置

`model_config.toml` 给麦麦配置"AI 大脑"——决定不同组件使用什么 LLM 模型，以及如何连接 API 服务商。

最少启动只需一个 LLM 模型和一个 API 提供商（`models` 和 `api_providers` 均非空）。完整功能还需 VLM 模型（看图）和嵌入模型（记忆搜索）。

## API 提供商

每个 `[[api_providers]]` 块定义一个 API 服务商。一个配置文件可以有多个提供商。

```toml
[[api_providers]]
name = "deepseek"                          # [必填] API 服务商名称，在 models 的 api_provider 中需使用这个命名
base_url = "https://api.deepseek.com/v1"   # [必填] API 服务商的 BaseURL
api_key = "your-api-key"                   # [必填] API 密钥。若 auth_type 为 none 则不需要
client_type = "openai"                     # [可选] 客户端类型：openai(默认) / google
auth_type = "bearer"                       # [可选] 鉴权方式：bearer(默认) / header / query / none
auth_header_name = "Authorization"         # [可选] 当 auth_type 为 header 时使用的请求头名称
auth_header_prefix = "Bearer"              # [可选] 当 auth_type 为 header 时的请求头前缀，留空表示直接发送原始密钥
auth_query_name = "api_key"                # [可选] 当 auth_type 为 query 时使用的查询参数名称
default_headers = {}                       # [可选] 所有请求默认附带的 HTTP Header
default_query = {}                         # [可选] 所有请求默认附带的查询参数
# organization = "org-xxxx"                # [可选] OpenAI 官方接口可选的 organization
# project = "proj-xxxx"                    # [可选] OpenAI 官方接口可选的 project
model_list_endpoint = "/models"            # [可选] 模型列表端点路径
reasoning_parse_mode = "auto"              # [可选] 推理内容解析模式：auto(默认) / native / think_tag / none
tool_argument_parse_mode = "auto"          # [可选] 工具参数解析模式：auto(默认) / strict / repair / double_decode
max_retry = 3                              # [可选] 最大重试次数
timeout = 60                               # [可选] API 调用超时，单位秒
retry_interval = 5                         # [可选] 重试间隔，单位秒
```

**要点：**

* **必填**：`name`（服务商名称）、`base_url`（端点地址）、`api_key`（密钥，`auth_type = "none"` 时除外）
* **鉴权**：默认 `bearer` 适用于绝大部分服务商。其他可选 `header` / `query` / `none`
* **客户端**：默认 `openai`。Google Gemini 用 `"google"`，见 [模型额外参数](./model-extra-params.md#gemini-原生-api)
* **超时与重试**：`timeout` 默认 60s，`max_retry` 默认 3 次，`retry_interval` 默认 5s
* 其余字段参见上方注释，均有合理默认值

## 模型

每个 `[[models]]` 块定义一个具体的 LLM 模型，关联到某个 API 提供商。

```toml
[[models]]
model_identifier = "deepseek-v4-flash"       # [必填] API 服务商提供的模型标识符
name = "deepseek-v4-flash"                   # [必填] 模型名称，在 model_task_config 中需使用这个命名
api_provider = "deepseek"                    # [必填] 对应 api_providers 中配置的服务商名称
price_in = 1.0                               # [可选] 输入价格，单位：元/M token
cache = false                                # [可选] 是否启用缓存计费
cache_price_in = 0.0                         # [可选] 缓存命中输入价格，仅 cache=true 时使用
price_out = 2.0                              # [可选] 输出价格，单位：元/M token
# temperature = 0.7                          # [可选] 模型级别温度，会覆盖任务配置中的 temperature
# max_tokens = 4096                          # [可选] 模型级别最大 token 数，会覆盖任务配置中的 max_tokens
force_stream_mode = false                    # [可选] 强制流式输出模式，模型不支持非流式输出时设为 true
visual = false                               # [可选] 是否为多模态模型（支持视觉输入）
extra_params = {}                            # [可选] 额外参数，详见 模型额外参数
```

**要点：**

* **必填**：`model_identifier`（API 标识符）、`name`（自定义名称）、`api_provider`（归属服务商）
* **价格**：`price_in` / `price_out` 用于统计，单位 元/百万 token。开启 `cache` 后可单独设置 `cache_price_in`
* **模型级覆盖**：`temperature` / `max_tokens` 可覆盖任务配置，不设则使用任务默认值
* **视觉**：`visual = true` 表示支持图像输入，用于 `vlm` 任务
* **`extra_params`**：服务商特有参数（思考模式、推理强度等），详见 [模型额外参数](./model-extra-params.md)

## 任务配置

根据任务特点给每个任务分配不同模型，实现最优表现和效率。

麦麦将模型调用分为三类角色：**Planner** 是战略核心，决定何时说话、调用哪些工具（需较强推理能力来调度 MCP 和工具链）；**Replyer** 负责将 Planner 收集的信息转化为最终回复文本，追求语言质量；其余辅助任务用低价 flash 模型追求速度。一次典型的「收到消息 → 发出回复」触发 3~6 次 LLM 调用。

::: code-group

```toml [replyer（智能模型）]
# [必填] 回复器：将 Planner 收集的信息转为最终回复文本。追求语言质量和表达风格，推荐 pro 模型 + 思考模式。
[model_task_config.replyer]
model_list = ["deepseek-v4-pro-think"]        # [必填] 模型名称列表
max_tokens = 4096                             # [可选] 最大输出 token 数
temperature = 1.0                             # [可选] 模型温度，0.3 保守 / 0.7 有创意 / 1.0 随机
slow_threshold = 120.0                        # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略：balance / random / sequential
hard_timeout = 240.0                          # [可选] 硬超时（秒）
```

```toml [planner（快模型）]
# [必填] 规划器：战略核心——决定何时说话、回复谁、调用哪些工具（MCP/插件）。需较强推理和 tool 调用能力。
[model_task_config.planner]
model_list = ["deepseek-v4-flash"]            # [必填] 模型名称列表
max_tokens = 8000                             # [可选] 最大输出 token 数
temperature = 0.7                             # [可选] 模型温度
slow_threshold = 12.0                         # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略
hard_timeout = 180.0                          # [可选] 硬超时（秒）
```

```toml [utils（快模型）]
# [必填] 组件模型：表情包分析、学习分析、取名、关系模块、情绪变化等。麦麦必须的模型。
[model_task_config.utils]
model_list = ["deepseek-v4-flash"]            # [必填] 模型名称列表
max_tokens = 4096                             # [可选] 最大输出 token 数
temperature = 0.5                             # [可选] 模型温度
slow_threshold = 15.0                         # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略
hard_timeout = 120.0                          # [可选] 硬超时（秒）
```

```toml [memory（长期记忆）]
# [可选] 长期记忆：记忆总结、抽取、写回等高质量任务（A_Memorix 子系统）。
# 默认 model_list 为空（不自动回退），未配置时调用方按需处理。
[model_task_config.memory]
model_list = []                               # [可选] 模型名称列表
max_tokens = 8192                             # [可选] 最大输出 token 数
temperature = 0.5                             # [可选] 模型温度
slow_threshold = 30.0                         # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略
hard_timeout = 240.0                          # [可选] 硬超时（秒）
```

```toml [mid_memory（中期摘要）]
# [可选] 中期摘要：上下文裁切时将历史聊天压缩为摘要。留空时自动回退到 planner。
[model_task_config.mid_memory]
model_list = []                               # [可选] 模型名称列表（→回退 planner）
max_tokens = 8000                             # [可选] 最大输出 token 数
temperature = 0.7                             # [可选] 模型温度
slow_threshold = 12.0                         # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略
hard_timeout = 180.0                          # [可选] 硬超时（秒）
```

```toml [timing_gate（节奏控制）]
# [可选] 节奏控制：独立判断是否该在此时说话。留空时自动回退到 planner。
[model_task_config.timing_gate]
model_list = []                               # [可选] 模型名称列表（→回退 planner）
max_tokens = 4096                             # [可选] 最大输出 token 数
temperature = 0.3                             # [可选] 模型温度
slow_threshold = 12.0                         # [可选] 慢请求阈值（秒）
selection_strategy = "random"                 # [可选] 模型选择策略
hard_timeout = 120.0                          # [可选] 硬超时（秒）
```

```toml [learner（学习）]
# [可选] 学习模型：表达方式学习和黑话学习。留空时自动回退到 utils。
[model_task_config.learner]
model_list = []                               # [可选] 模型名称列表（→回退 utils）
max_tokens = 4096                             # [可选] 最大输出 token 数
hard_timeout = 120.0                          # [可选] 硬超时（秒）
```

```toml [emoji（表情包选择）]
# [可选] 表情包选择：从候选表情包中选出合适的一张发送。
# 选择优先级：emoji 有模型→用 emoji，planner 全视觉→用 planner，否则→用 vlm
[model_task_config.emoji]
model_list = []                               # [可选] 模型名称列表
max_tokens = 4096                             # [可选] 最大输出 token 数
hard_timeout = 120.0                          # [可选] 硬超时（秒）
```

```toml [vlm（看图）]
# [强烈建议] 看图说话：理解图片内容。需 visual=true 的多模态模型。
[model_task_config.vlm]
model_list = ["qwen-vl"]                      # [必填] 模型名称列表，需 visual=true 的多模态模型
max_tokens = 4096                             # [可选] 最大输出 token 数
hard_timeout = 240.0                          # [可选] 硬超时（秒）
```

```toml [voice（语音识别）]
# [可选] 语音识别：语音转文字。
[model_task_config.voice]
model_list = []                               # [可选] 模型名称列表
max_tokens = 4096                             # [可选] 最大输出 token 数
hard_timeout = 120.0                          # [可选] 硬超时（秒）
```

```toml [embedding（嵌入模型）]
# [强烈建议] 嵌入模型：生成文本向量，用于长期记忆的语义搜索。
# 推荐专门的嵌入模型（如 text-embedding-3-small）。未配置时记忆搜索不可用。
[model_task_config.embedding]
model_list = ["text-embedding-3-small"]       # [必填] 模型名称列表，推荐专门的嵌入模型
max_tokens = 4096                             # [可选] 最大输出 token 数
hard_timeout = 60.0                           # [可选] 硬超时（秒）
```

:::

**要点：**

* **三个必配**：`replyer`、`planner`、`utils` 配好即可运行，其余留空自动回退
* **Planner 是战略核心**：决定何时说话、调用哪些工具（MCP/插件），需要一定的推理能力，建议用能力均衡的模型
* **Replyer 追求语言质量**：将 Planner 收集的信息转为最终回复，推荐 pro 模型 + 思考模式
* **视觉**：`vlm` 需 `visual = true` 的多模态模型，推荐 `qwen-vl`
* **嵌入**：`embedding` 推荐专门嵌入模型（如 `text-embedding-3-small`），未配置则记忆搜索不可用
* 模型配置中的 `temperature` / `max_tokens` 会覆盖此处设置

### 回退规则

部分任务的 `model_list` 为空时，自动复用其他任务：

```
         ┌──────────┐
         │  planner │◄──── mid_memory（留空时回退）
         │          │◄──── timing_gate（留空时回退）
         └──────────┘
              ▲
              │
         ┌──────────┐
         │  utils   │◄──── learner（留空时回退）
         └──────────┘

memory · emoji · vlm · voice · embedding → 留空不自动回退，调用方会跳过或报错

emoji 特殊逻辑：emoji 有模型→用 emoji，planner 全视觉→用 planner，否则→用 vlm
```

## 下一步

* 模型高级参数（思考模式、推理强度）：[模型额外参数](./model-extra-params.md)
* 配置机器人：看 [Bot 配置](./bot-config.md)
* 连接 QQ：[NapCat 适配器](../adapters/napcat.md)
* 管理 WebUI：[WebUI 配置管理](../webui/config-management.md)

---

---
url: /manual/configuration/model-extra-params.md
---

# 模型额外参数 (extra\_params)

`model_config.toml` 中每个模型都可以设置 `extra_params` 字段，用于在 API 调用时传递服务商特有的参数。最常见的用途是控制大模型的思考模式和推理强度。

`extra_params` 不会以原样整体发送给服务商，实际请求前客户端会按规则拆分转换：

* **`headers`** — 作为请求头传入
* **`query`** — 作为 URL 查询参数传入
* **`body`** — 合并到请求体
* **其他普通键** — 作为请求体额外字段传入（OpenAI SDK 的 `extra_body`）

当 `client_type = "google"` 时，`extra_params` 不按上述规则拆分，而是由 Gemini 客户端按自身支持的字段筛选和映射到 `GenerateContentConfig`。

***

# 思考与非思考模式

很多大模型支持"思考模式"，让模型在回答前先进行深度推理，从而提升复杂问题的回答质量。MaiBot 支持两种 API 体系，配置方式不同：

* **OpenAI 兼容 API**（`client_type = "openai"`）：DeepSeek、OpenAI、阿里云百炼等
* **Gemini 原生 API**（`client_type = "google"`）：Google Gemini 系列

## OpenAI 兼容 API

`thinking` 对象是多家服务商通用的思考模式开关，**DeepSeek**、**Kimi（月之暗面）**、**GLM（智谱）** 等均采用此格式，配置方式完全一致。`reasoning_effort` 为可选参数，不填则使用默认强度。部分第三方平台（如阿里云百炼/DashScope）则使用 `enable_thinking` 参数格式：

::: code-group

```toml [官方（思考）]
[[models]]
name = "deepseek-v4-flash-think"
model_identifier = "deepseek-v4-flash"
api_provider = "deepseek"
visual = false
extra_params = {thinking = {type = "enabled"}, reasoning_effort = "high"}
```

```toml [官方（非思考）]
[[models]]
name = "deepseek-v4-flash-nothink"
model_identifier = "deepseek-v4-flash"
api_provider = "deepseek"
visual = false
extra_params = {thinking = {type = "disabled"}}
```

```toml [官方（极限）]
[[models]]
name = "deepseek-v4-flash-max"
model_identifier = "deepseek-v4-flash"
api_provider = "deepseek"
visual = false
extra_params = {thinking = {type = "enabled"}, reasoning_effort = "max"}
```

```toml [第三方（思考）]
[[models]]
name = "deepseek-v4-flash-think"
model_identifier = "deepseek-v4-flash"
api_provider = "dashscope"
visual = false
extra_params = {enable_thinking = true}
```

```toml [第三方（非思考）]
[[models]]
name = "deepseek-v4-flash-nothink"
model_identifier = "deepseek-v4-flash"
api_provider = "dashscope"
visual = false
extra_params = {enable_thinking = false}
```

:::

**要点：**

* DeepSeek V4 的 `reasoning_effort` 仅支持 `high`（默认）和 `max`（极限推理）两个有效等级。`low`/`medium` 映射为 `high`，`xhigh` 映射为 `max`
* 对比 OpenAI：OpenAI 的 `reasoning_effort` 支持 6 个独立等级（`none`/`minimal`/`low`/`medium`（默认）/`high`/`xhigh`），各自独立生效，与 DeepSeek V4 只有 2 个有效等级不同。注意 `o1-mini` 不支持此参数
* **多轮对话规则**：如果思考轮次没有工具调用，不需要把思考内容回传；如果有工具调用，必须回传
* **限制**：思考模式下 `temperature` 和 `top_p` 会被静默忽略，`tool_choice` 会导致 400 错误
* 第三方平台（如阿里云百炼/DashScope）使用 `enable_thinking`（布尔值）控制思考模式，与原生 `thinking` 对象写法不同。配置前请确认你使用的平台支持哪种参数格式

## Gemini 原生 API

当 `client_type = "google"` 时，`extra_params` 不按 OpenAI 的 `headers/query/body` 规则处理，而是由 Gemini 客户端按自身支持的字段筛选和映射到 `GenerateContentConfig`。

### Gemini 2.5（thinking\_budget）

Gemini 2.5 系列通过 `thinking_budget`（整数）控制思考预算：

::: code-group

```toml [开启思考]
[[models]]
name = "gemini-2.5-flash-think"
model_identifier = "gemini-2.5-flash"
api_provider = "google-gemini"
visual = true
client_type = "google"
extra_params = {thinking_config = {thinking_budget = 4096, include_thoughts = true}}
```

```toml [关闭思考]
[[models]]
name = "gemini-2.5-flash-nothink"
model_identifier = "gemini-2.5-flash"
api_provider = "google-gemini"
visual = true
client_type = "google"
extra_params = {thinking_config = {thinking_budget = 0}}
```

```toml [自动预算]
[[models]]
name = "gemini-2.5-pro-think"
model_identifier = "gemini-2.5-pro"
api_provider = "google-gemini"
visual = true
client_type = "google"
extra_params = {thinking_config = {thinking_budget = -1, include_thoughts = true}}
```

:::

**要点：**

* `thinking_budget`：`-1` = 自动分配，`0` = 关闭思考，`N` = 指定 token 预算
* `include_thoughts`：是否在响应中包含思考过程
* 已知问题：Flash Preview 04-17 版本设置 `thinking_budget = 0` 可能失败

### Gemini 3.0+（thinking\_level）

Gemini 3.0 及更新版本通过 `thinking_level`（枚举值）控制思考强度：

::: code-group

```toml [高强度思考]
[[models]]
name = "gemini-3-flash-high"
model_identifier = "gemini-3-flash"
api_provider = "google-gemini"
visual = true
client_type = "google"
extra_params = {thinking_config = {thinking_level = "high", include_thoughts = true}}
```

```toml [低强度思考]
[[models]]
name = "gemini-3-flash-low"
model_identifier = "gemini-3-flash"
api_provider = "google-gemini"
visual = true
client_type = "google"
extra_params = {thinking_config = {thinking_level = "low", include_thoughts = true}}
```

:::

**要点：**

* `thinking_level` 可选：`minimal`、`low`、`medium`、`high`
* 不要同时使用 `thinking_budget` 和 `thinking_level`，会导致 400 错误
* 多轮对话中需要使用 thought signatures 保持上下文

### Gemini 总览

* **Gemini 2.5** — 通过 `thinking_budget` 控制思考预算，值域：`-1`（自动）/ `0`（关闭）/ `N`（预算），关闭方式为 `budget = 0`。budget 和 level 不可混用
* **Gemini 3.0+** — 通过 `thinking_level` 控制思考等级，值域：`minimal` / `low` / `medium` / `high`，关闭方式为不设置或 `minimal`。不支持 token 级预算控制

Gemini 2.5 使用 token 数量间接控制强度，`-1` 为自动分配。Gemini 3.0+ 使用枚举值直接指定等级。

> Google API 在国内无法直接访问，需要代理。

# 自定义 HTTP 请求

`extra_params` 支持三个特殊 key 来精确控制 API 请求：

* **`headers`** — 添加 HTTP 请求头，如 `{headers = {"X-Custom" = "value"}}`
* **`query`** — 添加 URL 查询参数，如 `{query = {"key" = "value"}}`
* **`body`** — 其中的字段与其他普通键一起进入请求体，仅用于在配置中按用途分组

::: warning 注意
`body` 并不创建独立的请求通道。`body` 内的字段和 `headers`/`query` 之外的**所有普通键**会合并后一起发送到请求体中。
:::

例如：

```toml
[[models]]
name = "custom-model"
model_identifier = "custom-model-v1"
api_provider = "custom"
visual = false
extra_params = {
  headers = {"X-API-Version" = "2024-06", "X-Priority" = "high"},
  query = {version = "2024-01-01"},
  body = {metadata = {source = "maibot"}},
  enable_thinking = false
}
```

客户端拆分后的实际效果：

| 来源 | 目标 | 内容 |
|------|------|------|
| `headers` | HTTP 请求头 | `X-API-Version: 2024-06`, `X-Priority: high` |
| `query` | URL 查询参数 | `?version=2024-01-01` |
| `body` 内字段 + 其他普通键 | 请求体 JSON | `{"metadata": {"source": "maibot"}, "enable_thinking": false}` |

所以 `extra_params = {enable_thinking = "false"}` 等价于 `extra_params = {body = {enable_thinking = "false"}}`，都会把 `enable_thinking` 作为请求体 JSON 字段发给服务商，而不是发送嵌套的 `{"extra_params": {"enable_thinking": "false"}}`。

# 高级鉴权配置

* **`auth_header_name`** — Header 鉴权名称。默认 `Authorization`
* **`auth_header_prefix`** — Header 鉴权前缀。默认 `Bearer`
* **`auth_query_name`** — Query 鉴权参数名。默认 `api_key`

# 其他高级参数

## 模型级参数覆盖

* **`temperature`** — 模型级温度，覆盖任务配置。可选，如 `0.7`
* **`max_tokens`** — 模型级最大 token，覆盖任务配置。可选，如 `4096`
* **`force_stream_mode`** — 强制流式输出，不支持非流式时设为 `true`。默认关闭
* **`extra_params`** — 额外参数字典。默认为空

## 优先级说明

`temperature` 和 `max_tokens` 可以写在 `extra_params` 中作为模型级默认值，但更推荐使用模型配置里的同名独立字段：

```toml
temperature = 0.7
max_tokens = 4096
```

这样配置意图更清楚，也能避免和服务商请求体中的同名字段混淆。

当多处存在同名参数时，生效优先级为：

1. 调用方本次请求显式传入的值
2. 当前模型配置里的独立字段（如 `temperature`、`max_tokens`）
3. 当前模型 `extra_params` 中的同名字段
4. 当前任务配置中的默认值

## API 提供商高级配置

* **`default_headers`** — 默认 HTTP 头。默认为空
* **`default_query`** — 默认查询参数。默认为空
* **`organization`** — OpenAI 组织（可选）。默认无
* **`project`** — OpenAI 项目（可选）。默认无
* **`model_list_endpoint`** — 模型列表端点。默认 `/models`
* **`reasoning_parse_mode`** — 推理内容解析模式。默认 `auto`
* **`tool_argument_parse_mode`** — 工具参数解析模式。默认 `auto`

## 运行时配置

* **`timeout`** — 超时时间。推荐 60 秒
* **`max_retry`** — 失败重试次数。推荐 3 次
* **`retry_interval`** — 重试间隔。推荐 5 秒

# 常用参数速查

## OpenAI 兼容 API

* **`thinking`** — 思考模式控制，含 `type`（enabled/disabled）。适用 DeepSeek
* **`reasoning_effort`** — 推理强度等级（DeepSeek V4 仅 high/max，OpenAI 6 级）。适用 DeepSeek, OpenAI
* **`enable_thinking`** — 开启思考模式。适用阿里云百炼
* **`headers`** — 自定义 HTTP 请求头。适用全部
* **`query`** — 自定义 URL 查询参数。适用全部
* **`body`** — 自定义请求体字段。适用全部

## Gemini 原生 API

* **`thinking_config`** — 思考配置，含 `thinking_budget` 或 `thinking_level`。适用 Gemini 全系
* **`thinking_budget`** — 思考预算（-1 自动 / 0 关闭 / N 指定）。适用 Gemini 2.5
* **`thinking_level`** — 思考等级（minimal/low/medium/high）。适用 Gemini 3.0+
* **`include_thoughts`** — 响应是否包含思考过程。适用 Gemini 全系

> 参数会原样传递给 LLM API，务必与你使用的服务商文档一致，否则可能导致调用失败。

***

**更多信息请参考各服务商官方文档：**

* [DeepSeek API 文档](https://api-docs.deepseek.com/guides/thinking_mode)
* [OpenAI 推理指南](https://platform.openai.com/docs/guides/reasoning)
* [Google Gemini 思考配置](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking)
* [阿里云百炼 API 参考](https://help.aliyun.com/zh/model-studio/developer-reference/)
* [Kimi 思考模式指南](https://platform.kimi.com/docs/guide/use-kimi-k2-thinking-model)
* [GLM 思考模式文档](https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode)

---

---
url: /manual/features/message-pipeline.md
---

# 消息是怎么处理的 📨

你有没有想过，当你@MaiBot 或者跟它聊天时，它到底是怎么处理你的消息的呢？让我们用简单的话来解释这个过程。

## 一句话版本

**你发消息 → 机器人想想 → 给你回复**

就这么简单！但中间其实有很多有趣的小步骤。

## 详细流程（用大白话讲）

### 1️⃣ 收到消息

当你在群里发消息时：

* 如果是@机器人，它肯定会看到
* 如果没@它，它也会偷偷看看，想想要不要插话
* 不管是文字、图片还是表情包，它都能收到

### 2️⃣ 先看看要不要理你

机器人会先快速判断：

* 这是不是垃圾消息？（有屏蔽词就过滤掉）
* 这是不是命令？（比如"!help"这种）
* 如果是命令，就先处理命令

### 3️⃣ 进入思考模式

如果不是命令，机器人就开始认真思考：

* 看看你们之前在聊什么
* 回忆一下你这个人的特点
* 想想现在是不是适合插话的时机

### 4️⃣ 决定要不要回复

这一步很关键！机器人会考虑：

* 现在聊天氛围怎么样？
* 我说话会不会打扰到你们？
* 我说点什么比较合适？

有时候它会选择：

* **立即回复** - 觉得该说话了
* **等等再说** - 觉得时机不合适
* **保持沉默** - 决定还是不插话了

### 5️⃣ 组织语言

如果决定回复，机器人会：

* 想想用什么语气说话
* 回忆你们群的说话风格
* 选择合适的表情包（如果需要）
* 组织一段自然的回复

### 6️⃣ 发送回复

最后就是把想好的话发出来啦！

## 举个实际例子 🌰

**场景**：群里在讨论周末去哪里玩

```
小明：周末想去爬山，有人一起吗？
小红：我想去！不过天气预报说可能下雨
小刚：那要不改去商场？
（这时候你@了MaiBot）
你：@MaiBot 你觉得呢？

[机器人收到消息，开始思考...]

MaiBot：我觉得爬山挺好的啊！不过要看天气，
       如果下雨的话商场确实更稳妥～
       你们可以准备个Plan B，这样更灵活 😊
```

**机器人思考过程**：

1. 收到@消息 → "有人问我意见"
2. 看上下文 → "他们在讨论周末活动"
3. 看聊天气氛 → "挺轻松的，可以参与"
4. 决定回复 → "给点实用建议"
5. 组织语言 → "用轻松语气，加个表情"
6. 发送回复 → "完成！"

## 什么时候会回复你？

### 肯定会回复的情况：

* 你@了机器人
* 你直接跟它说话
* 它觉得你的消息是问它的

### 可能会回复的情况：

* 群里聊得热火朝天，气氛很好
* 聊到它感兴趣的话题
* 它觉得自己有有用的信息可以分享

### 通常不会回复的情况：

* 群里在讨论很私人的事情
* 气氛比较严肃或紧张
* 它觉得自己插话不合适

## 回复速度有多快？

这个要看情况：

* **秒回**：有时候想得快，立马就回
* **等等**：有时候要思考一会儿
* **很久才回**：可能在忙别的，或者真的在认真思考

就像真人一样，它也有自己的"思考时间"。

## 为什么有时候不回复？

机器人不回复通常是因为：

1. **觉得不该说话** - 像真人一样懂礼貌
2. **在思考中** - 还没想好怎么说
3. **网络问题** - 技术原因（很少见）
4. **被设置成了安静模式** - 管理员让它少说话

## 想更深入了解？

如果你对技术细节感兴趣：

* [看看 MaiBot 是怎么思考的 →](./maisaka-reasoning.md)
* [了解它的记忆系统 →](./memory-system.md)
* [看它怎么学习说话风格 →](./learning.md)

记住，MaiBot 的目标不是最快回复，而是最自然地参与对话。它想成为一个真正的聊天伙伴，而不是一个冷冰冰的自动回复机器。

---

---
url: /develop/architecture/message-pipeline.md
---

# 消息管线

MaiBot 的消息处理管线是从入站接收到出站发送的完整链路。本文详述管线各阶段的内部机制、数据结构和 Hook 拦截点。

## 整体流程

```mermaid
flowchart TD
    A[平台消息到达] --> B[maim-message MessageServer]
    B --> C[ChatBot.message_process]
    C --> D[MessageBase → SessionMessage 反序列化]
    D --> E["Hook: chat.receive.before_process"]
    E -->|aborted| F[中止处理]
    E -->|继续| G["SessionMessage.process() 预处理"]
    G --> H["Hook: chat.receive.after_process"]
    H -->|aborted| F
    H -->|继续| I[过滤器：ban_words / ban_regex]
    I -->|命中| F
    I -->|通过| J["ChatManager.register_message()"]
    J --> K["ChatManager.get_or_create_session()"]
    K --> L{命中命令?}
    L -->|是| M["Hook: chat.command.before_execute"]
    M -->|aborted| N[命令被中止]
    M -->|继续| O[命令执行 RPC]
    O --> P["Hook: chat.command.after_execute"]
    P --> Q{继续处理?}
    Q -->|否| R[返回命令结果]
    Q -->|是| S[HeartFlow 心流处理]
    L -->|否| S
    S --> T["HeartFCMessageReceiver.process_message()"]
    T --> U["HeartflowManager.get_or_create_heartflow_chat()"]
    U --> V["MaisakaHeartFlowChatting.register_message()"]
    V --> W[Maisaka 推理引擎]
    W --> X[回复生成]
    X --> Y[SendService]
    Y --> Z["Hook: send_service.after_build_message"]
    Z -->|aborted| AA[取消发送]
    Z -->|继续| AB["Hook: send_service.before_send"]
    AB -->|aborted| AA
    AB -->|继续| AC["PlatformIOManager.send_message()"]
    AC --> AD[适配器驱动发送]
    AD --> AE["Hook: send_service.after_send"]
```

## 消息入站与反序列化

### 入口：`ChatBot.message_process()`

源码位置：`src/chat/message_receive/bot.py`

消息通过 maim-message `MessageServer` 到达后，调用 `ChatBot.message_process(message_data)` 进入主链路：

```python
async def message_process(self, message_data: Dict[str, Any]) -> None:
    # 1. 确保后台任务已启动
    await self._ensure_started()
    # 2. 规范化 group_id / user_id 为字符串
    # 3. 反序列化
    maim_raw_message = MessageBase.from_dict(message_data)
    message = SessionMessage.from_maim_message(maim_raw_message)
    await self.receive_message(message)
```

### `SessionMessage` 结构

源码位置：`src/chat/message_receive/message.py`

`SessionMessage` 继承自 `MaiMessage`，是管线中流转的核心消息对象：

* **`message_id`** `str` — 消息唯一 ID
* **`platform`** `str` — 来源平台标识
* **`session_id`** `str` — 会话 ID（由 `SessionUtils.calculate_session_id()` 计算）
* **`processed_plain_text`** `str` — 经过预处理的纯文本
* **`message_info`** `MessageInfo` — 包含 `user_info`、`group_info`、`additional_config`
* **`raw_message`** `MessageSequence` — 原始消息组件序列
* **`is_at`** `bool` — 是否 @ 了 bot
* **`is_mentioned`** `bool` — 是否提及了 bot
* **`is_command`** `bool` — 是否命中命令
* **`is_notify`** `bool` — 是否为通知消息
* **`timestamp`** `datetime` — 消息时间戳

### `SessionMessage.process()` 预处理

将原始消息组件转化为纯文本，支持以下组件类型：

* **`TextComponent`** — 直接返回文本
* **`ImageComponent`** — 调用 `image_manager.get_image_description()` 生成 `[图片：描述]`
* **`EmojiComponent`** — 调用 `emoji_manager.get_emoji_description()` 生成 `[表情包：描述]`
* **`AtComponent`** — 解析目标用户名，生成 `@昵称`
* **`VoiceComponent`** — 调用 `get_voice_text()` 转写为 `[语音：转录文本]`
* **`ReplyComponent`** — 查找原消息内容，生成 `[回复了XXX的消息：内容]`
* **`ForwardNodeComponent`** — 递归处理转发节点，生成 `【合并转发消息：...】`

入站主链调用时使用轻量模式（`enable_heavy_media_analysis=False, enable_voice_transcription=False`），图片/表情包的二进制数据延迟到 Maisaka 需要时按需回填。

## Hook 拦截链

### chat.receive.before\_process

在 `SessionMessage.process()` 之前触发，可拦截或改写原始消息。

* **注册位置**：`src/chat/message_receive/bot.py` `register_chat_hook_specs()`
* **默认超时**：8000ms
* **允许中止**：是
* **允许改写**：是

参数 Schema：

```json
{
  "message": { "type": "object", "description": "当前入站消息的序列化 SessionMessage" }
}
```

### chat.receive.after\_process

在消息完成预处理后触发，可改写文本、消息体或中止后续链路。

* **默认超时**：8000ms
* **允许中止**：是
* **允许改写**：是

### chat.command.before\_execute

在命令匹配成功、实际执行前触发。

* **默认超时**：5000ms
* **允许中止**：是
* **允许改写**：是

参数包含：`message`、`command_name`、`plugin_id`、`matched_groups`

### chat.command.after\_execute

在命令执行结束后触发，可调整返回文本和是否继续主链处理。

* **默认超时**：5000ms
* **允许中止**：否
* **允许改写**：是

参数包含：`message`、`command_name`、`plugin_id`、`matched_groups`、`success`、`response`、`intercept_message_level`、`continue_process`

### send\_service.after\_build\_message

在出站 `SessionMessage` 构建完成后触发，可改写消息体或取消发送。

* **注册位置**：`src/services/send_service.py` `register_send_service_hook_specs()`
* **默认超时**：5000ms
* **允许中止**：是

### send\_service.before\_send

在真正调用 Platform IO 发送前触发，最终拦截点。

* **默认超时**：5000ms
* **允许中止**：是

### send\_service.after\_send

在发送流程结束后触发，仅观察用途。不允许中止或改写。

## 消息过滤

源码位置：`src/chat/message_receive/bot.py` `receive_message()` 中

过滤在 `chat.receive.after_process` Hook 之后执行：

1. **屏蔽词过滤**（`MessageUtils.check_ban_words()`）：检查 `processed_plain_text` 是否包含配置中的 `ban_words`
2. **正则过滤**（`MessageUtils.check_ban_regex()`）：检查是否匹配配置中的 `ban_regex` 模式

命中过滤规则后，消息直接丢弃，不会进入后续任何阶段。

## 会话管理

源码位置：`src/chat/message_receive/chat_manager.py`

### ChatManager

单例 `chat_manager`，管理所有聊天会话。

```python
class ChatManager:
    sessions: Dict[str, BotChatSession]    # session_id → BotChatSession
    last_messages: Dict[str, SessionMessage]  # session_id → 最近一条消息
```

### Session ID 计算

由 `SessionUtils.calculate_session_id()` 根据以下参数生成：

* `platform`：平台标识
* `user_id`：用户 ID
* `group_id`：群 ID（可选）
* `account_id`：平台账号 ID（可选，从 `additional_config` 提取）
* `scope`：路由作用域（可选，从 `additional_config` 提取）

### BotChatSession

继承自 `MaiChatSession`，扩展了：

* **`context`** `SessionContext` — 会话上下文（含最近消息、模板名）

* **`accept_format`** `List[str]` — 可接受的消息格式列表

* **`update_active_time()`** — 更新最后活跃时间

* **`set_context(message)`** — 设置会话上下文

* **`check_types(types)`** — 检查消息是否符合可接受类型

## 命令处理

源码位置：`src/chat/message_receive/bot.py` `_process_commands()`

命令处理流程：

1. `component_query_service.find_command_by_text(text)` 在插件组件注册表中查找匹配命令
2. 命中后触发 `chat.command.before_execute` Hook
3. 调用命令执行器 `command_executor()`，传入 `message`、`plugin_config`、`matched_groups`
4. 触发 `chat.command.after_execute` Hook
5. 根据 `intercept_message_level` 决定是否继续后续处理
   * `intercept_message_level == 0`：继续处理（消息会同时走 HeartFlow）
   * `intercept_message_level > 0`：停止处理

被命令拦截的消息会写入数据库（`MessageUtils.store_message_to_db()`），但不再进入 HeartFlow。

## HeartFlow 心流处理

源码位置：`src/chat/heart_flow/`

### HeartFCMessageReceiver

源码位置：`src/chat/heart_flow/heartflow_message_processor.py`

```python
class HeartFCMessageReceiver:
    async def process_message(self, message: SessionMessage):
        # 1. 跳过通知消息
        # 2. 存储消息到数据库
        # 3. 获取或创建 HeartFlow Chat
        # 4. 注册消息到 Maisaka 运行时
        # 5. 注册用户到 Person 信息库
```

### HeartflowManager

源码位置：`src/chat/heart_flow/heartflow_manager.py`

管理 session 级别的 `MaisakaHeartFlowChatting` 实例：

```python
class HeartflowManager:
    heartflow_chat_list: Dict[str, MaisakaHeartFlowChatting]
    _chat_create_locks: Dict[str, asyncio.Lock]

    async def get_or_create_heartflow_chat(self, session_id: str) -> MaisakaHeartFlowChatting
    def adjust_talk_frequency(self, session_id: str, frequency: float) -> None
```

使用双重检查锁（double-checked locking）确保同一会话只创建一个 Maisaka 运行时实例。

## 出站发送

源码位置：`src/services/send_service.py`

`SendService` 构建出站消息的流程：

1. 构建 `MessageSending` 对象（`SessionMessage` + 目标信息）
2. 触发 `send_service.after_build_message` Hook
3. 计算打字时间（`calculate_typing_time()`）
4. 触发 `send_service.before_send` Hook
5. 通过 `PlatformIOManager.send_message()` 路由到平台驱动
6. 触发 `send_service.after_send` Hook
7. 发送成功的消息写入数据库并同步到 Maisaka 历史记录

## 内置 Hook 汇总

所有内置 Hook 由 `hook_catalog.py` 统一注册。

> 完整的 Hook 目录及其参数说明请参阅 [Hook 处理器](../plugin-dev/hooks)。本文仅介绍管线中 Hook 的位置和作用。

## 数据流图

```mermaid
graph LR
    subgraph 入站
        A[平台适配器] -->|MessageBase| B[SessionMessage]
    end
    subgraph 预处理
        B --> C[Hook: before_process]
        C --> D[process 预处理]
        D --> E[Hook: after_process]
        E --> F[过滤检查]
    end
    subgraph 分发
        F --> G[命令匹配]
        G -->|命中| H[命令执行]
        G -->|未命中| I[HeartFlow]
        H -->|继续| I
    end
    subgraph 推理
        I --> J[Maisaka 运行时]
        J --> K[Timing Gate]
        K --> L[Planner]
        L --> M[工具执行]
    end
    subgraph 出站
        M --> N[SendService]
        N --> O[Platform IO]
        O --> P[适配器驱动发送]
    end
```

---

---
url: /develop/plugin-dev/message-gateway.md
---

# 消息网关

`@MessageGateway` 装饰器用于声明消息网关组件，实现 MaiBot 与外部消息平台（如 QQ、Discord 等）的双向消息路由。消息网关是平台适配器的核心组件，负责出站消息发送和入站消息注入。

## 装饰器签名

```python
from maibot_sdk import MessageGateway

@MessageGateway(
    route_type: str,             # 路由类型：send / receive / duplex（必填）
    *,
    name: str = "",              # 组件名，留空时使用方法名
    description: str = "",       # 组件描述
    platform: str = "",          # 平台名称（如 qq、discord）
    protocol: str = "",          # 协议或接入方言名称
    account_id: str = "",        # 账号 ID / self_id
    scope: str = "",             # 路由作用域
    **metadata,                  # 额外元数据
)
```

## 路由类型

* **`"send"`** → `MessageGatewayRouteType.SEND` — 出站：Host → 插件 → 外部平台
* **`"receive"`** → `MessageGatewayRouteType.RECEIVE` — 入站：外部平台 → 插件 → Host
* **`"duplex"`** → `MessageGatewayRouteType.DUPLEX` — 双向：同时支持出站和入站

::: tip 别名支持
`route_type` 也接受 `"recv"` 和 `"recive"` 作为 `"receive"` 的别名。
:::

## ctx.gateway 能力代理

* `await self.ctx.gateway.route_message(gateway_name, message_dict, route_metadata=None, ...)` — 注入入站消息到 Host
* `await self.ctx.gateway.update_state(gateway_name, ready, platform="", account_id="", scope="", metadata=None)` — 上报网关状态

### 状态管理

* 只有 `ready=True` 的网关才会被主程序选中进行消息路由
* `route_type="send"` 或 `"duplex"` 且 `ready=True` 的网关可被 Platform IO 选中处理出站消息
* `route_type="receive"` 或 `"duplex"` 且 `ready=True` 的网关可通过 `ctx.gateway.route_message()` 注入入站消息
* 插件应在链路可用时上报 `ready=True`，在断开或卸载时上报 `ready=False`

## 完整适配器示例

以下是一个完整的 QQ 平台适配器示例，基于 NapCat 协议实现双向消息路由：

```python
from typing import Any

from maibot_sdk import MaiBotPlugin, MessageGateway


class NapCatGatewayPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 上报网关就绪状态
        await self.ctx.gateway.update_state(
            gateway_name="napcat_gateway",
            ready=True,
            platform="qq",
            account_id="10001",
            scope="primary",
            metadata={"protocol": "napcat"},
        )
        self.ctx.logger.info("NapCat 网关已就绪")

    async def on_unload(self) -> None:
        # 上报网关离线
        await self.ctx.gateway.update_state(
            gateway_name="napcat_gateway",
            ready=False,
        )
        self.ctx.logger.info("NapCat 网关已下线")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @MessageGateway(
        route_type="duplex",
        name="napcat_gateway",
        platform="qq",
        protocol="napcat",
        account_id="10001",
        scope="primary",
    )
    async def send_to_platform(
        self,
        message: dict[str, Any],
        route: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """出站：将 Host 消息转发到外部平台。"""
        # 将 Host MessageDict 转换为平台格式并发送
        platform_msg = self._convert_to_platform_format(message)
        result = await self._send_to_napcat(platform_msg)
        return {"success": True, "external_message_id": result.get("message_id")}

    async def handle_inbound(self, payload: dict[str, Any]) -> None:
        """入站：将外部平台消息注入 Host。

        此方法由外部平台回调触发（如 WebSocket 推送），
        不是组件装饰器方法，但演示了入站消息的注入流程。
        """
        accepted = await self.ctx.gateway.route_message(
            gateway_name="napcat_gateway",
            message_dict={
                "message_id": payload["message_id"],
                "platform": "qq",
                "message_info": {
                    "user_info": {
                        "user_id": payload["user_id"],
                        "user_nickname": payload["nickname"],
                    },
                    "additional_config": {},
                },
                "raw_message": payload["message"],
            },
            route_metadata={
                "self_id": "10001",
                "connection_id": "primary",
            },
            external_message_id=payload["message_id"],
            dedupe_key=payload["message_id"],
        )
        if not accepted:
            self.ctx.logger.warning(
                "Host 未接收入站消息: %s", payload["message_id"]
            )

    def _convert_to_platform_format(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        """将 Host 消息格式转换为平台格式。"""
        return {
            "action": "send_msg",
            "params": {
                "message_type": "group",
                "group_id": message.get("group_id"),
                "message": message.get("raw_message", ""),
            },
        }

    async def _send_to_napcat(
        self, platform_msg: dict[str, Any]
    ) -> dict[str, Any]:
        """发送消息到 NapCat API。"""
        # 实际实现中这里会调用 NapCat 的 HTTP/WebSocket API
        return {"message_id": "platform-msg-1"}


def create_plugin():
    return NapCatGatewayPlugin()
```

## 仅入站网关示例

如果只需要向 MaiBot 注入消息（如 Webhook 监听），可以使用 `route_type="receive"`：

```python
from typing import Any

from maibot_sdk import MaiBotPlugin, MessageGateway


class WebhookReceiverPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        await self.ctx.gateway.update_state(
            gateway_name="webhook_receiver",
            ready=True,
            platform="webhook",
            scope="default",
        )

    async def on_unload(self) -> None:
        await self.ctx.gateway.update_state(
            gateway_name="webhook_receiver",
            ready=False,
        )

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @MessageGateway(
        route_type="receive",
        name="webhook_receiver",
        platform="webhook",
    )
    async def handle_outbound(self, message: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """仅入站网关，出站方向不会收到消息。"""
        # receive 类型网关不会被选中处理出站消息
        # 此处理器不会被调用，但必须声明
        return {"success": True}

    async def inject_webhook_message(self, payload: dict[str, Any]) -> None:
        """接收 Webhook 回调并注入消息。"""
        accepted = await self.ctx.gateway.route_message(
            gateway_name="webhook_receiver",
            message_dict={
                "message_id": payload["id"],
                "platform": "webhook",
                "message_info": {
                    "user_info": {
                        "user_id": payload.get("sender", "unknown"),
                        "user_nickname": payload.get("sender_name", "unknown"),
                    },
                    "additional_config": {},
                },
                "raw_message": payload.get("content", ""),
            },
        )
        if accepted:
            self.ctx.logger.info("Webhook 消息已注入")


def create_plugin():
    return WebhookReceiverPlugin()
```

## 网关处理器参数

`@MessageGateway` 装饰的处理器方法接收以下参数：

* **`self`** `MaiBotPlugin` — 插件实例
* **`message`** `dict[str, Any]` — Host 传出的消息字典（出站方向）
* **`route`** `dict[str, Any] | None` — 路由信息
* **`metadata`** `dict[str, Any] | None` — 路由元数据
* **`**kwargs`** `Any` — 其他参数

处理器返回值为 `dict[str, Any]`，应至少包含 `success` 字段表示发送是否成功。

## 消息路由流程

### 出站流程（Host → 外部平台）

```mermaid
sequenceDiagram
    participant Host as 主程序
    participant GW as MessageGateway 处理器
    participant Platform as 外部平台

    Host->>Host: 选择 ready=True 的 send/duplex 网关
    Host->>GW: 调用网关处理器(message, route, metadata)
    GW->>GW: 转换消息为平台格式
    GW->>Platform: 发送到外部平台
    Platform-->>GW: 返回平台消息 ID
    GW-->>Host: 返回 {success: true, external_message_id: ...}
```

### 入站流程（外部平台 → Host）

```mermaid
sequenceDiagram
    participant Platform as 外部平台
    participant Plugin as 插件
    participant Host as 主程序

    Platform->>Plugin: 推送消息（WebSocket/HTTP 回调等）
    Plugin->>Plugin: 转换为 Host 消息格式
    Plugin->>Host: ctx.gateway.route_message(gateway_name, message_dict, ...)
    Host->>Host: 验证消息格式和网关状态
    Host-->>Plugin: 返回是否接受
    Host->>Host: 将消息投递到消息处理链
```

## 网关生命周期

```mermaid
stateDiagram-v2
    [*] --> Offline: 插件加载
    Offline --> Ready: update_state(ready=True)
    Ready --> Offline: update_state(ready=False)
    Ready --> Offline: 插件卸载 (on_unload)
    Offline --> [*]: 插件销毁
```

::: important

* 插件在 `on_load()` 中应调用 `ctx.gateway.update_state(ready=True)` 上报就绪状态
* 插件在 `on_unload()` 中应调用 `ctx.gateway.update_state(ready=False)` 上报离线状态
* 只有 `ready=True` 的网关才会参与消息路由
  :::

## 平台字段说明

* **`platform`** `str` — 目标平台名称（如 `"qq"`、`"discord"`、`"webhook"`）
* **`protocol`** `str` — 协议或实现名称（如 `"napcat"`、`"go-cqhttp"`、`"discord.py"`）
* **`account_id`** `str` — 机器人账号 ID（如 `"10001"`、`"bot#1234"`）
* **`scope`** `str` — 路由作用域（如 `"primary"`、`"default"`）

`platform`、`protocol`、`account_id`、`scope` 也可以在运行时通过 `ctx.gateway.update_state()` 动态上报，无需在装饰器中固定。

---

---
url: /develop/plugin-dev/lifecycle.md
---

# 生命周期

MaiBot 插件有三个生命周期方法：`on_load()`、`on_unload()` 和 `on_config_update()`。SDK 强制要求所有插件实现这三个方法，否则 Runner 会拒绝加载。

## create\_plugin() 工厂函数

每个插件的 `plugin.py` 必须导出一个顶层 `create_plugin()` 函数，返回插件实例：

```python
from maibot_sdk import MaiBotPlugin


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        ...

    async def on_unload(self) -> None:
        ...

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        ...


def create_plugin():
    return MyPlugin()
```

Runner 加载插件时：

1. 导入 `plugin.py` 模块
2. 调用 `create_plugin()` 获取插件实例
3. 注入 `PluginContext`（此时 `self.ctx` 可用）
4. 调用 `on_load()`

## on\_load()

插件加载完成后的回调。Runner 在注入 `PluginContext` 并完成 capability bootstrap **之后**才调用此方法，因此可以在 `on_load()` 中直接使用 `self.ctx` 的所有能力代理。

```python
async def on_load(self) -> None:
    """Called after plugin loaded. Initialize resources here.

    Runner has already injected PluginContext before calling this,
    so self.ctx is available.
    """
```

**典型用途：**

* 初始化插件内部状态
* 调用 `self.ctx.gateway.update_state()` 上报消息网关状态
* 调用 `self.register_dynamic_api()` 注册动态 API 并 `await self.sync_dynamic_apis()`
* 读取配置并初始化资源

**示例：**

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyConfig(PluginConfigBase):
    greeting: str = Field(default="你好！", description="默认问候语")


class MyPlugin(MaiBotPlugin):
    config_model = MyConfig

    async def on_load(self) -> None:
        # self.ctx 已经注入，可以直接使用
        self.ctx.logger.info("插件已加载，当前问候语: %s", self.config.greeting)

        # 可以在这里注册动态 API
        self.register_dynamic_api(
            "my_api",
            self._handle_api,
            description="示例 API",
            version="1",
            public=True,
        )
        await self.sync_dynamic_apis()

    async def _handle_api(self, **kwargs):
        return {"status": "ok"}
```

## on\_unload()

插件卸载前的回调。在此方法中释放插件持有的所有资源。

```python
async def on_unload(self) -> None:
    """Called before plugin unloaded. Cleanup resources."""
```

**典型用途：**

* 关闭网络连接、文件句柄
* 上报网关离线状态（`self.ctx.gateway.update_state(..., ready=False)`）
* 注销动态 API
* 保存持久化数据

**示例：**

```python
class MyPlugin(MaiBotPlugin):
    async def on_unload(self) -> None:
        self.ctx.logger.info("插件正在卸载")

        # 上报消息网关离线
        await self.ctx.gateway.update_state(
            gateway_name="my_gateway",
            ready=False,
        )

        # 清空动态 API
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")
```

::: warning 注意
`on_unload()` 中仍然可以使用 `self.ctx`，但应尽快完成清理工作，不要执行耗时操作。
:::

## on\_config\_update()

配置热重载回调。当插件配置或已订阅的全局配置发生变化时，Runner 会调用此方法。

```python
async def on_config_update(
    self,
    scope: str,
    config_data: dict[str, Any],
    version: str,
) -> None:
    """Called when config hot-reloads.

    Args:
        scope: 配置变更范围，取值为 "self"、"bot" 或 "model"。
        config_data: 当前范围对应的最新配置数据。
        version: 配置版本号。
    """
```

### scope 取值

* **`"self"`** → `CONFIG_RELOAD_SCOPE_SELF` — 插件自身配置。插件目录下的 `config.toml` 变化时**始终触发**，无需订阅
* **`"bot"`** → `ON_BOT_CONFIG_RELOAD` — 全局 Bot 配置。需要通过 `config_reload_subscriptions` 订阅
* **`"model"`** → `ON_MODEL_CONFIG_RELOAD` — LLM 模型配置。需要通过 `config_reload_subscriptions` 订阅

::: important

* `scope == "self"` 的回调**始终触发**，不需要额外订阅
* `scope == "bot"` 和 `scope == "model"` 只有在 `config_reload_subscriptions` 中声明后才会触发
  :::

### 示例

```python
from maibot_sdk import MaiBotPlugin, CONFIG_RELOAD_SCOPE_SELF, ON_BOT_CONFIG_RELOAD, ON_MODEL_CONFIG_RELOAD
from typing import ClassVar, Iterable


class MyPlugin(MaiBotPlugin):
    # 订阅 bot 和 model 两种全局配置的热重载
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            # 插件自身配置变化，self.config 会自动更新
            self.ctx.logger.info("插件配置已更新: version=%s", version)
        elif scope == ON_BOT_CONFIG_RELOAD:
            # 全局 Bot 配置变化
            bot_name = config_data.get("bot_name", "未知")
            self.ctx.logger.info("Bot 配置已更新: bot_name=%s, version=%s", bot_name, version)
        elif scope == ON_MODEL_CONFIG_RELOAD:
            # LLM 模型配置变化
            model_name = config_data.get("model_name", "未知")
            self.ctx.logger.info("模型配置已更新: model=%s, version=%s", model_name, version)
```

## config\_reload\_subscriptions

类变量，声明插件需要订阅的全局配置热重载范围。仅支持 `"bot"` 和 `"model"` 两个值：

```python
from typing import ClassVar, Iterable


class MyPlugin(MaiBotPlugin):
    # 订阅两种全局配置
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    # 仅订阅 Bot 配置
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot",)

    # 仅订阅 Model 配置
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ("model",)

    # 不订阅任何全局配置（默认值）
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ()
```

**规则：**

* 默认值为空元组 `()`，即不订阅任何全局配置
* `"self"` 范围**始终触发**回调，不需要也不能在此声明
* 仅 `"bot"` 和 `"model"` 是有效的订阅值
* 声明不支持的值会在 `get_config_reload_subscriptions()` 中抛出 `ValueError`
* 不能直接传入字符串（如 `config_reload_subscriptions = "bot"`），必须使用可迭代集合

## 完整生命周期示例

以下是一个包含所有生命周期方法的完整插件示例：

```python
from typing import Any, ClassVar

from maibot_sdk import (
    CONFIG_RELOAD_SCOPE_SELF,
    Command,
    MaiBotPlugin,
    ON_BOT_CONFIG_RELOAD,
    ON_MODEL_CONFIG_RELOAD,
    Tool,
)
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class GreeterPlugin(MaiBotPlugin):
    """问候插件 —— 演示完整的插件生命周期。"""

    # 订阅全局配置热重载
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    async def on_load(self) -> None:
        """插件加载时初始化。"""
        self.ctx.logger.info("GreeterPlugin 已加载")
        # self.ctx 在此已经可用，可以直接调用能力代理
        raw_config = self.get_plugin_config_data()
        self.ctx.logger.info("当前配置: %s", raw_config)

    async def on_unload(self) -> None:
        """插件卸载时清理资源。"""
        self.ctx.logger.info("GreeterPlugin 正在卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        """处理配置热更新。"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info("插件配置已更新: version=%s", version)
        elif scope == ON_BOT_CONFIG_RELOAD:
            self.ctx.logger.info("Bot 配置已更新: version=%s", version)
        elif scope == ON_MODEL_CONFIG_RELOAD:
            self.ctx.logger.info("Model 配置已更新: version=%s", version)

    @Tool(
        "greet",
        brief_description="向用户打招呼",
        detailed_description="参数说明：\n- stream_id：string，必填。当前聊天流 ID。",
        parameters=[
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="当前聊天流 ID",
                required=True,
            ),
        ],
    )
    async def handle_greet(self, stream_id: str, **kwargs):
        await self.ctx.send.text("你好！", stream_id)
        return {"success": True, "message": "已回复"}

    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2


def create_plugin():
    return GreeterPlugin()
```

## 生命周期时序

```mermaid
sequenceDiagram
    participant Runner
    participant Plugin

    Runner->>Plugin: create_plugin()
    Note over Plugin: 返回插件实例
    Runner->>Plugin: _set_context(ctx)
    Note over Plugin: 注入 PluginContext
    Runner->>Plugin: on_load()
    Note over Plugin: 初始化资源，ctx 可用

    Note over Runner,Plugin: ... 插件运行中 ...

    Note over Runner: config.toml 变更
    Runner->>Plugin: on_config_update(scope="self", ...)

    Note over Runner: 全局配置变更（如已订阅）
    Runner->>Plugin: on_config_update(scope="bot"/"model", ...)

    Note over Runner: 卸载或热重载
    Runner->>Plugin: on_unload()
    Note over Plugin: 清理资源
```

---

---
url: /manual.md
---

# 用户手册

欢迎来到 MaiBot 用户手册！这里涵盖了从安装部署到高级配置的完整指南。

## 快速导航

### 🚀 快速开始

如果你是第一次使用 MaiBot，建议按以下顺序阅读：

1. [部署概览](/manual/deployment/) - 了解部署方式和前提条件
2. [安装指南](/manual/deployment/installation) - 下载并安装 MaiBot
3. [NapCat 适配器](/manual/adapters/napcat) - 连接 QQ
4. [配置概览](/manual/configuration/) - 了解配置文件结构

### ⚙️ 配置详解

* [Bot 配置](/manual/configuration/bot-config) - 平台、昵称、人格、聊天、记忆等基础设置
* [模型配置](/manual/configuration/model-config) - LLM 模型提供商和多模型回退

### 🧠 功能详解

* [消息处理管线](/manual/features/message-pipeline) - 消息从接收到回复的完整流程
* [Maisaka 推理引擎](/manual/features/maisaka-reasoning) - AI 如何决定是否回复、何时回复、回复什么
* [记忆系统](/manual/features/memory-system) - 长期记忆、人物画像、聊天摘要
* [表达与术语学习](/manual/features/learning) - AI 如何学习说话风格和新词汇
* [表情包系统](/manual/features/emoji-system) - 表情包收集、管理和发送
* [MCP 集成](/manual/features/mcp) - Model Context Protocol 工具集成

### 🖥️ WebUI 管理

* [WebUI 概览](/manual/webui/) - 通过浏览器管理 MaiBot
* [配置管理](/manual/webui/config-management) - 在线编辑配置
* [记忆管理](/manual/webui/memory-management) - 可视化管理记忆数据
* [插件管理](/manual/webui/plugin-management) - 安装和管理插件
* [聊天与统计](/manual/webui/chat-stats) - 查看聊天记录和使用统计

### 🔌 适配器

* [适配器概览](/manual/adapters/) - 了解平台适配器架构
* [NapCat](/manual/adapters/napcat) - QQ 协议适配
* [GoCQ](/manual/adapters/gocq) - GoCQ 协议适配

---

---
url: /community.md
---

# 社区

欢迎加入 MaiBot 社区！在这里你可以与其他用户交流使用经验、获取技术支持、参与项目贡献，以及关注项目的最新动态。

## QQ 交流群

MaiBot 有多个 QQ 交流群，按不同用途划分：

| 类别 | 群名称 | 链接 | 说明 |
|------|--------|------|------|
| 技术交流 | 麦麦脑电图 | [加入群聊](https://qm.qq.com/q/RzmCiRtHEW) | 技术交流 / 答疑 |
| 技术交流 | 麦麦大脑磁共振 | [加入群聊](https://qm.qq.com/q/VQ3XZrWgMs) | 技术交流 / 答疑 |
| 技术交流 | 麦麦要当 VTB | [加入群聊](https://qm.qq.com/q/wGePTl1UyY) | 技术交流 / 答疑 |
| 闲聊吹水 | 麦麦之闲聊群 | [加入群聊](https://qm.qq.com/q/JxvHZnxyec) | 仅限闲聊，不答疑 |
| 插件开发 | 插件开发群 | [加入群聊](https://qm.qq.com/q/1036092828) | 进阶开发与测试 |

::: tip 提示
技术问题请优先在技术交流群中提问，闲聊群不提供技术答疑。如果你在开发 MaiBot 插件，欢迎加入插件开发群交流。
:::

## GitHub

MaiBot 项目在 GitHub 上开源，欢迎参与贡献和反馈：

| 项目 | 链接 | 说明 |
|------|------|------|
| MaiBot 主仓库 | [Mai-with-u/MaiBot](https://github.com/Mai-with-u/MaiBot) | 核心项目代码 |
| Mailauncher | [Mai-with-u/mailauncher](https://github.com/Mai-with-u/mailauncher) | MaiBot 启动器（仅 MacOS，早期开发中） |
| 插件 SDK | [Mai-with-u/maibot-plugin-sdk](https://github.com/Mai-with-u/maibot-plugin-sdk) | 插件开发文档与 SDK |

### 参与贡献

欢迎参与 MaiBot 的开发！在提交贡献前，请先阅读 [贡献指南](https://github.com/Mai-with-u/MaiBot/blob/main/docs/CONTRIBUTE.md)。

贡献方式：

* **提交 Issue**：报告 Bug 或提出功能建议
* **提交 Pull Request**：修复 Bug 或实现新功能
* **改进文档**：补充和完善项目文档
* **开发插件**：为 MaiBot 开发第三方插件

### Issue 反馈

在 GitHub 上提交 Issue 时，请：

1. 使用清晰的标题描述问题
2. 提供复现步骤和环境信息（操作系统、Python 版本、MaiBot 版本）
3. 附上相关的日志输出
4. 检查是否已有相同问题的 Issue

## 社交媒体

关注 MaiBot 的最新动态和开发进展：

| 平台 | 说明 |
|------|------|
| GitHub Discussions | [Mai-with-u/MaiBot Discussions](https://github.com/Mai-with-u/MaiBot/discussions) |
| DeepWiki | [MaiBot DeepWiki](https://deepwiki.com/DrSmoothl/MaiBot) |

## 衍生项目

MaiBot 生态中有多个有趣的衍生项目：

| 项目 | 链接 | 说明 |
|------|------|------|
| Amaidesu | [Mai-with-u/Amaidesu](https://github.com/Mai-with-u/Amaidesu) | 让麦麦在 B 站开播 |
| MoFox\_Bot | [MoFox-Studio/MoFox-Core](https://github.com/MoFox-Studio/MoFox-Core) | 基于 MaiCore 0.10.0 的增强型 Fork，更稳定更有趣 |
| MaiCraft | [Mai-with-u/Maicraft](https://github.com/Mai-with-u/Maicraft) | 让麦麦陪你玩 Minecraft（暂时停止维护中） |

## 文档与资源

| 资源 | 链接 | 说明 |
|------|------|------|
| 核心文档 | [docs.mai-mai.org](https://docs.mai-mai.org) | 最全面的文档中心 |
| 演示视频 | [Bilibili](https://www.bilibili.com/video/BV1amAneGE3P) | 麦麦功能演示视频 |
| 插件开发指南 | [maibot-plugin-sdk 文档](https://github.com/Mai-with-u/maibot-plugin-sdk/blob/main/docs/guide.md) | 插件开发详细指南 |

## 设计理念

MaiBot 的核心设计理念来自创始人千石可乐（SengokuCola）：

> 这个项目最初只是为了给牛牛 bot 添加一点额外的功能，但是功能越写越多，最后决定重写。其目的是为了创造一个活跃在 QQ 群聊的"生命体"。目的并不是为了写一个功能齐全的机器人，而是一个尽可能让人感知到真实的类人存在。

> 程序的功能设计理念基于一个核心的原则："最像而不是好"。

> 如果人类真的需要一个 AI 来陪伴自己，并不是所有人都需要一个完美的，能解决所有问题的"helpful assistant"，而是一个会犯错的，拥有自己感知和想法的"生命形式"。

## 开源与许可

MaiBot 基于 **GPL-3.0** 许可证开源。使用前请阅读 [用户协议 (EULA)](https://github.com/Mai-with-u/MaiBot/blob/main/EULA.md) 和 [隐私协议](https://github.com/Mai-with-u/MaiBot/blob/main/PRIVACY.md)。AI 生成内容请仔细甄别。

::: warning 重要
MaiBot 是开源项目，完全免费使用。如果你看到有人售卖 MaiBot，请注意辨别，避免上当受骗。
:::

---

---
url: /manual/webui/chat-stats.md
---

# 聊天记录和统计

看看 MaiBot 有多活跃，都聊了什么！

## 聊天统计

### 📊 数据总览

打开"聊天统计"页面，能看到：

* **总消息数** - 机器人收到多少消息
* **回复数** - 机器人回复了多少条
* **在线时长** - 机器人运行了多久
* **平均响应** - 回复速度有多快

### 💰 费用统计

还能看到花钱的情况：

* **总花费** - 一共花了多少钱
* **每小时花费** - 平均每小时多少钱
* **Token 用量** - AI 处理了多少文字
* **各模型花费** - 不同 AI 模型分别花了多少

### 📈 趋势图表

直观的图表显示：

* **24 小时** - 最近一天的活动情况
* **7 天** - 最近一周的趋势
* **高峰时段** - 什么时候最活跃

## 聊天记录

### 查看记录

可以查看详细的聊天历史：

* 谁说了什么
* 机器人怎么回复的
* 什么时候聊的
* 在哪个群聊的

### 搜索记录

想找特定内容？

* 按用户筛选
* 按时间范围查找
* 按群聊筛选

### 记录管理

* **清理记录** - 删除旧记录
* **备份重要聊天** - 保存有趣的对话

## 用户管理

### 用户列表

显示所有聊过天的用户：

* 用户昵称和头像
* 认识多久了
* 聊天频率
* 在哪个平台认识的

### 人物画像

点击用户能看到：

* 性格特点
* 兴趣爱好
* 聊天习惯
* 互动历史

### 用户统计

* **总人数** - 认识多少用户
* **活跃用户** - 经常聊天的有多少
* **平台分布** - QQ、微信等分别多少

## 表达方式

### 说话风格

MaiBot 会学习不同的表达方式：

* 正式/随意
* 活泼/沉稳
* 幽默/严肃
* 各种网络用语

### 黑话管理

机器人学到的网络用语：

* 新词热词
* 梗和段子
* 小圈子术语
* 可以手动确认或拒绝

### 表情包

收集的表情包：

* 使用频率统计
* 热门表情包
* 可以上传新的
* 禁用不合适的

表情包在 WebUI 中统一显示为四种状态：

* **认识**：有描述，但未注册、未封禁
* **不认识**：还没有描述，且未注册、未封禁
* **据为己用**：已经注册，可被 MaiBot 使用
* **丢弃**：已经封禁，不再使用

从 WebUI 手动上传的表情会直接标记为「据为己用」。上传时填写的标签列表会合并为表情描述；如果图片已存在于数据库，会复用原记录、更新描述、解除封禁并标记为已注册。删除未注册表情时会同步删除数据库记录和本地文件；删除已注册表情时会先从可用表情库卸载，再删除数据库记录和文件。

## 使用建议

### 日常查看

* 每天看看统计数据，了解活跃度
* 关注费用变化，避免超支
* 查看用户反馈，改进机器人

### 数据分析

* 分析高峰时段，合理安排维护
* 观察用户偏好，调整机器人性格
* 统计热门话题，增加相关内容

### 优化建议

* 响应太慢？检查配置
* 费用太高？换便宜模型
* 用户太少？增加推广

## 常见问题

**Q: 统计数据多久更新？**
A: 实时更新，随时能看到最新数据

**Q: 记录会保存多久？**
A: 默认长期保存，可以设置自动清理

**Q: 可以导出数据吗？**
A: 暂不支持导出功能，未来版本会添加

**Q: 如何降低使用费用？**
A: 选择便宜模型，减少不必要的调用，优化提示词

## 实用技巧

### 监控机器人健康

* 响应时间突然变长？可能有问题
* 费用异常增加？检查是否被攻击
* 活跃用户下降？看看是不是说错话了

### 改善用户体验

* 分析用户画像，个性化回复
* 统计热门话题，准备相关内容
* 记录用户反馈，持续改进

### 节省开支

* 选择性价比高的模型
* 设置合理的调用频率
* 避免重复调用浪费 Token

---

---
url: /manual/features/emoji-system.md
---

# 表情包功能 😊

MaiBot 不只能发文字，它还会发表情包！而且不是随便发，它会根据聊天内容智能选择合适的表情包，让对话更有趣、更生动。

## MaiBot 的表情包超能力

### 🎯 智能选择

**看情绪选表情**

* 你开心时，它发开心的表情
* 你难过时，它发安慰的表情
* 你生气时，它发缓和气氛的表情

**看内容选表情**

* 聊到美食，发吃货表情
* 聊到游戏，发游戏相关表情
* 聊到工作，发打工人的表情

**看场合选表情**

* 正式场合用礼貌的表情
* 轻松场合用搞笑的表情
* 深夜聊天用温柔的表情

### 📸 自动收集

**看到好表情就收藏**

* 群里有人发表情包，它会偷偷收藏
* 自动识别表情包的内容和情绪
* 给每个表情包打上标签

**建立自己的表情库**

* 收集各种风格的表情包
* 按情绪和场景分类
* 越收集越懂你群的口味

### 🧠 理解表情

**看懂表情包**

* 能识别表情包表达的情绪
* 理解表情包的梗和含义
* 知道什么时候用合适

**不只是收藏**

* 真的理解每个表情的用法
* 不会用错场合
* 用得恰到好处

## 表情包是怎么工作的？

### 1️⃣ 收集阶段

**自动发现**

```
群友：[发了一个搞笑表情包]
MaiBot：（这个表情好有趣，收藏了！）
     （标签：搞笑、猫、开心）
```

**智能识别**

* 用 AI 识别表情包内容
* 分析表达的情绪
* 自动生成标签

### 2️⃣ 分类整理

**按情绪分类**

* 开心、难过、生气、惊讶
* 搞笑、温馨、励志、吐槽
* 正式、随意、亲切、幽默

**按场景分类**

* 日常聊天、工作讨论
* 游戏开黑、深夜谈心
* 节日祝福、安慰鼓励

### 3️⃣ 智能选择

**看情绪匹配**

```
用户：今天工作好累啊 😭
MaiBot：[发一个"打工人加油"的表情包]
```

**看内容匹配**

```
用户：今晚吃火锅！
MaiBot：[发一个"吃货开心"的表情包]
```

**看关系匹配**

* 跟熟人用搞笑表情
* 跟陌生人用礼貌表情
* 跟好友用亲昵表情

## 实际例子 🌰

### 情绪匹配

**你开心时**：

```
你：考试过了！好开心！
MaiBot：太棒了！恭喜你！🎉
     [发一个"庆祝"的表情包]
```

**你难过时**：

```
你：今天被老板骂了，好难受
MaiBot：抱抱你，打工人都不容易 😢
     [发一个"安慰"的表情包]
```

### 内容匹配

**聊美食**：

```
群友：今晚去吃烧烤？
MaiBot：冲！烧烤yyds！😋
     [发一个"吃货兴奋"的表情包]
```

**聊游戏**：

```
群友：今晚开黑？
MaiBot：走起！我辅助贼6 🎮
     [发一个"游戏开始"的表情包]
```

### 场景匹配

**工作场合**：

```
同事：这个方案大家觉得怎么样？
MaiBot：我觉得挺完整的，细节可以再优化 👍
     [发一个"专业点头"的表情包]
```

**朋友闲聊**：

```
好友：今天好无聊啊
MaiBot：来，给你看个搞笑的 😄
     [发一个"沙雕"的表情包]
```

## 表情包管理

### 📁 自动整理

**智能分类**

* 自动按情绪和场景分类
* 定期清理重复的表情
* 保留最受欢迎的表情

**容量管理**

* 表情包装满时会智能淘汰
* 保留常用的，删除不常用的
* 用 AI 决定哪些该留哪些该删

### 🔍 快速查找

**标签搜索**

* 每个表情都有多个标签
* 想找什么类型的很快就能找到
* 支持情绪、场景、内容多维度搜索

**智能推荐**

* 根据聊天内容推荐合适的表情
* 越用越懂你群的口味
* 推荐准确率越来越高

## 你可以做什么？

### 👀 查看表情库

通过 WebUI 你可以：

* 看 MaiBot 收集了哪些表情
* 查看每个表情的标签
* 看使用频率和最后使用时间
* 按「认识 / 不认识 / 据为己用 / 丢弃」筛选表情状态

### 🛠️ 管理表情

* 删除不合适的表情
* 给表情添加自定义标签
* 设置某些表情的使用偏好
* 删除未注册表情时会同步删除数据库记录和本地文件；删除已注册表情时也会先从可用表情库中卸载

### 📤 上传表情

* 手动上传你喜欢的表情
* 上传时填写标签列表，系统会合并为表情描述
* 丰富它的表情库
* 从 WebUI 上传的表情会直接标记为「据为己用」

### ⚙️ 设置偏好

* 设置表情的使用频率
* 选择喜欢的表情风格
* 控制自动收集的开关

## 表情包小贴士

### 💡 使用建议

* 表情要适量，不要满屏都是
* 根据场合选择合适的表情
* 好的表情能让对话更有趣

### 🎨 风格多样

* 收集不同风格的表情
* 可爱的、搞笑的、正经的都要有
* 适应不同的聊天场景

### 🔄 定期更新

* 表情也有流行趋势
* 定期添加新表情
* 淘汰过时的表情

***

MaiBot 的表情包功能不是简单的"发图"，而是真正理解表情包的含义，用得恰到好处。它会让你们的对话更生动、更有趣、更有"人味"！

---

---
url: /develop/architecture/emoji-internals.md
---

# 表情系统内部架构

本文基于 code-map 快照编写。

本文面向开发者，说明 `emoji_system/` 目录、`send_emoji` 内置工具、表情包数据库、内存缓存、VLM 描述生成、PIL 拼图合成和定期维护之间的协作关系。它与 `docs/manual/features/emoji-system.md` 的用户视角互补，不重复介绍如何管理表情包，也不把 WebUI 操作当成内部实现。

## 概述

**定位** ：表情系统是 MaiBot 的视觉表达素材层。它负责把图片文件、数据库记录、情绪标签、使用次数和维护状态组织成可被推理引擎调用的能力。

**核心单例** ：`EmojiManager` 是表情包的集中管理器。它保存 `self.emojis` 内存池，维护 `self._emoji_num` 数量，注册配置热重载回调，并调度描述构建和定期维护任务。

**用户边界** ：用户文档解释“什么时候会发表情包、如何上传和审核”。本文解释“为什么能选中这张图、图片如何变成 base64、使用次数如何写入数据库”。

**实现边界** ：当前实现不把表情包选择权重直接交给 `ExpressionLearner`。表情包有 `query_count` 和 `last_used_time`，表达方式学习有 `Expression.count` 和 `last_active_time`，两者通过 Maisaka 的上下文和工具调用产生间接关系。

**主要输入** ：配置项、数据库中的 `Images` 记录、`data/emoji` 目录中的图片、Maisaka 推理上下文、工具调用参数和 Hook 返回值。

**主要输出** ：选中 `MaiEmoji` 对象、base64 图片、发送服务消息、使用次数更新、描述缓存、维护日志和监控 metadata。

## 架构图

```mermaid
graph TD
    subgraph "配置与存储"
        C["global_config.emoji\nPydantic JSON schema"]
        D["data/emoji\n图片文件目录"]
        DB["Images 表\nImageType.EMOJI"]
    end

    subgraph "EmojiManager"
        L["load_emojis_from_db\n数据库到内存缓存"]
        R["register_emoji_by_filename\n注册新图片"]
        DESC["build_emoji_description\nVLM 生成描述"]
        REV["review_emoji_for_registration\n内容过滤"]
        MATCH["get_emoji_for_emotion\nLevenshtein 情绪匹配"]
        USAGE["update_emoji_usage\nquery_count 与 last_used_time"]
        MAINT["periodic_emoji_maintenance\n扫描与完整性检查"]
        CACHE["self.emojis\nMaiEmoji 内存池"]
    end

    subgraph "Maisaka 工具层"
        T["send_emoji 内置工具"]
        H1["emoji.maisaka.before_select"]
        SEL["emoji_selector 回调"]
        H2["emoji.maisaka.after_select"]
        SEND["send_emoji_for_maisaka"]
    end

    subgraph "候选选择与合成"
        SAMP["random.sample\n候选池"]
        PIL["PIL 拼图合成\n256px 小图 + 序号"]
        SUB["emoji_selection 子代理\n选择序号"]
    end

    subgraph "出站发送"
        B64["resolve_stored_image_path\nimage_path_to_base64"]
        SVC["send_service.emoji_to_stream_with_message"]
        CLI["CLI 预览与本地使用记录"]
        HIST["Maisaka 聊天历史同步"]
    end

    C --> R
    C --> MAINT
    D --> R
    DB --> L
    L --> CACHE
    R --> DESC
    DESC --> REV
    REV --> DB
    DB --> USAGE
    R --> CACHE
    MAINT --> D
    MAINT --> DB
    MAINT --> CACHE
    T --> H1
    H1 --> SEL
    SEL --> SAMP
    SAMP --> PIL
    PIL --> SUB
    SUB --> H2
    H2 --> SEND
    SEND --> B64
    B64 --> SVC
    B64 --> CLI
    SVC --> HIST
    SEND --> USAGE
```

## 核心概念

**`EmojiManager`** ：表情包生命周期管理器。它不直接代表一张图片，而是把数据库、文件系统、内存缓存、VLM 调用、Hook 和定期维护串起来。

**`MaiEmoji`** ：运行时表情包对象。它包含 `full_path`、`file_name`、`file_hash`、`image_format`、`description`、`emotion`、`query_count`、`register_time` 和 `last_used_time`。

**`file_hash`** ：图片身份标识。它由 SHA256 计算得到，用于数据库主索引、内存查找、Hook 序列化和发送成功后的使用统计。

**`description`** ：逗号分隔的描述或标签文本。它通常由 VLM 生成，也可以来自数据库缓存、WebUI 上传或 Hook 改写。

**`emotion`** ：从 `description` 规范化得到的标签列表。规范化会拆分中文逗号、顿号、分号和换行，并去重。

**`query_count`** ：表情包被真实发送后的累计次数。它用于统计热度，也在满额替换时作为低使用率优先候选的权重来源。

**`last_used_time`** ：最近一次真实发送时间。它用于维护、排序和开发者排查使用频率。

**`is_registered`** ：数据库注册状态。只有已注册、未封禁且文件存在的记录会进入可发送内存池。

**`is_banned`** ：封禁状态。被封禁的表情不会加载到 `self.emojis`，也不会通过普通选择流程发送。

**`no_file_flag`** ：文件缺失标记。删除时保留描述缓存会设置该标记，未注册记录可继续作为描述缓存存在。

**`vlm_processed`** ：VLM 处理标记。自动维护用它避免对同一批已处理文件反复消耗视觉模型额度。

**`EMOJI_DIR`** ：`data/emoji` 目录。新收集的表情、临时文件和注册文件都在这里落地。

**`Images` 表** ：通用图片数据库表。表情使用 `image_type = ImageType.EMOJI` 区分于普通图片。

**JSON 配置入口** ：`EmojiConfig` 通过 Pydantic 配置模型暴露 JSON schema，运行时通过 `global_config.emoji` 读取。文档说“JSON 配置”时，指的是这些结构化配置项，而不是图片文件内嵌 JSON。

**模型任务配置** ：VLM 描述、内容过滤和选择子代理依赖 `model_task_config`。`emoji_manager_vlm` 使用 `task_name="vlm"`，`emoji_manager_emotion_judge_llm` 使用 `task_name="utils"`。

**内存缓存** ：`emoji_manager.emojis` 是可发送池。它不是完整数据库镜像，只包含当前可用、已注册、未封禁且有文件的 `MaiEmoji`。

**Hook 载荷** ：`_serialize_emoji_for_hook()` 把 `file_hash`、`file_name`、`full_path`、`description`、`emotions` 和 `query_count` 转成插件可接收的字典。

## 表情包加载

**加载入口** ：`load_emojis_from_db()` 在启动阶段把数据库中的已注册表情读入内存。

**数据库扫描** ：它查询全部 `Images` 记录，跳过非 `ImageType.EMOJI` 的记录。

**注册过滤** ：只有 `is_registered=True` 且 `is_banned=False` 的记录会进入候选列表。

**文件校验** ：记录如果标记 `no_file_flag`，或 `resolve_stored_image_path()` 找不到实际文件，会被视为破损注册记录。

**内存构建** ：可用记录通过 `MaiEmoji.from_db_instance()` 转成运行时对象，再追加到 `self.emojis`。

**数量同步** ：加载结束后，`self._emoji_num` 被设置为 `len(self.emojis)`，后续维护循环依赖这个数量判断是否还能收集新表情。

**破损清理** ：破损的已注册记录会从数据库删除，并记录清理数量。未注册但缺少文件的记录不会被当作可发送表情加载。

**注册入口** ：`register_emoji_by_filename()` 用于把 `data/emoji` 中的图片注册进数据库和内存池。

**路径归一化** ：注册时先调用 `Path(filename).absolute().resolve()`，保证后续路径比较和文件访问稳定。

**图片初始化** ：`MaiEmoji(full_path=file_full_path)` 会校验文件存在，记录目录和文件名。

**哈希与格式** ：`calculate_hash_format()` 读取图片字节，计算 SHA256，识别实际格式，并在扩展名不匹配时重命名文件。

**数据库查重** ：注册前按 `image_hash` 和 `ImageType.EMOJI` 查询已有记录。已封禁记录直接跳过，已注册且文件可用也跳过。

**描述复用** ：如果数据库已有 `description`，注册流程会把缓存描述转成 `target_emoji.description` 和 `target_emoji.emotion`。

**描述生成** ：没有描述时调用 `build_emoji_description()`，用 VLM 提取最多 5 个情绪或场景标签。

**内容过滤** ：启用 `content_filtration` 时，`review_emoji_for_registration()` 会把图片转 base64 后调用 VLM 审核。响应包含“否”会拒绝注册。

**容量控制** ：如果 `self._emoji_num` 达到 `max_reg_num` 且 `do_replace=True`，会进入替换流程。

**替换策略** ：`replace_an_emoji_by_llm()` 用 `1 / (query_count + 1)` 作为低使用率优先概率，选择最多 20 个候选，再让 LLM 决定取消注册哪一个编号。

**注册写库** ：`register_emoji_to_db()` 写入 `Images` 记录，设置 `is_registered=True`、`is_banned=False`、`no_file_flag=False`，并保存路径、描述、使用次数和时间。

**注册入内存** ：注册成功后，新 `MaiEmoji` 被追加到 `self.emojis`，`self._emoji_num` 同步增加。

**删除文件** ：`delete_emoji()` 先删除图片文件。文件不存在时只记录警告。

**删除数据库** ：`keep_desc=True` 时保留数据库描述并把 `no_file_flag` 设为 `True`；`keep_desc=False` 时删除数据库记录。

**封禁** ：`ban_emoji()` 把数据库 `is_banned` 设为 `True`，并按 `file_hash` 从内存池移除。

**取消注册** ：`unregister_emoji()` 保留文件和描述，但把 `is_registered` 设为 `False`，并从内存池移除。

## 表情匹配算法

**触发词入口** ：`send_emoji` 工具本身没有参数 schema，实际情绪词来自 Maisaka 的推理结果、工具调用参数或格式化回复标签。

**情绪参数** ：`handle_tool()` 从 `invocation.arguments["emotion"]` 读取 `requested_emotion`，再传给 `send_emoji_for_maisaka()`。

**格式化标签入口** ：`_build_emoji_component_for_label()` 会先尝试把标签当作 `file_hash` 精确查找。

**精确命中** ：`get_emoji_by_hash()` 在 `self.emojis` 中线性查找 `file_hash`。命中后直接返回该 `MaiEmoji`。

**模糊匹配** ：精确查找失败时，`get_emoji_for_emotion()` 调用 `_calculate_emotion_similarity_list()`，把输入标签和每个表情的标签做 Levenshtein 相似度比较。

**相似度公式** ：单个标签相似度为 `1 - distance / max(len(input), len(tag))`。一个表情包取所有标签中的最高相似度。

**Top-N 随机** ：`get_emoji_for_emotion()` 取相似度最高的 10 个表情，再 `random.choice()` 一个。这避免固定返回同一张图。

**空库回退** ：如果 `self.emojis` 为空，匹配函数记录警告并返回 `None`。

**候选池采样** ：`send_emoji.py` 的 `_select_emoji_with_sub_agent()` 使用 `random.sample()` 从 `emoji_manager.emojis` 中抽取候选。默认配置为 25，最大 64。

**上下文匹配** ：工具会收集最近 5 条 `LLMContextMessage.processed_plain_text`，并把 Maisaka 上一次的 `last_reasoning_content` 作为推理理由传给子代理。

**候选拼图匹配** ：子代理看到的是拼图图片和“根据上下文选择最合适一张”的提示词，不是完整数据库列表。

**命中回退** ：子代理返回无效 JSON、越界序号或空候选池时，流程会回退到候选首项或返回空结果。

**Hook 改写** ：`emoji.maisaka.before_select` 可以修改 `requested_emotion`、`reasoning`、`context_texts`、`sample_size`，也可以中止选择。

**结果改写** ：`emoji.maisaka.after_select` 可以替换 `selected_emoji_hash`、补充 `matched_emotion`，也可以中止发送。

**匹配边界** ：当前算法不把 `ExpressionLearner` 的学习结果直接写入表情包权重。它影响的是回复文本和上下文，再间接影响 `send_emoji` 子代理看到的语义环境。

## 关键流程一：表情选择算法

**第一步，触发词提取** ：Maisaka 决定是否调用 `send_emoji`。调用时，`handle_tool()` 尝试从工具参数读取 `emotion`，同时读取最近推理理由和最近聊天文本。

**第二步，选择前 Hook** ：`send_emoji_for_maisaka()` 先触发 `emoji.maisaka.before_select`。插件可以改写输入，也可以返回 `abort_message` 直接中止。

**第三步，候选采样** ：`send_emoji.py` 读取 `emoji_manager.emojis`，按配置数量随机采样。采样数量受 `emoji_send_num` 限制，且不会超过 64。

**第四步，拼图合成** ：候选图片被读取成字节，逐一缩放到 256px 小图，并叠加序号角标，再合成一张 PNG 拼图。

**第五步，子代理选择** ：`run_sub_agent()` 使用 `emoji_selection` prompt。模型任务优先选择专用 `emoji`，其次选择具备视觉能力的 `planner`，最后回退到 `vlm`。

**第六步，结果解析** ：子代理必须返回 `{"emoji_index": 1, "reason": "简短理由"}`。解析失败时记录警告，并使用候选首项。

**第七步，选择后 Hook** ：`send_emoji_for_maisaka()` 触发 `emoji.maisaka.after_select`。Hook 可以替换最终表情，也可以中止发送。

**第八步，空结果处理** ：如果最终 `selected_emoji` 为 `None`，返回失败结果，消息为“当前表情包库中没有可用表情”。

**第九步，发送结果回写** ：`send_emoji.py` 在成功且 `sent_message is None` 时，把 base64 表情追加到聊天历史，保证 Maisaka 后续上下文能看见自己刚发的表情。

**第十步，监控信息** ：工具会把请求消息、子代理输出、token 指标、耗时、选择理由和发送结果写入 metadata，供监控和调试使用。

## PIL 图片合成

**合成目标** ：`send_emoji.py` 的 PIL 合成不是生成新表情包，而是为选择子代理生成候选拼图。

**候选数量** ：`_EMOJI_MAX_CANDIDATE_COUNT = 64`，默认读取 `global_config.emoji.emoji_send_num`。

**小图尺寸** ：`_EMOJI_CANDIDATE_TILE_SIZE = 256`，每张候选图被放入 256x256 的方格。

**网格计算** ：`_calculate_grid_shape()` 枚举列数，计算行数和空位数量，优先选择行列差最小、空位最少的矩形。

**尺寸调整** ：`_build_labeled_tile()` 用 `thumbnail((tile_size, tile_size))` 缩放图片，保持原图比例，不拉伸变形。

**透明通道** ：候选图转换为 `RGBA`，粘贴到白色 `RGBA` 画布上。粘贴时传入原图作为 alpha mask，保留透明边缘。

**文字叠加** ：序号角标用 `ImageDraw` 绘制。黑色半透明圆角矩形作为底，白色数字作为文字。

**默认字体** ：当前实现使用 `ImageFont.load_default()`。如果部署环境没有自定义字体，序号仍能显示，但视觉一致性依赖默认字体。

**占位图** ：读取候选图失败时，`_build_placeholder_tile()` 创建灰色 RGB 背景，并在中间写序号。

**拼图间距** ：`_merge_emoji_tiles()` 使用 `gap = 12`，画布宽高按 `tile_size * columns + gap * (columns - 1)` 计算。

**粘贴顺序** ：候选按列表顺序从左到右、从上到下排列。序号从 1 开始，便于子代理返回 `emoji_index`。

**导出格式** ：最终画布先 `convert("RGB")`，再保存为 PNG 字节流。这样输出稳定，避免透明背景在不同平台渲染差异。

**失败边界** ：图片打不开、格式不支持或文件被占用时，单张小图会变成占位图，不会导致整个拼图流程崩溃。

**性能边界** ：读取候选图片、合并拼图都通过 `asyncio.to_thread()` 放到线程池，避免阻塞事件循环。

## 关键流程二：PIL 图片合成

**第一步，读取字节** ：`_load_emoji_bytes()` 使用 `asyncio.to_thread(emoji.full_path.read_bytes)` 读取单张表情包。

**第二步，并发读取** ：`_build_emoji_candidate_message()` 用 `asyncio.gather()` 并发读取全部候选图片。

**第三步，构建小图** ：`_build_labeled_tile()` 打开图片字节，转换色彩模式，缩放到 256px，再绘制序号角标。

**第四步，创建画布** ：`_merge_emoji_tiles()` 根据候选数量计算行列，创建白色 `RGBA` 大画布。

**第五步，网格粘贴** ：每张带序号小图按行列偏移粘贴到画布，偏移量为 `column * (tile_size + gap)` 和 `row * (tile_size + gap)`。

**第六步，输出消息** ：合成后的 PNG 字节放入 `ImageComponent`，并和“请从这张拼图中选择一个序号”的文本组成 `SessionBackedMessage`。

**第七步，交给子代理** ：候选消息作为 `extra_messages` 传入 `run_sub_agent()`，子代理根据上下文和拼图选择序号。

**第八步，解析序号** ：返回 JSON 中的 `emoji_index` 被转换为 0-based 索引，并检查是否越界。

**第九步，回退处理** ：无效 JSON 或越界序号都会回退到候选首项，避免工具调用因模型格式问题完全失败。

**第十步，记录理由** ：子代理返回的 `reason` 被写入 `selection_metadata`，最终进入工具成功结果。

## 表情发送

**路径解析** ：`send_emoji_for_maisaka()` 先调用 `resolve_stored_image_path(selected_emoji.full_path)`，把存储路径映射为实际文件路径。

**base64 转换** ：`ImageUtils.image_path_to_base64()` 读取图片并转为 base64 字符串。转换失败会返回失败结果。

**会话解析** ：工具通过 `chat_manager.get_session_by_session_id(stream_id)` 找到目标会话。

**CLI 分支** ：如果目标会话平台是 CLI，工具只渲染预览文本，设置 `record_usage_locally=True`，并在发送成功后调用 `emoji_manager.update_emoji_usage(selected_emoji)`。

**平台分支** ：非 CLI 平台调用 `send_service.emoji_to_stream_with_message()`。参数包含 `storage_message=True`、`set_reply=False`、`reply_message=None`、`sync_to_maisaka_history=True` 和 `maisaka_source_kind="guided_reply"`。

**消息构造** ：发送服务负责把 base64 图片包装成平台消息组件，并决定是否写入数据库、同步到 Maisaka 历史和触发发送后通知。

**使用统计** ：正常平台路径由发送服务在消息真实发送后记录使用次数。CLI 路径没有统一发送服务，因此在 `send_emoji_for_maisaka()` 中本地更新。

**成功结果** ：`MaisakaEmojiSendResult.success=True` 时，结果包含 `emoji_base64`、`description`、`emotions`、`requested_emotion`、`matched_emotion` 和 `sent_message`。

**失败结果** ：选择失败、base64 转换失败、发送异常或 Hook 中止都会返回结构化失败结果，便于工具层输出错误信息。

**聊天历史补偿** ：`handle_tool()` 发现 `send_result.sent_message is None` 时，会调用 `append_sent_emoji_to_chat_history()`，把 base64 表情写入当前上下文。

**结果日志** ：成功时会记录描述、情绪标签和命中情绪。失败时会记录错误信息，并保留描述和情绪字段用于监控。

## 与 Maisaka 的交互

**工具声明** ：`get_tool_spec()` 返回 `name="send_emoji"`，描述为“发送一个合适的表情包来辅助表达情绪”。参数 schema 为空，表示默认由推理引擎自动调用。

**工具入口** ：`handle_tool()` 是内置工具执行函数。它从运行时上下文读取会话、聊天历史和推理理由。

**上下文切片** ：工具只取最近 5 条 `LLMContextMessage` 的 `processed_plain_text`。这限制子代理看到的上下文大小，也降低 token 成本。

**推理理由传递** ：`tool_ctx.engine.last_reasoning_content` 作为 `reasoning` 传入选择流程，让子代理知道 Maisaka 为什么想发表情。

**选择回调** ：`send_emoji_for_maisaka()` 接收 `emoji_selector` 回调。默认内置工具把回调接到 `_select_emoji_with_sub_agent()`。

**模型任务选择** ：`_resolve_emoji_selector_model_task_name()` 优先使用专用 `emoji` 模型任务。没有专用任务时，如果 planner 模型具备视觉能力，则使用 planner。否则使用 vlm。

**视觉模型检查** ：当模型任务是 `vlm` 且 `_is_vlm_task_configured()` 为 `False` 时，工具抛出“没有配置视觉模型”的错误。

**子代理上下文限制** ：`_EMOJI_SUB_AGENT_CONTEXT_LIMIT = 12`，限制子代理读取的历史消息数量。

**统一监控** ：`_build_send_emoji_monitor_detail()` 和 `_build_send_emoji_monitor_metadata()` 把请求消息、推理文本、输出文本、指标、异常和发送结果组织成统一监控结构。

**Hook 边界** ：Maisaka 工具层只负责调用 Hook 和解释 Hook 返回值。真正的图片加载、描述生成和数据库维护仍在 `EmojiManager`。

**结果边界** ：`send_emoji_for_maisaka()` 返回的是结构化结果，不直接操作 UI。UI 展示由工具执行结果和 Maisaka 监控层处理。

## 与学习模块的交互

**ExpressionLearner 定位** ：`ExpressionLearner` 学习的是表达方式，即“什么情境下用什么风格说话”。它写入 `Expression` 表，而不是直接写入 `Images` 表。

**学习输入** ：`learn_from_context_messages()` 从裁切历史中过滤真实聊天消息，跳过工具结果、参考消息、记忆注入和规划器思考。

**最小消息数** ：默认至少需要 10 条真实聊天消息，才会进入表达学习批次。

**候选解析** ：学习模型输出 JSON 后，`parse_expression_response()` 提取 `expression` 和 `jargon` 两类候选。

**过滤规则** ：`_filter_expressions()` 会跳过机器人自己的发言、空消息、包含 SELF 的内容、包含表情包或图片标记的内容，以及和机器人名称重复的风格。

**写入数据库** ：`_upsert_expression_to_db()` 根据 `situation` 查找相似表达。完全匹配时直接复用，相似匹配时可用 LLM 概括新的情境文本。

**使用次数** ：每次表达方式被选中或写入时，`Expression.count` 会增加。它代表表达方式的学习热度。

**选择权重** ：`MaisakaExpressionSelector._load_expression_candidates()` 会对 `count > 1` 的候选使用 `weighted_sample()` 抽样。这部分影响的是文本表达方式选择，不是表情包选择权重。

**间接影响** ：表达学习会改变回复上下文、回复理由和目标消息。`send_emoji` 子代理看到这些上下文后，可能选择不同的候选拼图序号。

**无直接耦合** ：`ExpressionLearner` 不修改 `emoji_manager.emojis`，不调用 `update_emoji_usage()`，也不改变 `MaiEmoji.query_count`。

**相似机制** ：表情包也有 `query_count`，但只用于使用统计和满额替换时的低使用率优先，不用于 ExpressionLearner 的表达候选抽样。

**共同边界** ：两者都通过 Hook 允许插件扩展。表达学习有 `expression.select.*` 和 `expression.learn.*` Hook，表情包有 `emoji.maisaka.*` 和 `emoji.register.after_build_description` Hook。

**调试建议** ：如果看到“学习结果没有影响表情包”，先确认是否影响的是表达方式选择。若要影响表情包选择，应通过 `emoji.maisaka.before_select` 改写 `requested_emotion`、`reasoning`、`context_texts` 或 `sample_size`。

## 关键流程三：拼图筛选

**第一步，候选池生成** ：从 `emoji_manager.emojis` 随机采样，数量由配置决定。

**第二步，图片读取** ：每个候选图异步读取为字节，失败时后续使用占位图。

**第三步，缩略图生成** ：每张图片缩放到 256px 以内，放入独立方格。

**第四步，序号叠加** ：每个方格左上角绘制 56px 黑色圆角角标，并在其中写白色序号。

**第五步，布局计算** ：根据候选数量计算行列，尽量让拼图接近矩形，同时减少空位。

**第六步，网格合成** ：所有方格按行列粘贴到白色画布，方格之间保留 12px 间距。

**第七步，消息包装** ：合成图片被包装成 `ImageComponent`，并附加可见文本 `[表情包拼图候选]`。

**第八步，子代理选择** ：子代理只看拼图和任务提示，返回一个序号和简短理由。

**第九步，序号映射** ：返回序号减 1 后映射回采样列表。越界时回退到第 1 张。

**第十步，结果合并** ：选中的 `MaiEmoji` 和选择理由进入 `send_emoji_for_maisaka()` 的选择后 Hook。

## 定期维护

**维护循环** ：`periodic_emoji_maintenance()` 是无限循环。它等待 `global_config.emoji.check_interval` 分钟，或等待 `_maintenance_wakeup_event` 被配置热重载唤醒。

**扫描条件** ：只有 `steal_emoji=True`，并且当前数量低于 `max_reg_num`，或超过上限且 `do_replace=True`，才会扫描 `data/emoji`。

**已知文件集合** ：维护任务先读取 `Images` 表，把已注册、已封禁或已 VLM 处理且文件存在的图片加入 `known_paths`。

**新文件扫描** ：遍历 `EMOJI_DIR.iterdir()`，跳过目录、已知路径和超过 `max_emoji_size_mb` 的文件。

**逐个注册** ：每个新文件调用 `register_emoji_by_filename()`。注册成功后立即停止本轮扫描，避免一次维护循环注册过多图片。

**跳过逻辑** ：已注册、已封禁或描述构建失败的图片会被保留在文件系统中，但不会进入可发送池。

**完整性检查** ：`check_emoji_file_integrity()` 重新扫描 `Images` 表，重建 `self.emojis`，删除破损的已注册记录。

**描述缓存保留** ：未注册且缺少文件的记录会被保留为描述缓存，不会被完整性检查删除。

**文件清理边界** ：完整性检查不主动删除 `data/emoji` 下的图片文件。真正删除文件由 `delete_emoji()` 或外部管理流程触发。

**使用频率统计** ：`query_count` 和 `last_used_time` 由发送路径更新。正常平台发送由 `send_service._record_sent_emoji_usage()` 根据消息中的 `EmojiComponent.binary_hash` 更新。

**CLI 使用统计** ：CLI 分支没有统一发送服务回执，因此在 `send_emoji_for_maisaka()` 成功后直接调用 `emoji_manager.update_emoji_usage(selected_emoji)`。

**缓存清理** ：封禁、取消注册、删除、完整性检查和启动加载都会重建或修剪 `self.emojis`。后台描述构建任务完成后会从 `_pending_description_tasks` 移除。

**配置热重载** ：`reload_runtime_config()` 只唤醒维护等待事件。下一次维护循环会读取最新的 `global_config.emoji` 值。

**关闭清理** ：`shutdown()` 注销配置热重载回调，并唤醒维护循环，让后台任务有机会退出。

## 错误与回退

**无可用表情** ：候选池为空时，工具返回“当前表情包库中没有可用表情”。

**无视觉模型** ：选择子代理需要视觉模型时，如果未配置 VLM 任务，工具返回明确错误。

**图片读取失败** ：单张候选图读取失败会变成占位图，不会中断拼图。

**base64 转换失败** ：选中图片无法转换时，发送流程返回失败结果，并保留描述和情绪标签。

**发送失败** ：发送服务返回空消息或抛出异常时，工具返回失败结果。

**Hook 中止** ：选择前或选择后 Hook 可以中止流程。中止消息会进入工具失败结果。

**子代理 JSON 失败** ：解析失败时回退到候选首项，并记录 warning。

**序号越界** ：子代理返回不在候选范围内的序号时，回退到第 1 张。

**描述为空** ：VLM 返回空描述或 Hook 返回空标签时，注册流程拒绝该图片。

**数据库异常** ：加载、注册、更新使用次数和完整性检查都会记录错误，避免单个数据库问题扩大成整个系统崩溃。

## 开发调试入口

**查看内存池** ：`emoji_manager.emojis` 是当前可发送表情列表。它不包含未注册、封禁或缺文件的表情。

**查看数量** ：`emoji_manager._emoji_num` 是内部数量缓存。修改内存池后必须同步更新它。

**查看描述** ：`emoji.description` 是原始描述文本，`emoji.emotion` 是规范化后的标签列表。

**查看使用次数** ：`emoji.query_count` 和 `emoji.last_used_time` 来自数据库记录，发送成功后会更新。

**查看数据库字段** ：`Images.image_hash`、`Images.description`、`Images.full_path`、`Images.is_registered`、`Images.is_banned`、`Images.no_file_flag` 和 `Images.vlm_processed` 是核心字段。

**查看 Hook 规格** ：`register_emoji_hook_specs()` 注册了选择前、选择后和描述构建后三类 Hook。

**查看发送监控** ：`send_emoji.py` 的 metadata 包含请求消息、子代理输出、token 指标、耗时和发送结果。

**查看拼图合成** ：`_merge_emoji_tiles()`、`_build_labeled_tile()` 和 `_calculate_grid_shape()` 是候选拼图的核心函数。

**查看情绪匹配** ：`_calculate_emotion_similarity_list()` 和 `get_emoji_for_emotion()` 是标签匹配入口。

**查看维护循环** ：`periodic_emoji_maintenance()`、`check_emoji_file_integrity()` 和 `register_emoji_by_filename()` 是维护入口。

## 设计约束

**不要把 `self.emojis` 当数据库** ：内存池是发送优化缓存，完整状态仍以 `Images` 表为准。

**不要绕过 `resolve_stored_image_path()`** ：数据库保存的是存储路径，发送和校验前必须解析为实际文件路径。

**不要在维护循环中删除未知文件** ：当前完整性检查只维护数据库和内存池，不主动清理 `data/emoji`。

**不要让 Hook 直接依赖内部类** ：Hook 载荷使用 `_serialize_emoji_for_hook()` 的字典结构，避免跨进程序列化 `MaiEmoji`。

**不要假设 VLM 一定可用** ：描述生成、内容过滤和选择子代理都可能因为模型任务缺失而失败。

**不要重复更新使用次数** ：正常平台路径由发送服务记录。CLI 路径才在工具层本地更新。

**不要把表达学习和表情包学习混为一谈** ：`ExpressionLearner` 学习的是文本表达，表情包描述来自 VLM 或缓存描述。

**不要忽略配置上限** ：候选数量最大 64，收集大小受 `max_emoji_size_mb` 限制，注册数量受 `max_reg_num` 限制。

## 小结

**表情包加载** ：数据库记录经过注册状态、封禁状态和文件存在性过滤后进入 `emoji_manager.emojis`。

**表情匹配** ：精确哈希查找、Levenshtein 情绪匹配、最近上下文和随机候选采样共同决定候选池。

**图片合成** ：PIL 负责把候选图缩略、加序号、拼网格，为视觉子代理提供可选择的拼图。

**表情发送** ：选中表情后，路径被解析为实际文件，再转为 base64，由发送服务或 CLI 分支完成出站。

**学习交互** ：`ExpressionLearner` 不直接改变表情包权重，它通过表达方式和上下文间接影响 `send_emoji` 子代理看到的信息。

**定期维护** ：维护循环扫描新文件、注册可用表情、检查文件完整性，并通过 `query_count` 与 `last_used_time` 保留使用频率统计。

---

---
url: /develop/architecture/expression-learning.md
---

本文基于 code-map 快照编写。

# 表达学习架构

MaiBot 的 `learners/` 学习模块是一个自主进化子系统，旨在让机器人通过观察用户对话，自动习得特定的表达习惯、行为模式和社群文化。它不依赖于预定义的规则集，而是通过“观察 $\rightarrow$ 分析 $\rightarrow$ 存储 $\rightarrow$ 影响”的闭环，实现从“通用智能体”到“社群成员”的身份转变。

学习模块由四类专门的学习器协作完成：行为学习器（BehaviorLearner）、表情学习器（ExpressionLearner）、俚语挖掘器（JargonMiner）和场景聚类器（SceneClusterer）。

## 学习流转架构

学习模块在消息管线中处于异步分析位置。它不直接阻塞消息的实时回复，而是在消息流经管线时触发分析任务，并将结果持久化，从而在后续的推理循环中影响回复质量。

```mermaid
flowchart TD
    Msg[用户消息/对话流] --> Dispatcher{学习调度器}
    
    subgraph Analysis[并行分析层]
        Dispatcher --> BL[BehaviorLearner 行为学习]
        Dispatcher --> EL[ExpressionLearner 表情学习]
        Dispatcher --> JM[JargonMiner 俚语挖掘]
        Dispatcher --> SC[SceneClusterer 场景聚类]
    end
    
    subgraph Storage[持久化存储层]
        BL --> BStore[BehaviorPatternStore 行为模式库]
        EL --> EStore[ExpressionReviewStore 审核存储]
        JM --> JStore[JargonStore 俚语字典]
        SC --> SStore[SceneClusterStore 场景标签簇]
    end
    
    subgraph Feedback[反馈与应用]
        BStore --> Maisaka[Maisaka 推理引擎]
        EStore --> EmojiSys[表情包系统]
        JStore --> JExplainer[俚语解释器/推理上下文]
        SStore --> BSelector[行为选择器]
    end
    
    Maisaka --> FinalReply[最终个性化回复]
    EmojiSys --> FinalReply
    BSelector --> Maisaka
```

## 学习器详解

### BehaviorLearner（行为学习器）

行为学习器负责捕捉用户与 Bot 交互的深层模式。它不关注具体的词汇，而关注“在什么场景下，采取什么行为，会得到什么结果”。

**核心机制**：通过 LLM 解析聊天历史，生成“场景-行为-结果”三元组。如果某种行为模式（如：在用户沮丧时使用幽默化解）获得了正向反馈，该模式的权重将增加。

**关键组件**：
**`BehaviorCandidate`** ：学习到的潜在行为候选，包含场景描述、建议动作和预期效果。
**`BehaviorPatternStore`** ：管理行为模式的 CRUD，负责将学习到的候选转化为持久化的行为经验。
**`BehaviorPatternMaintenance`** ：执行模式衰减（Decay）机制，防止 Bot 僵化在过时的表达习惯中，确保学习结果具有时效性。

**触发时机**：学习行为的触发由 `LearningTrigger` 组件管理，基于以下条件组合判断：

`触发频率` — 同一场景-行为对在滑动窗口（默认 24 小时）内出现 ≥3 次即触发候选记录。

`反馈信号` — 用户对 Bot 回复的显式（点赞、@提及认可）或隐式（继续追问、使用相同风格回复）正反馈加速模式固化。

`场景相似度` — 通过 SceneClusterer 的场景标签簇计算当前对话与已存储模式的语义相似度，超过 `BEHAVIOR_SIMILARITY_THRESHOLD`（默认 0.75）时激活。

**数据存储**：学习的模式以 `BehaviorPattern` 结构持久化于 `BehaviorPatternStore`。每个模式包含以下字段：

`scene_descriptor` — 场景描述，由 SceneClusterer 的标签向量表示。

`suggested_action` — 建议行为，如"使用轻松调侃的语气回应"。

`expected_effect` — 预期效果，如"缓解用户焦虑情绪"。

`confidence` — 置信度得分（0.0–1.0），随正向反馈递增，随负向反馈或时间衰减递减。

`last_triggered` — 最后触发时间戳，用于衰减计算。

`source_rooms` — 来源群组 ID 列表，支持跨群模式迁移。

**模式衰减（Decay）**：`BehaviorPatternMaintenance` 定期扫描 Store，对置信度低于 `DECAY_THRESHOLD`（默认 0.2）且超过 7 天未触发的模式进行软删除。衰减曲线采用指数衰减公式 `confidence *= exp(-λ × Δt)`，λ 由 `DECAY_RATE` 配置项控制。

**学习示例**：

```json
{
  "scene": "用户在深夜抱怨工作压力大",
  "suggested_action": "先用幽默 GIF 缓和气氛，再提供实用建议",
  "action_keywords": ["安慰", "共情", "实用建议"],
  "expected_effect": "用户情绪好转并继续对话",
  "confidence": 0.85,
  "source_rooms": ["group_1001", "group_1002"]
}
```

### ExpressionLearner（表情学习器）

表情学习器专注于非文本的表达倾向，特别是表情包的使用习惯。它学习用户在特定语境下倾向于发送哪类表情，以及这些表情背后的触发词。

**核心机制**：监控消息流中的表情使用频率与上下文。当检测到高频且具有特定语义的表情组合时，触发学习批次，由 LLM 生成表情使用摘要。

**关键组件**：
**`ExpressionLearningBatchGate`** ：并发控制门控，防止在消息高峰期产生过多的 LLM 学习请求。
**`ExpressionReviewStore`** ：审核存储。由于自主学习可能引入不适宜的内容，学习到的表达需经过 AI 审核，并支持人工干预（Rescue/Reject）。
**`ExpressionUtils`** ：提供适格性检查和 LLM 响应解析，确保学习到的表情映射符合 JSON 规格。

**触发时机**：ExpressionLearner 通过 `ExpressionLearningBatchGate` 控制学习节奏。以下条件同时满足时触发学习批次：

`频率阈值` — 某个表情或表情组合在最近 30 条消息中出现 ≥5 次。

`语义稳定性` — 该表情在上下文中指向一致的语义（如表情\[旺柴]始终伴随调侃语气），由 LLM 进行语义一致性验证。

`并发水位` — 当前待处理的学习任务数低于 `MAX_CONCURRENT_BATCHES`（默认 3），防止 LLM 请求堆积。

**数据存储**：学习结果以 `ExpressionMapping` 结构存入 `ExpressionReviewStore`：

`trigger_keywords` — 触发关键词列表，如 \["笑死", "哈哈哈", "绝了"] → \[旺柴]。

`expression_id` — 表情包资源标识符。

`context_tags` — 语境标签，如 \["调侃", "自嘲", "轻松"]。

`review_status` — 审核状态（pending / approved / rejected / rescue）。

`frequency` — 该映射在观测窗口内的出现次数。

`confidence_weight` — 权重值，影响 expression\_selector 的最终选择概率。

**审核流程**：自主学习到的映射先标记为 `pending`。AI 审核器根据安全策略评估内容适格性，审核通过后标记为 `approved` 并加入生产映射表。人工可通过 Rescue（恢复被拒映射）或 Reject（否决）介入。审核日志记录于 `ExpressionReviewStore.audit_log`，支持追溯与回滚。

**学习示例**：

```json
{
  "trigger_keywords": ["绷不住了", "笑死", "哈哈哈"],
  "expression_id": "emoji_packet_042",
  "context_tags": ["调侃", "搞笑", "高强度吐槽"],
  "review_status": "approved",
  "frequency": 12,
  "confidence_weight": 0.78
}
```

### JargonMiner（俚语挖掘器）

俚语挖掘器负责提取社群特有的“黑话”或自定义术语。它将 Bot 变成一个能够自动更新的社群词典。

**核心机制**：基于频率推理阈值（Inference Thresholds）。一个词汇被多次出现且在上下文中具有稳定语义时，会被标记为潜在俚语 $\rightarrow$ 提交 LLM 推理含义 $\rightarrow$ 存入俚语库。

**关键组件**：
**`JARGON_INFERENCE_THRESHOLDS`** ：四级推理阈值，决定一个词从“普通词汇”升级为“候选俚语”再到“确认黑话”的触发频率。
**`JargonEntry`** ：存储俚语的定义、来源会话以及在不同群组中的含义差异。
**`JargonExplainer`** ：提供模糊搜索和范围过滤，让 Bot 能在回复中正确使用或在被询问时解释这些黑话。

**四级推理阈值详解**：

`Level 0` — 首次出现。标记为普通词汇，仅记录出现频率，不触发后续分析。

`Level 1` — 在当前群组中出现 ≥3 次。升级为候选俚语，开始追踪其出现的语义上下文，构建初步含义向量。

`Level 2` — 跨 ≥2 个不同群组出现，且语义一致性验证通过。确认为俚语候选，提交 LLM 推理其含义，生成 `JargonEntry`。

`Level 3` — 被 Bot 在回复中主动使用 ≥2 次并获正向反馈（用户互动率提升）。固化为 Bot 的主动词汇，列入主动表达库。

**数据存储**：`JargonEntry` 包含以下字段：

`term` — 俚语词汇本身。

`definition` — LLM 推理得出的含义描述。

`examples` — 使用示例，从观测对话中提取的真实句子。

`origin_sessions` — 来源会话 ID 列表。

`group_variants` — 不同群组中的含义差异映射表，同一俚语在不同社群可能有不同含义。

`inference_level` — 当前所处的推理级别（0–3）。

`first_seen_at` / `last_seen_at` — 首次与最后出现时间戳，用于频率衰减计算。

**学习示例**：

```json
{
  "term": "YBB",
  "definition": "used as a playful greeting among close friends",
  "examples": ["YBB 你今天又迟到了", "YBB 吃饭了没"],
  "group_variants": {
    "group_1001": "friend group nickname",
    "group_1002": "inside joke reference"
  },
  "inference_level": 3,
  "frequency": 47,
  "last_seen_at": "2026-06-16T12:00:00Z"
}
```

### SceneClusterer（场景聚类器）

场景聚类器为行为学习提供底层的语义支撑。它将零散的对话片段聚类为可复用的“场景标签簇”。

**核心机制**：使用 LLM 对对话进行维度分析（态度 $\rightarrow$ 领域 $\rightarrow$ 需求）。例如，将“抱怨加班”和“吐槽KPI”聚类为 `[职场, 负面, 寻求共情]` 场景簇。

**关键组件**：
**`BehaviorScenarioProfile`** ：场景画像，包含态度（Attitude）、领域（Domain）和需求（Need）三个维度。
**`TagCluster`** ：标签平等簇，支持标签的合并与权重计算。
**`SCENE_CLUSTER_REUSE_THRESHOLD`** ：复用阈值，决定一个新场景是加入现有簇还是创建新簇。

**触发条件**：SceneClusterer 不直接由单条消息触发，而是在 BehaviorLearner 或系统主动请求场景分析时启动轮次。每轮收集最近 N 条对话记录（N 由 `CLUSTER_WINDOW_SIZE` 控制，默认 50 条）作为聚类输入。

**维度分析流程**：每条对话片段通过 LLM 从三个维度进行编码：

`态度维度（Attitude）` — 用户的情感倾向，如正面、负面、中性、嘲讽、焦虑、兴奋。

`领域维度（Domain）` — 对话涉及的主题领域，如职场、技术、生活、娱乐、情感。

`需求维度（Need）` — 用户的深层需求，如寻求帮助、情感宣泄、信息获取、社交互动。

编码后的三维向量通过余弦相似度与现有 `TagCluster` 比较。相似度超过 `SCENE_CLUSTER_REUSE_THRESHOLD`（默认 0.7）则归入现有簇，否则创建新簇。

**数据存储**：`TagCluster` 包含以下属性：

`cluster_id` — 簇的唯一标识符。

`tags` — 标签集，如 \["职场", "负面", "寻求共情"]，含权重值。

`prototype_utterances` — 代表性对话原文，用于场景还原。

`member_count` — 归入该簇的对话片段数量。

`centroid_vector` — 聚类中心向量，用于新片段的相似度计算。

`last_updated` — 最后更新时间，支持簇的合并与分裂。

**聚类示例**：

```json
{
  "cluster_id": "sc_0042",
  "tags": {
    "职场": 0.92,
    "负面": 0.85,
    "寻求共情": 0.78,
    "加班": 0.65
  },
  "prototype_utterance": "真的受不了了，天天加班到十点",
  "member_count": 34,
  "last_updated": "2026-06-16T12:00:00Z"
}
```

## 学习配置示例

学习模块的各项行为通过 `config.yaml` 集中管理，以下为核心配置项：

**行为学习配置**：

```yaml
behavior_learner:
  trigger_frequency: 3           # 同一场景-行为对触发候选的记录次数
  trigger_window_hours: 24       # 滑动窗口时长（小时）
  decay_rate: 0.1                # 指数衰减系数 λ
  decay_threshold: 0.2           # 软删除置信度阈值
  similarity_threshold: 0.75     # 场景相似度阈值
  max_patterns_per_room: 200     # 每群组最大模式数
```

**表情学习配置**：

```yaml
expression_learner:
  min_frequency: 5               # 表情触发最低出现次数
  observation_window: 30         # 观测窗口消息数
  max_concurrent_batches: 3      # 最大并发 LLM 学习批次
  review_required: true          # 是否需要 AI 审核
  auto_approve_threshold: 0.9    # 自动通过审核的置信度阈值
```

**俚语挖掘配置**：

```yaml
jargon_miner:
  inference_thresholds: [1, 3, 5, 10]  # 四级推理阈值（出现次数）
  cross_group_min: 2                    # 跨群确认所需的最小群组数
  llm_inference_model: gpt-4o-mini     # 俚语推理使用的 LLM 模型
  max_jargon_per_room: 500              # 每群组最大俚语条目数
```

**场景聚类配置**：

```yaml
scene_clusterer:
  cluster_window_size: 50        # 每轮聚类分析的对话数
  reuse_threshold: 0.7           # 簇复用余弦相似度阈值
  max_clusters: 1000             # 全局最大簇数
  enable_merge: true             # 是否启用自动簇合并
  merge_similarity: 0.9          # 簇合并相似度阈值
```

## 核心处理流程

学习模块的执行遵循异步、非阻塞的管线：

**消息触发** $\rightarrow$ 消息进入 `chat` 管线 $\rightarrow$ 触发 `learners` 异步任务。
**预处理** $\rightarrow$ 提取消息元数据（用户、群组、时间） $\rightarrow$ 过滤噪声内容。
**并行分析** $\rightarrow$ 四个学习器根据各自的触发条件（频率、语义、模式）并行执行分析。
**学习结果存储** $\rightarrow$ 经过 AI 审核（表情）或阈值判定（俚语）后，写入对应的 Store。
**影响回复** $\rightarrow$ 在下一次 Maisaka 推理循环中，通过 `BehaviorSelector` 检索匹配场景的行为模式，或通过 `JargonStore` 注入黑话上下文。

## 与其它模块的交互

学习结果通过多条路径影响 Bot 的整体行为，与核心模块形成紧密的反馈闭环。

### Maisaka 推理引擎

学习结果不是直接覆盖 LLM 输出，而是作为**约束**和**上下文**注入：

**行为约束**：`BehaviorSelector` 根据当前场景标签，从 `BehaviorPatternStore` 中选出最优行为模式（如"使用轻微调侃的语气"），作为 System Prompt 的一部分注入。
**语义增强**：`JargonMiner` 挖掘的俚语及其含义被注入到推理上下文，使 Maisaka 能理解用户发送的黑话并用相同的风格回应。
**表达引导**：`ExpressionLearner` 学习到的倾向影响 `expression_selector` 的权重，提高特定表情包在当前语境下的被选中概率。

### 表情包系统

ExpressionLearner 与表情包系统的交互分为两个方向：

**正向影响**：学习到的表情-语境映射按 `confidence_weight` 排序，Top-K 映射被注入 `ExpressionSelector` 的候选池。当用户消息命中 `trigger_keywords` 时，对应表情包的选择权重上调 `weight *= (1 + confidence_weight)`。

**反向校验**：表情包系统的实际使用反馈（用户是否对带表情的回复做出积极反应）会回流至 ExpressionLearner，修正 `confidence_weight`。连续 3 次未获得正向反馈的映射降至 `rejected` 状态。

**配置联动**：表情包的审核状态（`approved` / `rejected`）由 `ExpressionReviewStore` 统一管理，表情包系统仅消费 `approved` 状态的映射，确保输出内容安全可控。

### 聊天系统

消息管线是学习模块的数据入口和效果验证场：

**数据采集**：每条消息进入 `chat` 管线后，经 `MessagePreprocessor` 提取元数据（用户 ID、群组 ID、消息时间、消息类型），以 `LearningTriggerEvent` 事件形式派发给四类学习器。学习器根据各自的过滤条件决定是否参与分析。

**异步解耦**：学习分析任务通过 `BackgroundTaskExecutor` 异步执行，不阻塞消息的实时回复管线。即使用户消息量大，回复延迟也不受影响。

**效果回测**：聊天系统定期（默认每 100 条消息）对比使用学习结果前后的用户互动指标（回复率、对话轮次长度、表情使用率），形成量化反馈闭环。

## Hook 扩展点

为了支持插件化扩展，学习模块提供了多个 Hook 拦截点：

**`expression.*`** ：允许插件自定义表情学习的过滤规则，或在表情学习完成前拦截并修改学习结果。
**`jargon.*`** ：支持外部词典注入，或在俚语挖掘触发 LLM 推理前自定义提示词。
**`learning.*`** ：全局学习行为 Hook，可用于监控学习进度、导出学习记录或强制触发模式衰减。

---

---
url: /develop/architecture/memory-system.md
---

# 记忆系统（A-Memorix）

A-Memorix 是 MaiBot 内置的长期记忆子系统，负责持久化用户偏好、对话记忆和人物画像等数据。本文详述其架构、存储机制和检索流程。

## 架构总览

```mermaid
graph TD
    subgraph "宿主侧 (Host)"
        A["AMemorixHostService<br/>(host_service.py)"]
        A --> B["SDKMemoryKernel<br/>(core/runtime/sdk_memory_kernel.py)"]
    end
    subgraph "存储层 (core/storage/)"
        B --> C["VectorStore 向量存储"]
        B --> D["GraphStore 图谱存储"]
        B --> E["MetadataStore 元数据存储"]
    end
    subgraph "检索层 (core/retrieval/)"
        B --> F["DualPathRetriever 双路检索"]
        F --> G["向量检索"]
        F --> H["图谱关系召回"]
        F --> I["稀疏检索 BM25"]
    end
    subgraph "策略层 (core/strategies/)"
        B --> J["factual 事实策略"]
        B --> B2["narrative 叙事策略"]
        B --> B3["quote 引用策略"]
    end
    subgraph "辅助服务"
        B --> K["SearchExecutionService"]
        B --> L["EpisodeService"]
        B --> M["PersonProfileService"]
        B --> N["RelationWriteService"]
        B --> O["AggregateQueryService"]
    end
```

## SDKMemoryKernel

源码位置：`src/A_memorix/core/runtime/sdk_memory_kernel.py`

`SDKMemoryKernel` 是 A-Memorix 的核心运行时，初始化时加载配置并构建所有存储和检索组件。

### 初始化流程

```mermaid
flowchart TD
    A["SDKMemoryKernel.__init__()"] --> B["加载配置 config"]
    B --> C["initialize()"]
    C --> D["创建 Embedding 适配器"]
    D --> E["初始化 VectorStore"]
    E --> F["初始化 GraphStore"]
    F --> G["初始化 MetadataStore"]
    G --> H["初始化 SparseBM25Index"]
    H --> I["初始化 EpisodeService"]
    I --> J["初始化 PersonProfileService"]
    J --> K["初始化 RelationWriteService"]
    K --> L["初始化 SearchRuntimeBundle"]
    L --> M["运行时自检"]
```

### KernelSearchRequest

检索请求的数据结构：

* **`query`** `str` · 默认为空 — 查询文本
* **`limit`** `int` · 默认 `5` — 返回条数
* **`mode`** `str` · 默认 `"search"` — 检索模式
* **`chat_id`** `str` · 默认为空 — 聊天流 ID
* **`person_id`** `str` · 默认为空 — 人物 ID
* **`time_start`** `Optional[str|float]` · 默认 `None` — 起始时间
* **`time_end`** `Optional[str|float]` · 默认 `None` — 结束时间
* **`respect_filter`** `bool` · 默认开启 — 是否应用聊天过滤配置
* **`user_id`** `str` · 默认为空 — 用户 ID
* **`group_id`** `str` · 默认为空 — 群组 ID

### 检索模式

* **`search`** — 语义向量检索 · 必需参数：`query`
* **`time`** — 时间范围检索 · 必需参数：`time_start` 或 `time_end`
* **`hybrid`** — 向量 + 时间混合 · 必需参数：`time_start` 或 `time_end`
* **`episode`** — Episode 检索 · 必需参数：`query`
* **`aggregate`** — 聚合检索 · 必需参数：`query`

::: warning
`semantic` 模式已移除，传入将返回参数错误。`time` 和 `hybrid` 模式**必须**提供 `time_start` 或 `time_end`，否则返回错误。
:::

## AMemorixHostService

源码位置：`src/A_memorix/host_service.py`

宿主侧服务，桥接 MaiBot 主进程与 A-Memorix 内核：

```python
class AMemorixHostService:
    _kernel: Optional[SDKMemoryKernel]
    _config_cache: Dict[str, Any] | None

    async def start() -> None
    async def stop() -> None
    async def reload() -> None  # 关闭内核 → 重新读取配置 → 重建内核
    async def invoke(component_name, args) -> Any  # 统一调用入口
```

### invoke 调用入口

`invoke()` 根据组件名路由到内核的对应方法：

* **`search_memory`** — `kernel.search_memory()`
* **`ingest_summary`** — `kernel.ingest_summary()`
* **`ingest_text`** — `kernel.ingest_text()`
* **`get_person_profile`** — `kernel.get_person_profile()`
* **`maintain_memory`** — `kernel.maintain_memory()`
* **`memory_stats`** — `kernel.memory_stats()`
* **`memory_graph_admin`** — `kernel.memory_graph_admin()`
* **`memory_source_admin`** — `kernel.memory_source_admin()`
* **`memory_episode_admin`** — `kernel.memory_episode_admin()`
* **`memory_profile_admin`** — `kernel.memory_profile_admin()`
* **`memory_feedback_admin`** — `kernel.memory_feedback_admin()`
* **`memory_runtime_admin`** — `kernel.memory_runtime_admin()`
* **`memory_import_admin`** — `kernel.memory_import_admin()`
* **`memory_tuning_admin`** — `kernel.memory_tuning_admin()`
* **`memory_v5_admin`** — `kernel.memory_v5_admin()`
* **`memory_delete_admin`** — `kernel.memory_delete_admin()`

### 配置管理

* 主配置路径：`config/bot_config.toml` 的 `[a_memorix]` 段
* 旧版兼容配置：`config/a_memorix.toml`（可作为迁移来源）
* Schema 文件：`src/A_memorix/config_schema.json`
* `get_config()` / `update_config()` / `get_raw_config()` / `update_raw_config()` 读写配置
* 更新配置后自动 `reload()`，重建内核实例

## 存储层

源码位置：`src/A_memorix/core/storage/`

### VectorStore

源码：`vector_store.py`

向量存储，保存段落的 embedding 向量，支持：

* 写入向量（段落哈希 → 向量映射）
* 最近邻搜索（余弦相似度）
* 量化支持（`QuantizationType`：`int8`）
* 非阻塞写入队列（embedding 失败时入队回填）

### GraphStore

源码：`graph_store.py`

知识图谱存储，管理实体和关系：

* 创建/删除/重命名节点
* 创建/删除/更新边（含权重）
* 关系向量索引
* 图谱访问操作（reinforce / protect / restore / freeze）

### MetadataStore

源码：`metadata_store.py`

元数据存储，管理来源、段落和运维记录：

* 来源（Source）管理：列表、删除、批量删除
* 段落元数据追踪
* 关系维护操作（reinforce / protect / restore / freeze / recycle\_bin）
* V5 运维记录（`external_memory_refs`、`memory_v5_operations`、`delete_operations`）

### knowledge\_types.py

定义知识内容的数据类型，区分事实性知识和叙事性知识。

## 检索层

源码位置：`src/A_memorix/core/retrieval/`

### 双路检索架构

```mermaid
flowchart TD
    A["SearchExecutionService"] --> B["DualPathRetriever"]
    B --> C["向量检索<br/>VectorStore"]
    B --> D["图谱关系召回<br/>GraphStore"]
    B --> E["稀疏检索<br/>SparseBM25Index"]
    C --> F["结果合并与排序"]
    D --> F
    E --> F
    F --> G["阈值过滤<br/>threshold.py"]
    G --> H["最终检索结果"]
```

### 关键组件

* **`dual_path.py`** — `DualPathRetriever` · 协调向量 + 图谱联合召回
* **`graph_relation_recall.py`** — 图谱关系召回 · 基于图的关联查找
* **`sparse_bm25.py`** — `SparseBM25Index` · 基于 BM25 的稀疏检索（需 FTS5 支持）
* **`pagerank.py`** — PageRank · 图结构权重计算
* **`threshold.py`** — 阈值过滤 · 相似度阈值控制

### RetrivalResult

检索结果的数据结构，包含匹配的段落、相似度分数和来源信息。

## 策略层

源码位置：`src/A_memorix/core/strategies/`

写入策略决定记忆如何被处理和存储：

* **`factual`** — `factual.py` · 事实性知识策略，提取实体和关系
* **`narrative`** — `narrative.py` · 叙事性策略，处理对话摘要
* **`quote`** — `quote.py` · 引用策略，保留原文

所有策略继承自 `base.py` 中的基类，定义统一的处理接口。

## 辅助服务

### EpisodeService

源码：`core/utils/episode_service.py`

管理 Episode（对话片段），按 source 重建：

* 状态查询（pending / processing / completed）
* 批量处理 pending Episode
* Episode 分段服务（`EpisodeSegmentationService`）
* Episode 检索服务（`EpisodeRetrievalService`）

### PersonProfileService

源码：`core/utils/person_profile_service.py`

人物画像管理：

* 自动快照：从记忆数据中自动提取人物特征
* 手动 override：通过 API 手动设置画像属性
* 画像查询：按 person\_id 和 chat\_id 获取画像

### RelationWriteService

源码：`core/utils/relation_write_service.py`

关系写入服务：

* 实体和关系的联合写入
* `external_id` 幂等去重
* 段落/关系联合写入

### AggregateQueryService

源码：`core/utils/aggregate_query_service.py`

聚合查询服务，组合多种检索模式的结果。

### ImportTaskManager

源码：`core/utils/web_import_manager.py`

Web 导入任务管理器：

* 任务创建（上传、粘贴、原始扫描、LPMM 等模式）
* 任务状态追踪
* 分块处理
* 失败重试

## 基础工具接口

### search\_memory

检索长期记忆。

**参数**：

* **`query`** `str` — 查询文本
* **`mode`** `str` — 检索模式（search/time/hybrid/episode/aggregate）
* **`limit`** `int` — 返回条数（默认 5）
* **`chat_id`** `str` — 聊天流 ID
* **`person_id`** `str` — 人物 ID
* **`time_start`** `float` — 起始时间戳
* **`time_end`** `float` — 结束时间戳
* **`respect_filter`** `bool` — 是否应用聊天过滤配置

### ingest\_summary

写入聊天摘要到长期记忆。

**参数**：

* **`external_id`** `str` — 外部幂等 ID（必填）
* **`chat_id`** `str` — 聊天流 ID（必填）
* **`text`** `str` — 摘要文本（必填）
* **`participants`** `list[str]` — 参与者列表
* **`time_start`** `float` — 起始时间戳
* **`time_end`** `float` — 结束时间戳
* **`tags`** `list[str]` — 标签
* **`metadata`** `dict` — 元数据

### ingest\_text

写入普通文本记忆。

* **`external_id`** `str` — 外部幂等 ID（必填）
* **`source_type`** `str` — 来源类型（必填）
* **`text`** `str` — 原始文本（必填）
* **`chat_id`** `str` — 聊天流 ID
* **`entities`** `list` — 实体列表
* **`relations`** `list` — 关系列表

### get\_person\_profile

获取人物画像。

* **`person_id`** `str` — 人物 ID（必填）
* **`chat_id`** `str` — 聊天流 ID
* **`limit`** `int` — 证据条数

### maintain\_memory

维护长期记忆关系状态。

* **`reinforce`** — 强化关系
* **`protect`** — 保护关系（指定小时数内不衰减）
* **`restore`** — 恢复关系
* **`freeze`** — 冻结关系
* **`recycle_bin`** — 查看回收站

## 管理工具接口

* **`memory_graph_admin`** — `get_graph` / `create_node` / `delete_node` / `rename_node` / `create_edge` / `delete_edge` / `update_edge_weight`
* **`memory_source_admin`** — `list` / `delete` / `batch_delete`
* **`memory_episode_admin`** — `query` / `list` / `get` / `status` / `rebuild` / `process_pending`
* **`memory_profile_admin`** — `query` / `list` / `set_override` / `delete_override`
* **`memory_feedback_admin`** — `list` / `get` / `rollback`
* **`memory_runtime_admin`** — `save` / `get_config` / `self_check` / `refresh_self_check` / `set_auto_save`
* **`memory_import_admin`** — `settings` / `get_guide` / `create_upload` / `create_paste` / `list` / `get` / `chunks` / `cancel` / `retry_failed`
* **`memory_tuning_admin`** — `settings` / `get_profile` / `apply_profile` / `rollback_profile` / `create_task` / `list_tasks` / `get_task` / `cancel` / `apply_best` / `get_report`
* **`memory_v5_admin`** — `status` / `recycle_bin` / `restore` / `reinforce` / `weaken` / `remember_forever` / `forget`
* **`memory_delete_admin`** — `preview` / `execute` / `restore` / `get_operation` / `list_operations` / `purge`

## 与 MaiBot 的集成

### 插件模式（Legacy）

源码位置：`src/A_memorix/plugin.py`

`AMemorixPlugin` 继承 `MaiBotPlugin`，通过 `@Tool` 装饰器注册内存检索和写入工具到插件运行时。

::: info
当前 MaiBot 主线通过 `AMemorixHostService` 直接接入，不再通过插件运行时发现和加载。`plugin.py` 保留为兼容入口。
:::

### 配置

* 主配置文件：`config/bot_config.toml` 的 `[a_memorix]` 段
* 旧版兼容配置：`config/a_memorix.toml`
* 运行时数据目录：`data/a-memorix`（由 `storage.data_dir` 控制）
* 配置 Schema：`config_schema.json` 供 WebUI 长期记忆控制台使用
* WebUI 接口：`/api/webui/memory/*`

## 元数据版本

当前元数据 schema 版本为 **v12**，支持：

* 外部引用（`external_memory_refs`）
* 运维操作记录（`memory_v5_operations`）
* 删除操作记录（`delete_operations`）

运行时可从 v9 及以上的版本化 schema 自动迁移到当前版本；更早或缺少版本表的旧库需要先执行离线迁移脚本。

## 删除语义（source 模式）

* **`requested_source_count`** — 请求删除的 source 数
* **`matched_source_count`** — 实际命中的 source 数
* **`deleted_paragraph_count`** — 实际删除段落数
* **`deleted_count`** — 与实际删除对象一致
* **`success`** — 基于实际命中与实际删除判定

---

---
url: /develop/contributing.md
---

# 贡献指南

欢迎参与 MaiBot 开发！在提交代码之前，请仔细阅读以下规范。

## 导入规范

1. 标准库和第三方库使用 `from ... import ...` 形式在前，`import ...` 形式在后；同组按字母序排列
2. 本地模块：同目录使用相对导入，跨目录使用 `from src.xxx` 绝对导入
3. 标准库/第三方库导入放在本地模块导入之前，块间用空行分隔
4. 重构时调整不符合规范的导入顺序

```python
# 标准库
import asyncio
import os
from pathlib import Path

# 第三方库
from fastapi import FastAPI
from pydantic import BaseModel

# 本地模块
from src.common.logger import get_logger
from src.config.config import config_manager
```

## 注释规范

1. 保持良好注释；重构时保留原注释（可修改内容）
2. 原无注释的重构时，较长或复杂功能块应添加注释
3. 首选语言为简体中文（注释、日志、WebUI 文案）

## 类型注解规范

1. 重构时保留原类型注解；无注解的复杂函数/多参数函数应添加
2. 参数化泛型使用 Python 3.10+ 内置语法（如 `dict[K, V]`、`list[T]`、`T | None`），避免使用旧式 typing 模块写法
3. 变量类型确定后不必使用 `or` 回退

```python
# 推荐
def process_message(message: SessionMessage, timeout: float = 5.0) -> bool:
    ...

# 不推荐
def process_message(message, timeout=5.0):
    ...
```

## 反模式列表

以下行为在项目中**严格禁止**：

* **修改 `dashboard/` 下任何内容** — 前端由独立仓库构建
* **直接编辑 `bot_config.toml` / `model_config.toml`** — 应修改模版 + 版本号
* **空 catch 块 `catch(e) {}`** — 至少记录日志
* **删除失败测试来"通过"** — 必须修复问题本身
* **硬编码 API key / 密码 / token** — 使用配置系统管理
* **`eval()` / `exec()` / `__import__`** — 存在安全风险

## 变量与属性规范

* 确定类型后不必 `or` fallback
* 减少 `getattr`/`setattr`，优先直接属性访问

## 开发命令

### 安装依赖

```bash
uv sync
```

### 运行项目

```bash
uv run python bot.py
```

### 运行测试

```bash
uv run pytest
```

### 代码检查

```bash
# Lint
uv run ruff check .

# 自动格式化
uv run ruff format .
```

## PR 流程

1. Fork 仓库并从 `dev` 分支创建功能分支
2. 确保代码通过 `uv run ruff check .` 和 `uv run pytest`
3. 提交 PR 到 `dev` 分支，附上清晰的修改说明
4. 等待代码审查与合并

### 注意事项

* WebUI 默认绑定 `127.0.0.1:8001`，生产环境需反向代理
* Token 存储在 `data/webui.json`（明文 JSON），依赖文件系统权限保护
* 限流器为内存型，多实例部署时无法共享状态
* 插件安装通过 `git clone` 执行，需确保 Git 安全配置
* `model_config.toml` 中包含 `api_key` 等敏感字段（`repr=False`）

---

---
url: /develop/adapter-dev.md
---

# 适配器开发指南

MaiBot 的适配器（Adapter）是指连接外部消息平台（如 QQ、Discord、Telegram 等）与 MaiBot 核心的桥接组件。本文档介绍 Platform IO 架构以及如何开发新的平台适配器。

## 架构概览

MaiBot 的平台 IO 层（`src/platform_io/`）采用**驱动抽象 + 路由表 + Broker 管理器**的三层架构：

```
外部平台消息 ──→ [驱动 Driver] ──→ [Broker Manager] ──→ 核心处理链
                    │                    │
                    │  InboundMessage    │  路由查找 + 去重
                    │  Envelope          │
                    │                    │
核心处理链 ──→ [Broker Manager] ──→ [驱动 Driver] ──→ 外部平台
                    │
                    │  RouteKey 解析
                    │  多驱动广播
```

核心组件：

* **PlatformIODriver**：驱动抽象基类，定义收发消息的契约
* **PlatformIOManager**：Broker 管理器，统一协调路由、去重与状态跟踪
* **RouteTable**：路由绑定表，维护 RouteKey 到驱动的映射
* **DriverRegistry**：驱动注册表，管理已注册的驱动实例

## 选择适配器开发模式

MaiBot 提供两种适配器开发方式：

**@MessageGateway（插件式）**
: 通过 `@MessageGateway` 组件装饰器注册，以插件形式运行在插件运行时（Plugin Runtime）中
: 适用场景：独立部署的适配器插件、需要跨平台复用、不需要修改 MaiBot 源码
: import: `from maibot.src.plugin_runtime.components import MessageGateway`
: 详见 [MessageGateway 开发指南](../plugin-dev/message-gateway)

**PlatformIODriver（驱动式）**
: 直接实现 `PlatformIODriver` 接口，注册到 MaiBot 的 Platform IO 系统中
: 适用场景：内置适配器、需要深度集成、随 MaiBot 一起发布
: import: `from maibot.src.platform_io.types import PlatformIODriver`
: 详见 [Platform IO 开发指南](platform-io)

## maim-message 集成

MaiBot 使用 [maim-message](https://github.com/Mai-with-u/maim_message) 作为统一消息格式标准。`MessageServer` 是 maim-message 提供的消息中间件，负责在平台适配器与 MaiBot 之间传递消息。

### 消息段（Seg）

maim-message 中的核心消息类型是 `Seg`（消息段），每条消息由一个或多个 `Seg` 组成：

```python
from maim_message import Seg

# 文本消息段
text_seg = Seg(type="text", data="你好")

# 图片消息段
image_seg = Seg(type="image", data={"file": "xxx.jpg"})
```

### Legacy 驱动

MaiBot 内置了 `LegacyPlatformDriver`，它封装了与 maim-message MessageServer 的通信逻辑，作为默认的平台驱动。当你通过 `bot_config.toml` 配置了 QQ 等平台连接信息后，Host 会自动创建并注册 Legacy 驱动。

## 如何创建新适配器

### 1. 继承 PlatformIODriver

新的适配器需要继承 `src/platform_io/drivers/base.py` 中的 `PlatformIODriver` 抽象基类：

```python
from src.platform_io.drivers.base import PlatformIODriver
from src.platform_io.types import DeliveryReceipt, DeliveryStatus, DriverDescriptor, DriverKind, RouteKey

class MyPlatformDriver(PlatformIODriver):
    async def send_message(self, message, route_key, metadata=None):
        # 实现消息发送逻辑
        ...
        return DeliveryReceipt(
            internal_message_id=message.message_id,
            route_key=route_key,
            status=DeliveryStatus.SENT,
            driver_id=self.driver_id,
            driver_kind=self.descriptor.kind,
        )
```

### 2. 实现 start/stop 生命周期

```python
async def start(self) -> None:
    # 初始化连接、启动监听等
    await self._connect()

async def stop(self) -> None:
    # 断开连接、清理资源
    await self._disconnect()
```

### 3. 上报入站消息

当适配器收到外部平台的入站消息时，通过 `emit_inbound` 方法上报给 Broker：

```python
from src.platform_io.types import InboundMessageEnvelope, DriverKind

envelope = InboundMessageEnvelope(
    route_key=RouteKey(platform="my_platform", account_id="bot_001"),
    driver_id=self.driver_id,
    driver_kind=DriverKind.PLUGIN,
    external_message_id="msg_12345",
    session_message=session_msg,  # 已规范化的 SessionMessage
)

accepted = await self.emit_inbound(envelope)
```

### 4. 注册驱动

通过 `PlatformIOManager` 注册驱动并绑定路由：

```python
from src.platform_io.manager import get_platform_io_manager
from src.platform_io.types import DriverDescriptor, DriverKind, RouteBinding

manager = get_platform_io_manager()

# 创建驱动描述
descriptor = DriverDescriptor(
    driver_id="plugin.my_adapter.qq",
    kind=DriverKind.PLUGIN,
    platform="qq",
    account_id="123456",
    plugin_id="my_adapter",
)

# 创建驱动实例并注册
driver = MyPlatformDriver(descriptor)
await manager.add_driver(driver)

# 绑定路由
manager.bind_send_route(RouteBinding(
    route_key=descriptor.route_key,
    driver_id=driver.driver_id,
    driver_kind=DriverKind.PLUGIN,
))
manager.bind_receive_route(RouteBinding(
    route_key=descriptor.route_key,
    driver_id=driver.driver_id,
    driver_kind=DriverKind.PLUGIN,
))
```

## 插件消息网关驱动

对于插件开发者，MaiBot 提供了 `PluginPlatformDriver`（定义在 `src/platform_io/drivers/plugin_driver.py`），它通过 IPC 调用插件 Runner 中的消息网关组件来实现收发能力，无需直接操作底层驱动 API。

详见 [PlatformIO 驱动](./platform-io.md) 页面。

---

---
url: /manual/adapters.md
---

# 适配器概览

适配器负责把 QQ、Telegram、微信、Discord 等消息平台接入 MaiBot。不同适配器支持的平台、运行方式和维护状态不同，第一次部署建议优先选择维护活跃、文档完整的适配器。

## 选择适配器

| 适配器 | 支持平台 | 状态 | 简介 |
| --- | --- | --- | --- |
| [NapCat](./napcat.md) | QQ | 推荐使用 | 麦麦官方维护的 QQ 适配器，支持插件版和独立版，插件版是当前推荐方案。 |
| [GoCQ](./gocq.md) | QQ | 可用，偏旧 | 基于 go-cqhttp / AstralGocq 的 QQ 适配方案，适合已有 GoCQ 环境或特定需求。 |
| [SnowLuma](./snowluma.md) | QQ | 可用（测试中） | 新一代QQ适配方案 |
| [Telegram](./telegram.md) | Telegram | 社区适配 | Telegram平台适配方案 |
| [Discord](./discord.md) | Discord | 社区适配 | Discord平台适配方案 |
| [桌宠 适配器](https://github.com/MaiM-with-u/MaiM-desktop-pet) | 桌宠 | 社区适配 | 将 MaiBot 接入桌面宠物交互场景。 |
| [微信 - wxauto Adapter](https://github.com/Angela459/WeMai) | 微信 | 社区适配 | 基于 wxauto 的微信平台适配方案。 |
| 更多适配器 | - | 社区适配 | 关注 [MaiBot GitHub 组织](https://github.com/Mai-with-u) 或社区交流群获取更多第三方适配器信息。 |

第一次部署 QQ 平台时，建议使用 **NapCat 插件版**。它直接作为 MaiBot 插件运行，配置更少，也不需要额外维护适配器与 MaiBot 之间的网络连接。

## 旧版 / 社区适配器列表（可能未及时维护）

下面这些适配器多为旧版或社区项目，部分可能无法兼容当前 MaiBot 版本。使用前建议先查看对应仓库的更新时间、README 和 Issue。

* [Nonebot 适配器](https://github.com/MaiM-with-u/nonebot-plugin-maibot-adapters)
* [Milky 协议适配器](https://github.com/ShinKanji/MaiBot-Milky-Adapter)

::: warning 注意兼容性
部分社区适配器可能是旧版项目，未必兼容当前 MaiBot。安装前建议先查看仓库更新时间、README 和 Issue。
:::

### 插件版适配器

如果适配器提供插件版，通常按这个流程安装：

1. 下载或克隆适配器项目。
2. 确认切换到适配器要求的插件分支。
3. 将适配器目录放入 MaiBot 的 `plugins/` 目录。
4. 启动 MaiBot，让插件系统自动加载适配器。

插件版适配器运行在 MaiBot 内部，通常只需要配置“消息平台到适配器”的连接。

### 独立版适配器

如果适配器是独立版，通常按这个流程安装：

1. 下载或克隆适配器项目。
2. 按适配器文档安装依赖。
3. 填写适配器自己的配置文件。
4. 单独启动适配器进程。

独立版适配器需要同时连接消息平台和 MaiBot，排查问题时也要分别检查这两段连接。

## 配置连接

适配器通常需要配置两类连接：

| 连接方向 | 说明 |
| --- | --- |
| 消息平台 → 适配器 | 例如 NapCat 连接到 QQ，并把 QQ 消息推送给适配器。 |
| 适配器 → MaiBot | 独立版适配器需要连接 MaiBot；插件版适配器通常不需要额外配置这一层。 |

使用插件版适配器时，主要确认适配器能正确连接消息平台。

使用独立版适配器时，还需要确认适配器能连接到 MaiBot 的消息服务地址。

如果你不确定该填什么地址，先按对应适配器文档的默认本机配置来跑通，再考虑跨机器或 Docker 网络部署。

## 确认连接成功

配置完成后，向对应平台发送一条测试消息。

如果 MaiBot 后台能看到对应消息日志，并且 MaiBot 能正常回复，说明适配器已经连接成功。

如果没有收到消息，按这个顺序检查：

1. 消息平台客户端是否已经登录成功。
2. 适配器是否正常启动。
3. 适配器是否成功连接消息平台。
4. 独立版适配器是否成功连接 MaiBot。
5. MaiBot 是否已经完成初始化并正常运行。

---

---
url: /manual/deployment.md
---

# MaiBot 简介

**MaiBot 是一个拟人化的智能体**，可以陪你聊天，不断学习了解你，搜集信息，或者用插件或者mcp扩展能力。

MaiBot可以通过本地命令行对话，也可以通过适配器插件连接到不同的IM平台或者任意客户端。

## 部署方法

MaiBot可以通过多种方法部署

| 方式                               | 适合人群          |
| -------------------------------- | ------------- |
| [源码安装](./installation.md)        | 适合喜欢用源码部署的人 |
| [一键包部署](./one_key.md) | 适合喜欢用一键包的人  |
| [Docker部署](./docker.md) | 适合喜欢用Docker的人  |

## 如何与麦麦对话

首先你要正确安装MaiBot，然后启动

### webui对话

启动MaiBot你将会看到WebUI伴随MaiBot启动，默认通过 http://127.0.0.1:8001/ 来访问你部署的麦麦的Webui

在WebUI中，你可以跟随**配置向导**进行基础配置，要与麦麦对话，你需要设置相应的模型和设置。

麦麦要能活动最少需要一个LLM模型，如果需要看图片，还需要一个VLM；如果需要启用记忆，还需要一个embedding嵌入模型。

配置好之后，你可以通过顶部导航的**麦麦聊天**进行对话。

关于配置的更多帮助，可以阅读[配置指南](../configuration/index.md)

### 在QQ与麦麦对话

要让 MaiBot 连接到QQ，你需要\*\*适配器（Adapter）\*\*来建立 MaiBot 与这些消息平台的联系。

这里介绍NapCat。

众所周知，QQ有官方机器人，但是官方机器人提供的接口很少，不能主动获取消息，局限性很大

所以这里我们建议使用**NapCat**，你可以通俗的理解为这是一个非官方的QQ机器人应用（通俗理解）。

要让NapCat连接到MaiBot，就需要通过Adapter来桥接，将NapCat的消息发送到MaiBot进行处理。

这就延伸出两个问题：1.如何部署NapCat  2.如何安装适配器

#### 如何部署NapCat

如果你是通过Docker或者一键包安装的，往往会附带一个NapCat客户端，所以不用额外安装

如果你是通过源码部署的，你需要单独安装NapCat，你可以参考NapCat的文档来安装，这里不再赘述

[NapCat官方文档](https://napneko.github.io/)

#### 如何安装适配器

要使用NapCat适配器，可以参考这个链接。[NapCat 适配器使用](../adapters/napcat.md)

### 在其他平台与麦麦对话

与QQ类似，在其他平台也可以通过安装适配器插件来实现对话

你可以在这里找到其他的适配器 [适配器概览](../adapters/index.md)。

---

---
url: /manual/configuration.md
---

# 配置概览

## 📋 配置文件清单

MaiBot 有两个主要的配置文件，都放在 `config/` 文件夹里：

| 📁 文件 | 📝 作用 | 🔗 详细说明 |
|---------|---------|------------|
| `bot_config.toml` | 机器人的基本信息、性格、聊天、记忆（含 A\_Memorix）、学习、日志等全部主配置 | [查看详情](./bot-config.md) |
| `model_config.toml` | AI模型设置，设置麦麦使用的LLM | [查看详情](./model-config.md) |

::: tip 💡 小贴士
这些配置文件需要启动一次MaiBot之后才会生成。如果无法找到，请先启动一次。
:::

::: tip 💡 麦麦现在支持配置热重载
麦麦现在支持配置热重载。修改配置文件后无需重启，保存即可自动重新加载新配置。
(有些配置（比如换AI模型）可能需要重新初始化相关服务才能完全生效。)
:::

## 🌐 WebUI 配置

如果你不喜欢手动改文件，MaiBot 还提供了网页版的配置界面（1.0.0 已内置 WebUI 配置界面）：

* 🌐 默认地址：`http://127.0.0.1:8001`
* 🖱️ 点点鼠标就能改配置
* 📱 手机、电脑都能用

---

---
url: /develop/plugin-dev/config.md
---

# 配置管理

MaiBot 插件支持声明式的配置管理机制，通过 `PluginConfigBase` 和 `Field` 定义强类型配置模型，Runner 会自动生成默认配置、补齐缺失字段，并向 WebUI 暴露可渲染的配置 Schema。

## 配置文件位置

每个插件的配置文件位于插件目录下的 `config.toml`：

```
my_plugin/
├── plugin.py          # 插件入口
├── config.toml        # 插件配置（可选）
└── _manifest.json     # 插件元信息
```

::: tip config.toml vs \_manifest.json

* `config.toml`：插件的**运行时配置**（功能开关、参数等），由插件自身读取
* `_manifest.json`：插件的**元信息**（ID、版本、依赖等），由 Host 校验和管理

两者用途完全不同，不要混淆。
:::

## PluginConfigBase 配置模型

### 基本用法

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    __ui_label__ = "插件配置"

    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")
    max_retries: int = Field(default=3, description="最大重试次数")


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 通过 self.config 访问强类型配置
        self.ctx.logger.info("当前问候语: %s", self.config.greeting)
        self.ctx.logger.info("最大重试: %d", self.config.max_retries)
```

### 嵌套配置

通过嵌套 `PluginConfigBase` 类实现分组配置：

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class PluginSection(PluginConfigBase):
    """插件基础配置"""
    __ui_label__ = "基础设置"

    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")


class AdvancedSection(PluginConfigBase):
    """高级配置"""
    __ui_label__ = "高级设置"

    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: float = Field(default=30.0, description="超时时间（秒）")


class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    plugin: PluginSection = Field(default_factory=PluginSection)
    advanced: AdvancedSection = Field(default_factory=AdvancedSection)


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 访问嵌套配置
        self.ctx.logger.info("问候语: %s", self.config.plugin.greeting)
        self.ctx.logger.info("超时: %s", self.config.advanced.timeout)
```

## Field 字段

`Field` 用于声明配置字段的元数据：

```python
from maibot_sdk import Field

Field(
    default=...,          # 默认值
    default_factory=...,   # 默认值工厂函数（用于可变默认值）
    description="...",     # 字段描述（显示在 WebUI 中）
)
```

* **`default`** `Any` — 字段默认值
* **`default_factory`** `Callable` — 默认值工厂函数，用于 `list`、`dict`、嵌套 `PluginConfigBase` 等可变类型
* **`description`** `str` — 字段描述，WebUI 中显示为表单标签
* **`json_schema_extra`** `dict` — 额外元数据，传递给 WebUI Schema 生成器。常用键: `placeholder`（输入框占位符文本）、`group`（UI 分组提示）

### **ui\_label**

`PluginConfigBase` 子类可通过 `__ui_label__` 类属性设置在 WebUI 中显示的分组标题：

```python
class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"  # WebUI 中显示的标题
    enabled: bool = Field(default=True, description="是否启用插件")
```

### **ui\_icon**

`PluginConfigBase` 子类可通过 `__ui_icon__` 类属性设置在 WebUI 中显示的分组图标，接受 [Material Icons](https://fonts.google.com/icons) 图标名称：

```python
class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"  # WebUI 中显示的 Material Icons 图标名
    enabled: bool = Field(default=True, description="是否启用插件")
```

### **ui\_order**

`PluginConfigBase` 子类可通过 `__ui_order__` 类属性设置分组在 WebUI 中的显示顺序，数值越小越靠前：

```python
class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"
    __ui_order__ = 0  # WebUI 中分组的排序权重，数字越小越靠前
    enabled: bool = Field(default=True, description="是否启用插件")
```

### json\_schema\_extra

`json_schema_extra` 用于传递额外元数据给 WebUI Schema 生成器，常用场景包括：

* `placeholder`：输入框的占位符提示文本
* `group`：WebUI 中的配置分组提示

```python
class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    greeting: str = Field(
        default="你好！",
        description="默认问候语",
        json_schema_extra={"placeholder": "请输入问候语", "group": "basic"}
    )
    api_key: str = Field(
        default="",
        description="API 密钥",
        json_schema_extra={"placeholder": "请输入 API Key", "group": "advanced"}
    )
```

## 访问配置

### 强类型访问（self.config）

```python
class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 强类型访问，有代码补全和类型检查
        greeting = self.config.plugin.greeting
        timeout = self.config.advanced.timeout
```

::: warning 注意

* 未声明 `config_model` 时调用 `self.config` 会抛出 `RuntimeError`
* 配置尚未注入时调用 `self.config` 也会抛出 `RuntimeError`
  :::

### 原始字典访问

```python
class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 获取原始配置字典
        raw = self.get_plugin_config_data()
        greeting = raw.get("plugin", {}).get("greeting", "默认值")
```

`get_plugin_config_data()` 始终可用，返回 `dict[str, Any]`，无需声明 `config_model`。

## 配置热重载

当 `config.toml` 文件变更时，Runner 会自动触发 `on_config_update()` 回调：

```python
from maibot_sdk import MaiBotPlugin, CONFIG_RELOAD_SCOPE_SELF

class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            # self.config 会自动更新为最新值
            self.ctx.logger.info("配置已更新，新问候语: %s", self.config.plugin.greeting)
```

::: important
`self.config` 在 `on_config_update(scope="self")` 调用时已自动更新，无需手动重新读取。
:::

更多关于配置热重载的内容，参见 [生命周期](./lifecycle.md#on-config-update)。

## config.toml 格式

配置文件使用 TOML 格式，与 `PluginConfigBase` 的嵌套结构对应：

```toml
[plugin]
config_version = "1.0.0"
enabled = true
greeting = "你好！"

[advanced]
max_retries = 3
timeout = 30.0
```

### config\_version

`config_version` 是一个特殊字段，用于跟踪配置版本。Runner 在合并默认配置时会保留此字段。

## 默认配置与 Schema 生成

### 自动补齐

当 `config.toml` 中缺少某些字段时，Runner 会根据 `config_model` 的默认值自动补齐：

```python
# 如果 config.toml 只有:
# [plugin]
# enabled = false

# Runner 会自动补齐 greeting 和 advanced 部分的默认值
```

### WebUI Schema

声明 `config_model` 后，Runner 会自动生成 WebUI 可渲染的配置 Schema：

```python
# 插件类上的方法（通常不需要手动调用）
schema = MyPlugin.build_config_schema(
    plugin_id="com.example.my-plugin",
    plugin_name="我的插件",
    plugin_version="1.0.0",
)
```

WebUI 会根据 Schema 渲染配置表单，用户可以在浏览器中直接编辑配置。

## 通过 API 读取配置

除了通过 `self.config` 和 `self.get_plugin_config_data()` 外，还可以通过能力代理读取配置：

```python
# 读取插件自身配置
value = await self.ctx.config.get("plugin.greeting")

# 读取其他插件配置
value = await self.ctx.config.get_plugin("com.other.plugin")

# 读取全局 Bot 配置
all_config = await self.ctx.config.get_all()
```

## 不使用 config\_model

如果插件配置非常简单，可以不声明 `config_model`，直接使用 `ctx.config` 和 `get_plugin_config_data()`：

```python
class SimplePlugin(MaiBotPlugin):
    # 不声明 config_model

    async def on_load(self) -> None:
        # 只能通过原始字典或 ctx.config 读取
        raw = self.get_plugin_config_data()
        name = raw.get("name", "默认名称")

        # self.config 会抛出 RuntimeError
        # 不要调用 self.config
```

但建议始终使用 `config_model`，以获得更好的类型安全和 WebUI 集成体验。
