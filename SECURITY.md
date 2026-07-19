# SECURITY.md

## 安全策略

### 凭证管理

- **严禁**将API密钥、账户密码、Token、Cookie写入Git仓库
- 所有真实凭证存储在 `.gitignore` 排除的本地文件（如 `data/wallet.json`）
- 凭证示例模板使用 `config/local_credentials.example.json`

### 数据隔离

以下数据类别**永不进入Git**：
- 券商账户数据、交易订单、持仓快照
- 原始Level-2逐笔/委托/队列数据
- 生产数据库文件（.db, .sqlite, .sqlite3）
- 大型市场数据导出（CSV/Parquet > 5MB）
- 日志文件（可能含泄漏的路径/令牌）

### 分支保护

- `main` 分支不得直接修改
- 所有变更通过独立分支 + Pull Request 提交
- PR 必须经过复核（CODEX 技术复核 + GPT 架构验收）

### 报告协议

- 发现疑似凭证：**只报告路径和类型，不展示内容**
- 发现生产风险：**立即停止，保全现场并报告**
- 不得在聊天记录、日志、报告或仓库中输出凭证正文

### 连接器安全

- CodeBuddy-Connector 仅获账号级授权，无仓库级权限
- 仓库操作使用本地Git + 系统凭证管理器
- 不得创建Personal Access Token（PAT），除非Git + 凭证管理器均失败并单独报告

### 密钥泄露应急

如疑似密钥已泄露：
1. 立即停止所有Git操作
2. 报告给USER
3. 在GitHub上轮换受影响的密钥
4. 使用 `git filter-branch` 或 `BFG` 从历史中移除
5. 强制推送前通知所有协作者
