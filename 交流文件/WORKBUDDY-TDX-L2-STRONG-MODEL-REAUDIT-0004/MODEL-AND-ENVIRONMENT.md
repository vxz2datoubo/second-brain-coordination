# MODEL-AND-ENVIRONMENT — WORKBUDDY-TDX-L2-STRONG-MODEL-REAUDIT-0004

## 模型/质量配置
- **执行模型**: 当前会话最强推理配置（Hy3 推理模型，本任务以独立复验/复算/重跑探针为方法）。
- **方法**: 盲审优先——先只读 raw 证据 + 重跑只读探针，独立形成结论，最后才读旧 4 份总结报告对账。
- **锚定偏差声明**: 本助手上一轮(0003)即为旧报告作者，对旧结论有先验印象。本轮通过 (a)独立复算 raw 完整性 (b)重跑 tqcenter 运行时探针(旧轮未执行) (c)广谱本地文件审计(旧轮仅查.l2d/.tick) 三项**新证据**校正，已尽量降低锚定偏差。但无法完全排除。

## 环境（复验时点 2026-07-16 10:01–10:10）
| 项 | 值 |
|---|---|
| 北京时间 | 09:59:31 任务下发 → 10:10 复验进行 |
| TdxW.exe | PID 1628，全程存活（探针前后均 true），启动 09:21:53 |
| 安装目录 | F:\tongdaxin |
| tqcenter.py | v1.0.4，F:\tongdaxin\PYPlugins\{sys,user}\，桥接 TPythClient.dll (2.4MB, 2026-03-23) |
| 探针 Python | managed venv (3.13)，已装 numpy 2.5.1 / pandas 3.0.3 |
| TDX 独立 python.exe | **未发现**（插件用内嵌解释器，无独立可调用 python） |
| 现场保护 | 全程只读；探针仅 get_market_snapshot，未调 order/subscribe；TdxW 未重启未改配置 |

## 复验执行清单
1. ✅ 独立复算 raw 完整性（SHA256/记录数/时间/字段）→ 发现 R1/R2 raw 未落盘缺口
2. ✅ tqcenter.py 关键词静态枚举（tick/transaction/order/queue/auction/full/report/subscribe）→ 发现 _fast_format_tick_data + period=='tick' 死代码分支
3. ✅ TdxQuant 运行时探针（旧轮未做）→ import OK，InitConnect 失败，TdxW 未受损
4. ✅ 本地文件广谱审计（.dat/.bin/无扩展名/hq_cache/PriCS/PriGS）→ 发现 .th2/.tcu/.tnf/PriCS.dat 候选
5. ✅ R5 采样（300418, 10:09）→ 延长时间序列，十档仍 5 档
6. ✅ 读旧报告对账
