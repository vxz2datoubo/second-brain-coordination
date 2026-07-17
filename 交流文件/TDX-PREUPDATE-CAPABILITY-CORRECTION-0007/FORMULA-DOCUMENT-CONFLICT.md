# FORMULA-DOCUMENT-CONFLICT — 公式接口矛盾

## 矛盾
| 来源 | 陈述 | 
|---|---|
| 官方更新日志 | 声称存在 formula_get_all / formula_get_info |
| TQ-Local v1.0.12 SKILL.md | **未列出** formula_get_all / formula_get_info |
| TQ-Python v1.0.12 SKILL.md | **未列出** |
| tqcenter.py v1.0.4 运行时 | hasattr(tq, 'formula_get_all') = **False** |

## 判定
`DOCUMENT_CONFLICT_RUNTIME_NOT_VERIFIED_ON_V1_0_12`

- 官方更新日志声称有，但 Skill 文档和本地代码均无
- 不得根据 Skill 缺失宣布新版运行时不存在——可能 Skill 文档未涵盖所有方法
- 不得根据 v1.0.4 缺失推断 v1.0.12 也没有——公式接口可能是 v1.0.5+ 新增

## 升级后必须验证
```python
import tqcenter
from tqcenter import tq
hasattr(tq, 'formula_get_all')  # v1.0.12 应返回 True?
hasattr(tq, 'formula_get_info')
# 若存在，测试:
# tq.get_more_info 的 field_list 是否支持 formula 字段?
# DLL 是否有 FormulaGetAllInStr 等新函数?
```
