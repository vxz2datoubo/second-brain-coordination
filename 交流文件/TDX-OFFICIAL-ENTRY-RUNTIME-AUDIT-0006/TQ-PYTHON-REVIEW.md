# TQ-PYTHON-REVIEW — 官方 TQ-Python v1.0.12 审计

## 版本
v1.0.12，与 TQ-Local 同版本。

## 定位
"此技能支持python代码通过tqcenter接口与本地的通达信客户端交互。" — 即生成 Python 代码文件，在 TDX 策略管理器内运行 tqcenter.py。与本地已有的 tqcenter.py v1.0.4 调用方式**相同**但文档版本更新。

## 与本地 tqcenter.py v1.0.4 的关系
- TQ-Python v1.0.12 的 SKILL.md **接口文档比本地 tqcenter.py v1.0.4 更为丰富**(含 get_pricevol, get_more_info L2 聚合字段等)
- 但底层的 Python 代码仍调用本地 F:/tongdaxin/PYPlugins/user/tqcenter.py → **如果本地 tqcenter.py 是 v1.0.4，则运行时代码只能调用 v1.0.4 的接口**
- v1.0.12 SKILL.md 中新增的接口(get_pricevol 等)在 v1.0.4 的 tqcenter.py 中**不存在** → Skill 生成代码会报 AttributeError
- **版本错位 = 文档与运行时不对齐**

## 安装与使用
- TQ-Python 作为 Skill 安装到 WorkBuddy/CodeX 等 AI 平台
- AI 根据 Skill 生成 Python 代码 → 用户手动放入 PYPlugins/user/ → TDX 策略管理器运行
- 本轮不安装/不测试（依赖本地 tqcenter.py 版本，v1.0.4 缺少新接口）
- 需先更新客户端组件才能发挥 v1.0.12 的完整接口

## 结论
TQ-Python v1.0.12 文档比本地 tqcenter.py v1.0.4 丰富，但因版本错位无法运行新接口。安装 Skill 本身不会改变本地 tqcenter.py 版本。需先更新客户端（更新 TPythClient.dll + tqcenter.py）再安装 Skill 才能对齐。
