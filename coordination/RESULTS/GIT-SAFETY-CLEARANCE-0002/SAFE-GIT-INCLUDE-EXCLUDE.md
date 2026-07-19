# Safe Git Include / Exclude Decision

## A. 可直接进入 Git

建议直接纳入首次提交的范围：

1. 根级控制文件
   - `AGENTS.md`
   - `SYSTEM_MANUAL.md`
   - `AUTO_EVOLUTION.md`
   - `MCP_TOOLS.md`
   - `README.md`
   - `server.py`

2. 母系统源码
   - `brain_core/`（排除 `__pycache__`）
   - `apps/`（排除 `__pycache__`）

3. 测试
   - `tests/`（排除 `__pycache__`）

4. 治理与正式文档
   - `docs/`
   - `config/trading/*.candidate.yaml`

5. 已脱敏的正式审计摘要
   - 可保留 `coordination/RESULTS/` 下的**正式脱敏摘要**
   - 不包含回滚包、不包含明文秘密报告

## B. 修正后才能进入 Git

这些文件本质上属于源码，应进入版本控制，但必须先脱敏：

1. `core/tushare_bridge.py`
2. `core/qclaw.py`
3. `daytrade_system/live/tdx_mcp_client.py`
4. `mcp/tdx_live_bridge.py`

推荐修正方式：

- 用环境变量替代真实值
- 必要时允许本地不入库配置作为 fallback
- 缺失密钥时报错，但错误信息中不打印秘密值
- 不把秘密值写进日志、异常或审计事件

## C. 永久排除

以下内容不应进入 Git 首次基线：

1. 运行态数据
   - `data/`
   - `logs/`
   - `server.pid`
   - 根目录下各类 `*_log.txt` / `*_out*.txt`

2. 凭据与会话
   - `data/wallet.json`
   - `chatgpt_bridge/playwright_state.json`
   - `chatgpt_bridge/playwright_user_data/`
   - 任何 `.env`、密钥文件、Cookie / session / vault 文件

3. 缓存与本地依赖
   - `__pycache__/`
   - `*.pyc`
   - `codex_siliconflow_proxy/.venv/`

4. 归档与生成物
   - `backups/`
   - `handoff/`
   - `qclaw-output/`
   - 运行态回滚包
   - SQLite / JSONL / 本地 audit 产物

## D. 需要用户决定

这些范围不是“现在就必须排除”，但不建议在首次基线里自动带上：

1. 第三方或镜像型资料
   - `official-guide/`
   - `maibot/`
   - `MAIBOT_DOCS/`

2. 相邻服务或独立子工程
   - `codex_siliconflow_proxy/`

3. 第三方二进制或授权受限资源
   - `tools/dreamina/`

4. 第二大脑知识文本是否作为源码资产
   - `second-brain/rules.md`
   - `second-brain/lessons.md`

## Recommended First Baseline Shape

建议第一次提交用最窄、最干净的形状：

- A 类全部纳入
- B 类完成脱敏后纳入
- C 类全部排除
- D 类全部延后，等用户单独批准
