# PYTHON-ENVIRONMENT-REPRODUCTION — Codex 成功环境复现

## 成功环境 (WorkBuddy 复现)
| 参数 | 值 |
|---|---|
| Python 绝对路径 | `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe` |
| Python 版本 | 3.13.14 (MSC v.1944 64 bit AMD64) |
| numpy | 2.5.1 |
| pandas | 3.0.3 |
| 脚本路径 | `F:\aidanao\交流文件\TDX-PREUPDATE-CAPABILITY-CORRECTION-0007\_probe_v2.py` |
| sys.path[0] | `F:/tongdaxin/PYPlugins/user` |
| sys.path[1] | `F:/tongdaxin/PYPlugins/sys` |
| 实际加载 tqcenter | `F:\tongdaxin/PYPlugins/sys\tqcenter.py` (sys 优先于 user) |
| TPythClient.dll | `F:\tongdaxin\PYPlugins\TPythClient.dll` |
| TdxW 主进程 | PID 1628, VER 1,0,0,1, 启动 09:21:53 |
| 通达信安装目录 | F:\tongdaxin |

## 初始化参数
```python
from tqcenter import tq
tq.initialize(__file__)  # __file__ = probe_v2.py
```
- `_connection_path` = probe_v2.py 的绝对路径
- `dll.InitConnect(file_name, dll_path, run_mode=0, python_version)` → ErrorId='12' (已有同名连接，但 run_id 仍返回 3)
- run_id=3, _initialized=True
- 初始化输出: "TQ数据接口初始化成功，使用路径: F:\aidanao\交流文件\TDX-PREUPDATE-CAPABILITY-CORRECTION-0007\_probe_v2.py"

## WorkBuddy 与 Codex 差异
- **无根本差异**。WorkBuddy 上次失败根因: **未调 `tq.initialize(__file__)`**，直接调数据方法触发 `_auto_initialize` → `cls._connection_path` 为空 → RuntimeError。
- Codex 成功原因: 调了 `tq.initialize()` 设置路径。
- 复现确认: 只需 `tq.initialize(__file__)` 一步。——外部 python.exe 即可成功初始化。

## 注意事项
- ErrorId='12' 含义: "已有同名策略运行"——但不影响初始化成功(run_id=3 正常返回)
- `tq.close()` 成功关闭连接: "TQ数据连接已关闭"
- TdxW PID 1628 探针前后均存活(未受损)
